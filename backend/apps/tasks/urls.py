from django.urls import path
from .views import (
    TaskListView, TaskDetailView,
    TaskTransitionView, TaskProgressView,
    TaskHistoryListView, TaskCommentListView,
    TaskClaimView, KanbanView,
)

urlpatterns = [
    path('', TaskListView.as_view(), name='task-list'),
    path('kanban/', KanbanView.as_view(), name='task-kanban'),
    path('<uuid:pk>/', TaskDetailView.as_view(), name='task-detail'),
    path('<uuid:pk>/transition/', TaskTransitionView.as_view(), name='task-transition'),
    path('<uuid:pk>/progress/', TaskProgressView.as_view(), name='task-progress'),
    path('<uuid:pk>/history/', TaskHistoryListView.as_view(), name='task-history'),
    path('<uuid:pk>/comments/', TaskCommentListView.as_view(), name='task-comments'),
    path('<uuid:pk>/claim/', TaskClaimView.as_view(), name='task-claim'),
]
