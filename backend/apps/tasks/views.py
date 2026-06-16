from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied

from common.permissions import IsOwnerOrLeader, IsGroupLeader
from common.pagination import StandardPagination
from .models import Task, TaskHistory, TaskComment
from .serializers import (
    TaskListSerializer, TaskDetailSerializer, TaskCreateSerializer,
    TaskTransitionSerializer, TaskProgressSerializer,
    TaskHistorySerializer, TaskCommentSerializer, TaskCommentCreateSerializer,
)
from .services.task_service import TaskService


class TaskListView(generics.ListCreateAPIView):
    """任务列表：支持筛选、搜索、分页。"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TaskCreateSerializer
        return TaskListSerializer

    def get_queryset(self):
        from django.db.models import Q, Count

        qs = Task.objects.select_related(
            'assignee', 'creator', 'reviewer'
        ).annotate(
            comments_count=Count('comments', distinct=True),
            files_count=Count('files', distinct=True),
        )

        # 数据隔离：非组长以上只看自己的任务
        user = self.request.user
        if not user.is_superuser and user.role not in ('LEADER', 'ADMIN'):
            qs = qs.filter(Q(assignee=user) | Q(creator=user))

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


class TaskProgressView(views.APIView):
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

        serializer = TaskProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = TaskService.update_progress(
            task, serializer.validated_data['progress'], request.user
        )
        return Response({'progress': task.progress})


class TaskClaimView(views.APIView):
    """揭榜挂帅 — 任务领取 API。"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            task = Task.objects.select_related('assignee', 'creator').get(pk=pk)
        except Task.DoesNotExist:
            return Response({'error': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 任务必须未分配且状态为 PENDING
        if task.assignee is not None:
            return Response({'error': '该任务已有负责人'}, status=status.HTTP_400_BAD_REQUEST)
        if task.status != Task.Status.PENDING:
            return Response({'error': '仅待领取状态的任务可领取'}, status=status.HTTP_400_BAD_REQUEST)
        # 创建人不能领取自己创建的任务
        if task.creator == request.user:
            return Response({'error': '不能领取自己创建的任务'}, status=status.HTTP_400_BAD_REQUEST)

        from apps.notifications.models import Notification
        from django.utils import timezone

        # 领取任务
        task.assignee = request.user
        task.status = Task.Status.IN_PROGRESS
        task.started_at = timezone.now()
        task.save(update_fields=['assignee', 'status', 'started_at', 'updated_at'])

        # 创建通知
        Notification.objects.create(
            recipient=request.user,
            type=Notification.Type.TASK_ASSIGNED,
            title=f'您已领取任务: {task.title}',
            content=f'任务编号: {task.task_no}',
            task=task,
            actor=request.user,
        )

        # 记录历史
        TaskHistory.objects.create(
            task=task,
            action=TaskHistory.Action.ASSIGNED,
            actor=request.user,
            old_value={'assignee': None, 'status': 'PENDING'},
            new_value={'assignee': str(request.user.id), 'status': 'IN_PROGRESS'},
            note='领取任务（揭榜挂帅）',
        )

        return Response(TaskDetailSerializer(task).data)


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

        task = Task.objects.get(pk=self.kwargs['pk'])
        comment = serializer.save(author=self.request.user, task=task)

        TaskHistory.objects.create(
            task=task,
            action=TaskHistory.Action.COMMENTED,
            actor=self.request.user,
            note=comment.content[:100],
        )

        # 评论通知：通知 assignee 和 creator（排除评论者本人）
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
            qs = qs.filter(Q(assignee=user) | Q(creator=user))

        # 单次查询，Python 层分组
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
