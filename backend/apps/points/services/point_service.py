"""
积分服务 — 积分发放、扣除、排行榜。
"""
from django.db import transaction
from django.db.models import Sum, F, Q
from django.utils import timezone
from datetime import timedelta

from apps.points.models import PointBalance, PointRule, PointTransaction


class PointService:
    """积分核心业务逻辑。"""

    PRIORITY_WEIGHT = {
        'URGENT': 4,
        'HIGH': 3,
        'MEDIUM': 2,
        'LOW': 1,
    }

    @staticmethod
    def _get_or_create_balance(user):
        balance, _ = PointBalance.objects.get_or_create(user=user)
        return balance

    @staticmethod
    def _calculate_points(action, task=None):
        """按规则计算积分。"""
        try:
            rule = PointRule.objects.get(action=action, is_active=True)
        except PointRule.DoesNotExist:
            # 默认规则
            base = 10
            if task and hasattr(task, 'reward_points') and task.reward_points > 0:
                return task.reward_points
            return base

        if rule.mode == PointRule.Mode.CUSTOM:
            # 自定义模式优先使用任务自带积分
            if task and hasattr(task, 'reward_points') and task.reward_points > 0:
                return task.reward_points
            return rule.base_points

        if rule.mode == PointRule.Mode.PRIORITY_BASED:
            multiplier = 1
            if task:
                multiplier = PointService.PRIORITY_WEIGHT.get(task.priority, 1)
            return int(rule.base_points * multiplier * rule.priority_multiplier)

        # FIXED
        if task and hasattr(task, 'reward_points') and task.reward_points > 0:
            return task.reward_points
        return rule.base_points

    @staticmethod
    @transaction.atomic
    def award(user, task=None, action='TASK_COMPLETED', reason=''):
        """发放积分。"""
        points = PointService._calculate_points(action, task)
        if points <= 0:
            return 0

        balance = PointService._get_or_create_balance(user)
        balance.total_earned += points
        balance.balance += points
        balance.save()

        PointTransaction.objects.create(
            user=user,
            type=PointTransaction.Type.EARN,
            points=points,
            balance_after=balance.balance,
            reason=reason or f'动作: {action}',
            task=task,
        )

        return points

    @staticmethod
    @transaction.atomic
    def deduct(user, task=None, action='', points=0, reason=''):
        """扣除积分。"""
        if points <= 0:
            return 0

        balance = PointService._get_or_create_balance(user)
        actual = min(points, balance.balance)
        if actual <= 0:
            return 0

        balance.total_spent += actual
        balance.balance -= actual
        balance.save()

        PointTransaction.objects.create(
            user=user,
            type=PointTransaction.Type.DEDUCT,
            points=actual,
            balance_after=balance.balance,
            reason=reason or f'扣除: {action}',
            task=task,
        )

        return actual

    @staticmethod
    def get_balance(user):
        """获取用户积分余额。"""
        balance = PointService._get_or_create_balance(user)
        return {
            'balance': balance.balance,
            'total_earned': balance.total_earned,
            'total_spent': balance.total_spent,
        }

    @staticmethod
    def get_transactions(user, page=1, page_size=20):
        """获取积分流水。"""
        qs = PointTransaction.objects.filter(user=user).select_related('task')
        total = qs.count()
        qs = qs[(page - 1) * page_size:page * page_size]
        results = [{
            'id': str(t.id),
            'type': t.type,
            'points': t.points,
            'balance_after': t.balance_after,
            'reason': t.reason,
            'task_no': t.task.task_no if t.task else None,
            'task_title': t.task.title if t.task else None,
            'created_at': t.created_at.isoformat(),
        } for t in qs]
        return {'count': total, 'results': results}

    @staticmethod
    def get_leaderboard(period='all', limit=20):
        """排行榜。"""
        from apps.accounts.models import User

        qs = PointBalance.objects.select_related('user', 'user__team').filter(
            total_earned__gt=0
        )

        if period == 'week':
            week_ago = timezone.now() - timedelta(days=7)
            weekly = PointTransaction.objects.filter(
                type=PointTransaction.Type.EARN,
                created_at__gte=week_ago,
            ).values('user_id', 'user__username', 'user__team__name').annotate(
                weekly_points=Sum('points')
            ).order_by('-weekly_points')[:limit]
            return [{
                'rank': i + 1,
                'user_id': str(u['user_id']),
                'username': u['user__username'],
                'team_name': u['user__team__name'] or '',
                'points': u['weekly_points'] or 0,
            } for i, u in enumerate(weekly)]

        if period == 'month':
            month_ago = timezone.now() - timedelta(days=30)
            monthly = PointTransaction.objects.filter(
                type=PointTransaction.Type.EARN,
                created_at__gte=month_ago,
            ).values('user_id', 'user__username', 'user__team__name').annotate(
                monthly_points=Sum('points')
            ).order_by('-monthly_points')[:limit]
            return [{
                'rank': i + 1,
                'user_id': str(u['user_id']),
                'username': u['user__username'],
                'team_name': u['user__team__name'] or '',
                'points': u['monthly_points'] or 0,
            } for i, u in enumerate(monthly)]

        # all time
        qs = qs.order_by('-total_earned')[:limit]
        return [{
            'rank': i + 1,
            'user_id': str(b.user.id),
            'username': b.user.username,
            'team_name': b.user.team.name if b.user.team else '',
            'points': b.total_earned,
        } for i, b in enumerate(qs)]

    @staticmethod
    def get_stats(user):
        """个人积分统计。"""
        balance_data = PointService.get_balance(user)
        now = timezone.now()
        week_ago = now - timedelta(days=7)

        weekly_earned = PointTransaction.objects.filter(
            user=user, type=PointTransaction.Type.EARN,
            created_at__gte=week_ago,
        ).aggregate(total=Sum('points'))['total'] or 0

        return {
            **balance_data,
            'weekly_earned': weekly_earned,
            'rank': PointBalance.objects.filter(
                total_earned__gt=balance_data['total_earned']
            ).count() + 1 if balance_data['total_earned'] > 0 else None,
        }
