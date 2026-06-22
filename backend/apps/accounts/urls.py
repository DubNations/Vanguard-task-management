from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LoginView, LogoutView, MeView, ChangePasswordView,
    UserListView, UserDetailView, UserToggleActiveView, UserResetPasswordView,
    TeamListCreateView, TeamDetailView,
)

urlpatterns = [
    # Authentication
    path('login/', LoginView.as_view(), name='auth-login'),
    path('refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('me/', MeView.as_view(), name='auth-me'),
    path('password/', ChangePasswordView.as_view(), name='auth-password'),

    # User management (admin)
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<uuid:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('users/<uuid:pk>/toggle/', UserToggleActiveView.as_view(), name='user-toggle'),
    path('users/<uuid:pk>/reset-password/', UserResetPasswordView.as_view(), name='user-reset-password'),

    # Teams
    path('teams/', TeamListCreateView.as_view(), name='team-list'),
    path('teams/<uuid:pk>/', TeamDetailView.as_view(), name='team-detail'),
]
