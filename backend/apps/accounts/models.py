import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """自定义用户管理器，使用 email 作为登录标识。"""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('必须提供邮箱地址')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        return self.create_user(email, password, **extra_fields)


class Team(models.Model):
    """团队/小组。"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('团队名称', max_length=100, unique=True)
    description = models.TextField('描述', blank=True, default='')
    leader = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='led_teams', verbose_name='组长'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'teams'
        verbose_name = '团队'
        verbose_name_plural = verbose_name
        ordering = ['name']

    def __str__(self):
        return self.name


class User(AbstractUser):
    """自定义用户模型。"""

    class Role(models.TextChoices):
        MEMBER = 'MEMBER', '普通成员'
        LEADER = 'LEADER', '组长'
        ADMIN = 'ADMIN', '管理员'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField('邮箱', unique=True)
    phone = models.CharField('手机号', max_length=20, blank=True, default='')
    role = models.CharField(
        '角色', max_length=10, choices=Role.choices, default=Role.MEMBER
    )
    team = models.ForeignKey(
        Team, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='members', verbose_name='所属团队'
    )
    avatar = models.ImageField('头像', upload_to='avatars/', blank=True, default='')
    is_active = models.BooleanField('启用', default=True)
    last_login_ip = models.GenericIPAddressField('最后登录IP', null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        ordering = ['-date_joined']

    def __str__(self):
        return f'{self.username} ({self.email})'

    @property
    def is_leader_or_above(self):
        return self.is_superuser or self.role in (self.Role.LEADER, self.Role.ADMIN)

    @property
    def display_name(self):
        return self.get_full_name() or self.username
