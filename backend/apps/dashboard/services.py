import logging
from datetime import timezone as dt_timezone, datetime
from django.db.models import Count, Q, Sum, Exists, OuterRef, Case, When, Value, IntegerField
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger('apps')

# 缓存 TTL（秒）
DASHBOARD_CACHE_TTL = 60


def _safe_int(value, default, min_val=1, max_val=100):
    """安全的 int 解析，防止非法参数导致 500。"""
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    return max(min_val, min(max_val, v))


def _month_range(year, month):
    """返回 (month_start, month_end) 时区感知 datetime。"""
    start = datetime(year, month, 1, tzinfo=dt_timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=dt_timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=dt_timezone.utc)
    return start, end


def _days_label(deadline):
    """生成逾期/即将到期的可读标签。"""
    if not deadline:
        return ''
    now = timezone.now()
    delta = (now - deadline).days
    if delta > 0:
        return f'已逾期 {delta} 天'
    elif delta == 0:
        return '今天到期'
    elif delta >= -3:
        return f'{abs(delta)} 天后到期'
    return ''


class DashboardService:
    """仪表盘数据聚合（角色化）。"""

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_by_user(qs, user):
        """根据用户角色过滤查询集：非 superuser/leader/admin 只统计自己的任务。
        包含：assignee、creator、participants。
        """
        if user and not user.is_superuser and user.role not in ('LEADER', 'ADMIN'):
            from apps.tasks.models import TaskParticipant
            participation_exists = Exists(
                TaskParticipant.objects.filter(task=OuterRef('pk'), user=user)
            )
            qs = qs.filter(
                Q(assignee=user) | Q(creator=user) | participation_exists
            )
        return qs

    @staticmethod
    def _base_summary(qs):
        """单次聚合获取状态统计。"""
        now = timezone.now()
        return qs.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='PENDING')),
            in_progress=Count('id', filter=Q(status='IN_PROGRESS')),
            in_review=Count('id', filter=Q(status='IN_REVIEW')),
            completed=Count('id', filter=Q(status='COMPLETED')),
            overdue=Count('id', filter=Q(
                deadline__lt=now
            ) & ~Q(status__in=['COMPLETED', 'CANCELLED'])),
        )

    # ------------------------------------------------------------------
    # MEMBER 工作台
    # ------------------------------------------------------------------

    @staticmethod
    def get_member_dashboard(user):
        """MEMBER 个人工作台。"""
        from apps.tasks.models import Task

        now = timezone.now()
        year, month = now.year, now.month
        month_start, month_end = _month_range(year, month)

        # 基础查询集（个人相关任务）
        qs = Task.objects.all()
        qs = DashboardService._filter_by_user(qs, user)

        # 1. 状态统计
        summary = DashboardService._base_summary(qs)

        # 2. 本月个人积分
        monthly = qs.filter(
            completed_at__gte=month_start,
            completed_at__lt=month_end,
            status='COMPLETED',
        ).aggregate(
            earned=Sum('reward_points'),
            completed_count=Count('id'),
        )
        in_progress_count = qs.filter(status='IN_PROGRESS').count()

        # 3. 待办列表（按紧急度排序：逾期 → 进行中 → 待领取）
        now_ts = timezone.now()
        todo_qs = qs.filter(
            ~Q(status__in=['COMPLETED', 'CANCELLED'])
        ).select_related('assignee', 'creator').annotate(
            overdue_order=Case(
                When(deadline__lt=now_ts, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
        ).order_by(
            'overdue_order',
            'deadline',
            '-priority',
        )[:20]

        todo_list = []
        for t in todo_qs:
            todo_list.append({
                'id': str(t.id),
                'task_no': t.task_no,
                'title': t.title,
                'priority': t.priority,
                'status': t.status,
                'deadline': t.deadline.isoformat() if t.deadline else None,
                'is_overdue': t.is_overdue,
                'days_until_deadline': t.days_until_deadline,
                'progress': t.progress,
                'task_mode': t.task_mode,
                'assignee_name': t.assignee.display_name if t.assignee else '',
                'days_label': _days_label(t.deadline),
            })

        return {
            'summary': summary,
            'monthly_points': {
                'earned': monthly['earned'] or 0,
                'completed_count': monthly['completed_count'] or 0,
                'in_progress_count': in_progress_count,
            },
            'todo_list': todo_list,
        }

    # ------------------------------------------------------------------
    # LEADER/ADMIN 管理台
    # ------------------------------------------------------------------

    @staticmethod
    def get_leader_dashboard(user):
        """LEADER/ADMIN 团队管理台。"""
        from apps.tasks.models import Task
        from apps.accounts.models import User

        now = timezone.now()
        year, month = now.year, now.month
        month_start, month_end = _month_range(year, month)

        # 全团队查询集
        qs = Task.objects.all()

        # 1. 团队状态统计
        summary = DashboardService._base_summary(qs)

        # 2. 本月团队积分
        monthly = qs.filter(
            completed_at__gte=month_start,
            completed_at__lt=month_end,
            status='COMPLETED',
        ).aggregate(
            total_points=Sum('reward_points'),
            completed_count=Count('id'),
        )
        total_tasks = summary['total'] or 1
        completed_count = monthly['completed_count'] or 0

        # 3. 成员负载（只查有任务的活跃用户）
        all_members = User.objects.filter(
            is_active=True
        ).select_related('team').only('id', 'username', 'first_name', 'last_name', 'team__name')

        member_workload = []
        for u in all_members:
            member_qs = Task.objects.filter(
                Q(assignee=u) | Q(creator=u) | Q(participants__user=u)
            ).distinct()

            in_progress = member_qs.filter(status='IN_PROGRESS').count()
            completed_month = member_qs.filter(
                completed_at__gte=month_start,
                completed_at__lt=month_end,
                status='COMPLETED',
            ).count()
            points = member_qs.filter(
                completed_at__gte=month_start,
                completed_at__lt=month_end,
                status='COMPLETED',
            ).aggregate(total=Sum('reward_points'))['total'] or 0

            if in_progress > 0 or completed_month > 0:
                member_workload.append({
                    'user_id': str(u.id),
                    'username': u.username,
                    'display_name': u.display_name,
                    'team_name': u.team.name if u.team else '',
                    'in_progress': in_progress,
                    'completed_this_month': completed_month,
                    'total_points': points,
                })

        member_workload.sort(key=lambda x: -x['in_progress'])

        # 4. 逾期任务列表
        overdue_qs = qs.filter(
            deadline__lt=now,
        ).exclude(
            status__in=['COMPLETED', 'CANCELLED']
        ).select_related('assignee', 'creator').order_by('deadline')[:20]

        overdue_tasks = []
        for t in overdue_qs:
            overdue_tasks.append({
                'id': str(t.id),
                'task_no': t.task_no,
                'title': t.title,
                'priority': t.priority,
                'deadline': t.deadline.isoformat() if t.deadline else None,
                'is_overdue': t.is_overdue,
                'days_until_deadline': t.days_until_deadline,
                'assignee_name': t.assignee.display_name if t.assignee else '未分配',
                'assignee_id': str(t.assignee_id) if t.assignee_id else None,
                'creator_name': t.creator.display_name if t.creator else '',
                'days_label': _days_label(t.deadline),
            })

        return {
            'summary': summary,
            'monthly_team_points': {
                'total_points': monthly['total_points'] or 0,
                'completed_count': completed_count,
                'completion_rate': round(completed_count / total_tasks, 2) if total_tasks else 0,
            },
            'member_workload': member_workload,
            'overdue_tasks': overdue_tasks,
        }

    # ------------------------------------------------------------------
    # 缓存管理
    # ------------------------------------------------------------------

    @staticmethod
    def invalidate_user_cache(user_id):
        """清除指定用户的仪表盘缓存。"""
        cache.delete(f'dashboard:member:{user_id}')
        cache.delete(f'dashboard:leader:{user_id}')

    @staticmethod
    def invalidate_all_cache():
        """清除所有仪表盘缓存（谨慎使用）。"""
        from django.core.cache import cache as _cache
        _cache.clear()
