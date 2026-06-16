from django.core.management.base import BaseCommand
from apps.accounts.models import User, Team


class Command(BaseCommand):
    help = '创建种子数据：默认团队和超级管理员'

    def add_arguments(self, parser):
        parser.add_argument('--admin-email', default='admin@vanguard.local')
        parser.add_argument('--admin-password', default='vanguard2026')

    def handle(self, *args, **options):
        email = options['admin_email']
        password = options['admin_password']

        # 创建默认团队
        team, created = Team.objects.get_or_create(
            name='尖兵部队',
            defaults={'description': '系统默认团队，所有新用户自动加入'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'创建团队: {team.name}'))

        # 创建超级管理员
        if not User.objects.filter(email=email).exists():
            user = User.objects.create_superuser(
                email=email,
                password=password,
                username='admin',
                team=team,
            )
            self.stdout.write(self.style.SUCCESS(
                f'创建超级管理员: {user.email} / 密码: {password}'
            ))
        else:
            self.stdout.write(self.style.WARNING(f'超级管理员已存在: {email}'))

        self.stdout.write(self.style.SUCCESS('种子数据初始化完成'))
