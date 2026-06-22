import os
os.environ['DJANGO_ENV'] = 'local'
os.environ['DJANGO_SECRET_KEY'] = 'dev'
os.environ['JWT_SIGNING_KEY'] = 'dev'
os.environ['DJANGO_SETTINGS_MODULE'] = 'seedteam.settings'

import django
django.setup()

from apps.tasks.models import Task, TaskParticipant
from apps.tasks.serializers import TaskListSerializer
from apps.tasks.services.task_service import TaskService
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

User = get_user_model()
leader = User.objects.get(email='leader@seedteam.local')
member = User.objects.get(email='member@seedteam.local')

# Cleanup old test tasks
Task.objects.filter(title__startswith='【测试领取】').delete()
print('Cleaned up old test tasks')

# Create fresh FREE_CLAIM task as leader
task = TaskService.create_task({
    'title': '【调试】FREE_CLAIM',
    'description': 'test',
    'priority': 'MEDIUM',
    'task_mode': 'FREE_CLAIM',
    'reward_points': 100,
}, leader)
print(f'Created task: id={task.id} mode={task.task_mode} status={task.status}')

# Test serializer with member context
factory = APIRequestFactory()
request = factory.get('/api/v1/tasks/')
request.user = member

s = TaskListSerializer(task, context={'request': request})
print(f'can_claim with member context: {s.data.get("can_claim")}')

# Debug step by step
print(f'\n--- Debug get_can_claim ---')
print(f'task_mode: {task.task_mode}')
print(f'status: {task.status}')
print(f'creator_id: {task.creator_id}')
print(f'member.id: {member.id}')
print(f'creator == member: {task.creator_id == member.id}')
print(f'TaskParticipant exists: {TaskParticipant.objects.filter(task=task, user=member).exists()}')

# Check what happens in the list view queryset for member
from django.db.models import Q, Count, Exists, OuterRef
qs = Task.objects.select_related('assignee', 'creator', 'reviewer').annotate(
    comments_count=Count('comments', distinct=True),
    files_count=Count('files', distinct=True),
    participants_count=Count('participants', distinct=True),
)
participation_exists = Exists(
    TaskParticipant.objects.filter(task=OuterRef('pk'), user=member)
)
member_qs = qs.filter(
    Q(assignee=member) | Q(creator=member) | participation_exists | Q(status=Task.Status.PENDING)
).distinct()
print(f'\nMember visible tasks: {member_qs.count()}')
for t in member_qs:
    s2 = TaskListSerializer(t, context={'request': request})
    print(f'  {t.title} mode={t.task_mode} status={t.status} can_claim={s2.data.get("can_claim")}')
