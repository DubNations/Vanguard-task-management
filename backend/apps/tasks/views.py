import logging

from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from common.permissions import IsOwnerOrLeader, IsGroupLeader
from common.pagination import StandardPagination
from .models import Task, TaskHistory, TaskComment, TaskParticipant
from .serializers import (
    TaskListSerializer, TaskDetailSerializer, TaskCreateSerializer,
    TaskTransitionSerializer, TaskProgressSerializer,
    TaskHistorySerializer, TaskCommentSerializer, TaskCommentCreateSerializer,
    TaskParticipantSerializer,
)
from .services.task_service import TaskService

logger = logging.getLogger(__name__)


class TaskListView(generics.ListCreateAPIView):
    """任务列表：支持筛选、搜索、分页。"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TaskCreateSerializer
        return TaskListSerializer

    def get_queryset(self):
        from django.db.models import Q, Count, Exists, OuterRef

        qs = Task.objects.select_related(
            'assignee', 'creator', 'reviewer'
        ).annotate(
            comments_count=Count('comments', distinct=True),
            files_count=Count('files', distinct=True),
            participants_count=Count('participants', distinct=True),
        )

        # 数据隔离：非组长以上只看自己的任务（包括参与的任务）
        user = self.request.user
        if not user.is_superuser and user.role not in ('LEADER', 'ADMIN'):
            participation_exists = Exists(
                TaskParticipant.objects.filter(
                    task=OuterRef('pk'), user=user
                )
            )
            qs = qs.filter(
                Q(assignee=user) | Q(creator=user) | participation_exists
            )

        # 筛选参数
        params = self.request.query_params
        status_val = params.get('status')
        if status_val:
            qs = qs.filter(status=status_val)
        priority_val = params.get('priority')
        if priority_val:
            qs = qs.filter(priority=priority_val)
        search_val = params.get('search')
        if search_val:
            qs = qs.filter(title__icontains=search_val)
        assignee_val = params.get('assignee')
        if assignee_val:
            qs = qs.filter(assignee_id=assignee_val)
        task_mode_val = params.get('task_mode')
        if task_mode_val:
            qs = qs.filter(task_mode=task_mode_val)

        # 排序
        ordering = params.get('ordering', '-created_at')
        allowed_ordering = {
            '-created_at', 'created_at',
            '-deadline', 'deadline',
            '-priority', 'priority',
            '-progress', 'progress',
        }
        if ordering not in allowed_ordering:
            ordering = '-created_at'
        qs = qs.order_by(ordering)

        return qs

    def perform_create(self, serializer):
        """任务创建权限收紧：仅 LEADER/ADMIN/superuser 可创建。"""
        user = self.request.user
        if not (user.is_superuser or user.role in ('LEADER', 'ADMIN')):
            raise PermissionDenied('仅组长及以上可创建任务')
        task = TaskService.create_task(
            serializer.validated_data, self.request.user
        )
        self._created_task = task

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            TaskDetailSerializer(self._created_task).data,
            status=status.HTTP_201_CREATED,
        )


class TaskDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, IsOwnerOrLeader]
    queryset = Task.objects.select_related('assignee', 'creator', 'reviewer').all()
    serializer_class = TaskDetailSerializer

    def perform_update(self, serializer):
        TaskService.update_task(
            serializer.instance, serializer.validated_data, self.request.user
        )


class TaskTransitionView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            task = Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            return Response({'error': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 对象级权限检查
        perm = IsOwnerOrLeader()
        if not perm.has_object_permission(request, self, task):
            raise PermissionDenied('您无权操作此任务')

        # 派发模式完成：仅总牵头人可触发
        new_status = request.data.get('status')
        if (new_status == Task.Status.COMPLETED
                and task.task_mode == Task.TaskMode.ASSIGNED):
            if not self._is_chief_lead(request.user, task):
                raise PermissionDenied('仅总牵头人可完成派发任务')

        serializer = TaskTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            task = TaskService.transition_status(
                task, serializer.validated_data['status'],
                request.user, serializer.validated_data.get('note', '')
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(TaskDetailSerializer(task).data)

    @staticmethod
    def _is_chief_lead(user, task):
        """检查用户是否为该任务的总牵头人。"""
        if user.is_superuser or user.role in ('LEADER', 'ADMIN'):
            return True
        if task.creator == user:
            return True
        return task.participants.filter(
            user=user,
            role=TaskParticipant.Role.CHIEF_LEAD,
            status__in=[TaskParticipant.Status.ACCEPTED, TaskParticipant.Status.COMPLETED],
        ).exists()


class TaskProgressView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            task = Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            return Response({'error': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)

        perm = IsOwnerOrLeader()
        if not perm.has_object_permission(request, self, task):
            raise PermissionDenied('您无权操作此任务')

        serializer = TaskProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = TaskService.update_progress(
            task, serializer.validated_data['progress'], request.user
        )
        return Response({'progress': task.progress})


class TaskClaimView(views.APIView):
    """揭榜挂帅 — 任务领取 API（支持自由揭榜 + 固定揭榜）。"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from django.db import transaction

        with transaction.atomic():
            try:
                task = Task.objects.select_for_update().get(pk=pk)
            except Task.DoesNotExist:
                return Response({'error': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)

            # 任务必须是可领取模式
            if task.task_mode not in (Task.TaskMode.FREE_CLAIM, Task.TaskMode.FIXED_CLAIM):
                return Response({'error': '该任务非揭榜模式'}, status=status.HTTP_400_BAD_REQUEST)

            # 创建人不能领取自己创建的任务
            if task.creator == request.user:
                return Response({'error': '不能领取自己创建的任务'}, status=status.HTTP_400_BAD_REQUEST)

            # 已领取过
            if TaskParticipant.objects.filter(task=task, user=request.user).exists():
                return Response({'error': '您已领取过该任务'}, status=status.HTTP_400_BAD_REQUEST)

            # 固定揭榜：名额校验
            if task.task_mode == Task.TaskMode.FIXED_CLAIM:
                if task.max_claimers and task.current_claimers >= task.max_claimers:
                    return Response({'error': '名额已满，无法领取'}, status=status.HTTP_400_BAD_REQUEST)

        from django.utils import timezone

        # 创建参与者记录
        participant = TaskParticipant.objects.create(
            task=task,
            user=request.user,
            role=TaskParticipant.Role.CLAIMER,
            points=task.reward_points,
            status=TaskParticipant.Status.ACCEPTED,
        )

        # 更新已领取人数
        task.current_claimers += 1
        task.save(update_fields=['current_claimers', 'updated_at'])

        # 通知创建人
        from apps.notifications.models import Notification
        try:
            claimer_name = request.user.display_name or request.user.username
            Notification.objects.create(
                recipient=task.creator,
                type=Notification.Type.TASK_ASSIGNED,
                title=f'任务被领取: {task.title}',
                content=f'{claimer_name} 领取了任务 ({task.current_claimers}/{task.max_claimers or "不限"})',
                task=task,
                actor=request.user,
            )
        except Exception:
            logger.warning('领取通知发送失败: task=%s user=%s', task.task_no, request.user.pk, exc_info=True)

        # 固定揭榜：额满通知
        if (task.task_mode == Task.TaskMode.FIXED_CLAIM
                and task.max_claimers
                and task.current_claimers >= task.max_claimers):
            try:
                Notification.objects.create(
                    recipient=task.creator,
                    type=Notification.Type.TASK_STATUS,
                    title=f'名额已满: {task.title}',
                    content=f'任务 {task.task_no} 领取名额已满 ({task.current_claimers}/{task.max_claimers})',
                    task=task,
                    actor=request.user,
                )
            except Exception:
                logger.warning('额满通知发送失败: task=%s', task.task_no, exc_info=True)

        # 记录历史
        TaskHistory.objects.create(
            task=task,
            action=TaskHistory.Action.ASSIGNED,
            actor=request.user,
            old_value={'status': task.status},
            new_value={'current_claimers': task.current_claimers},
            note=f'领取任务（{task.get_task_mode_display()}）',
        )

        return Response(TaskParticipantSerializer(participant).data, status=status.HTTP_201_CREATED)


class TaskParticipantListView(generics.ListCreateAPIView):
    """任务参与者列表 / 添加参与者（仅派发模式）。"""
    permission_classes = [IsAuthenticated]
    serializer_class = TaskParticipantSerializer

    def get_queryset(self):
        return TaskParticipant.objects.filter(
            task_id=self.kwargs['pk']
        ).select_related('user')

    def perform_create(self, serializer):
        try:
            task = Task.objects.get(pk=self.kwargs['pk'])
        except Task.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound('任务不存在')

        if task.task_mode != Task.TaskMode.ASSIGNED:
            raise PermissionDenied('仅派发模式可添加参与者')

        user = self.request.user
        if not (user.is_superuser or user.role in ('LEADER', 'ADMIN')
                or task.creator == user):
            raise PermissionDenied('无权添加参与者')

        participant = serializer.save(task=task)
        self._participant = participant

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            TaskParticipantSerializer(self._participant).data,
            status=status.HTTP_201_CREATED,
        )


class TaskParticipantDetailView(views.APIView):
    """修改/移除参与者。"""
    permission_classes = [IsAuthenticated]

    def put(self, request, pk, pid):
        try:
            task = Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            return Response({'error': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)

        try:
            participant = TaskParticipant.objects.get(pk=pid, task=task)
        except TaskParticipant.DoesNotExist:
            return Response({'error': '参与者不存在'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if not (user.is_superuser or user.role in ('LEADER', 'ADMIN')
                or task.creator == user):
            raise PermissionDenied('无权修改参与者')

        role = request.data.get('role', participant.role)
        points = request.data.get('points', participant.points)
        participant.role = role
        participant.points = points
        participant.save(update_fields=['role', 'points'])

        return Response(TaskParticipantSerializer(participant).data)

    def delete(self, request, pk, pid):
        try:
            task = Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            return Response({'error': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)

        try:
            participant = TaskParticipant.objects.get(pk=pid, task=task)
        except TaskParticipant.DoesNotExist:
            return Response({'error': '参与者不存在'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if not (user.is_superuser or user.role in ('LEADER', 'ADMIN')
                or task.creator == user):
            raise PermissionDenied('无权移除参与者')

        participant.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskParticipantCompleteView(views.APIView):
    """管理员/发布者判定揭榜领取人完成 → 发放积分。"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, pid):
        try:
            task = Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            return Response({'error': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)

        if task.task_mode not in (Task.TaskMode.FREE_CLAIM, Task.TaskMode.FIXED_CLAIM):
            return Response({'error': '仅揭榜模式可执行此操作'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            participant = TaskParticipant.objects.get(pk=pid, task=task)
        except TaskParticipant.DoesNotExist:
            return Response({'error': '参与者不存在'}, status=status.HTTP_404_NOT_FOUND)

        if participant.status == TaskParticipant.Status.COMPLETED:
            return Response({'error': '该参与者已完成'}, status=status.HTTP_400_BAD_REQUEST)

        # 权限：管理员、创建人、发布者可判定
        user = request.user
        if not (user.is_superuser or user.role in ('LEADER', 'ADMIN')
                or task.creator == user):
            raise PermissionDenied('无权判定完成')

        from django.utils import timezone
        from apps.points.services.point_service import PointService

        # 标记完成
        participant.status = TaskParticipant.Status.COMPLETED
        participant.completed_at = timezone.now()
        participant.save(update_fields=['status', 'completed_at'])

        # 发放积分
        try:
            PointService.award(
                participant.user, task,
                action='TASK_COMPLETED',
                points=participant.points,
                reason=f'[揭榜] {task.task_no} 完成',
            )
        except Exception:
            logger.warning('积分发放失败: task=%s user=%s', task.task_no, participant.user.pk, exc_info=True)

        # 记录历史
        TaskHistory.objects.create(
            task=task,
            action=TaskHistory.Action.STATUS_CHANGE,
            actor=user,
            old_value={'participant_status': participant.status},
            new_value={'participant_status': TaskParticipant.Status.COMPLETED},
            note=f'判定 {participant.user.username} 完成揭榜任务',
        )

        # 通知领取人
        from apps.notifications.models import Notification
        try:
            Notification.objects.create(
                recipient=participant.user,
                type=Notification.Type.TASK_STATUS,
                title=f'任务确认完成: {task.title}',
                content=f'积分 {participant.points} 已发放',
                task=task,
                actor=user,
            )
        except Exception:
            logger.warning('完成通知发送失败: task=%s user=%s', task.task_no, participant.user.pk, exc_info=True)

        return Response(TaskParticipantSerializer(participant).data)


class TaskHistoryListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TaskHistorySerializer

    def get_queryset(self):
        from django.db.models import Q
        user = self.request.user
        qs = TaskHistory.objects.filter(
            task_id=self.kwargs['pk']
        ).select_related('actor')
        # 数据隔离：非相关人员不可查看
        if not user.is_superuser and user.role not in ('LEADER', 'ADMIN'):
            try:
                task = Task.objects.get(pk=self.kwargs['pk'])
                if task.assignee != user and task.creator != user:
                    # 检查是否为参与者
                    if not TaskParticipant.objects.filter(task=task, user=user).exists():
                        return qs.none()
            except Task.DoesNotExist:
                return qs.none()
        return qs


class TaskCommentListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TaskCommentCreateSerializer
        return TaskCommentSerializer

    def get_queryset(self):
        qs = TaskComment.objects.filter(task_id=self.kwargs['pk']).select_related('author')
        user = self.request.user
        if not user.is_superuser and user.role not in ('LEADER', 'ADMIN'):
            qs = qs.filter(is_internal=False)
        return qs

    def perform_create(self, serializer):
        from apps.notifications.models import Notification

        try:
            task = Task.objects.get(pk=self.kwargs['pk'])
        except Task.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound('任务不存在')
        comment = serializer.save(author=self.request.user, task=task)

        TaskHistory.objects.create(
            task=task,
            action=TaskHistory.Action.COMMENTED,
            actor=self.request.user,
            note=comment.content[:100],
        )

        recipients = set()
        if task.assignee and task.assignee != self.request.user:
            recipients.add(task.assignee)
        if task.creator and task.creator != self.request.user:
            recipients.add(task.creator)
        for recipient in recipients:
            Notification.objects.create(
                recipient=recipient,
                type=Notification.Type.TASK_COMMENT,
                title=f'新评论: {task.title}',
                content=f'{self.request.user.display_name}: {comment.content[:50]}',
                task=task,
                actor=self.request.user,
            )


class KanbanView(views.APIView):
    """看板视图：按状态分组的任务（单次查询 + Python 层分组）。"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Q

        qs = Task.objects.select_related('assignee', 'creator').exclude(
            status__in=['CANCELLED']
        )

        user = request.user
        if not user.is_superuser and user.role not in ('LEADER', 'ADMIN'):
            participation_q = Q(participants__user=user)
            qs = qs.filter(Q(assignee=user) | Q(creator=user) | participation_q).distinct()

        all_tasks = list(qs.order_by('status', '-priority', '-created_at')[:200])

        columns = {}
        for status_choice in Task.Status.choices:
            key = status_choice[0]
            tasks_in_col = [t for t in all_tasks if t.status == key][:20]
            columns[key] = {
                'label': status_choice[1],
                'count': len([t for t in all_tasks if t.status == key]),
                'tasks': TaskListSerializer(tasks_in_col, many=True).data,
            }

        return Response(columns)
