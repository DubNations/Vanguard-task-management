"""
管理命令：注册 django-q2 定时任务。

用法:
    python manage.py register_scheduled_tasks          # 注册全部
    python manage.py register_scheduled_tasks --clear  # 清除旧的再注册
"""
from django.core.management.base import BaseCommand


# 定时任务定义
SCHEDULED_TASKS = [
    {
        'name': 'check_overdue_tasks',
        'func': 'apps.tasks.scheduled_tasks.check_overdue_tasks',
        'schedule_type': 'C',  # Cron
        'cron': '0 */2 * * *',  # 每2小时检查一次
        'description': '检查逾期任务并发送提醒',
    },
    {
        'name': 'check_upcoming_deadlines',
        'func': 'apps.tasks.scheduled_tasks.check_upcoming_deadlines',
        'schedule_type': 'C',  # Cron
        'cron': '30 8 * * *',  # 每天 8:30
        'description': '检查24小时内到期的任务',
    },
    {
        'name': 'send_daily_digest_emails',
        'func': 'apps.tasks.scheduled_tasks.send_daily_digest_emails',
        'schedule_type': 'C',  # Cron
        'cron': '0 9 * * 1-5',  # 工作日 9:00
        'description': '发送每日任务摘要邮件',
    },
]


class Command(BaseCommand):
    help = '注册 django-q2 定时任务到 Schedule 表'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='先清除所有已注册的种子团队定时任务',
        )

    def handle(self, *args, **options):
        from django_q.models import Schedule

        if options['clear']:
            deleted_count = 0
            for task_def in SCHEDULED_TASKS:
                count, _ = Schedule.objects.filter(name=task_def['name']).delete()
                deleted_count += count
            self.stdout.write(self.style.WARNING(f'已清除 {deleted_count} 个旧定时任务'))

        for task_def in SCHEDULED_TASKS:
            # 检查是否已存在
            existing = Schedule.objects.filter(name=task_def['name']).first()
            if existing:
                self.stdout.write(self.style.WARNING(f'跳过已存在: {task_def["name"]}'))
                continue

            Schedule.objects.create(
                name=task_def['name'],
                func=task_def['func'],
                schedule_type=task_def['schedule_type'],
                cron=task_def['cron'],
            )
            self.stdout.write(self.style.SUCCESS(
                f'注册: {task_def["name"]} ({task_def["cron"]}) - {task_def["description"]}'
            ))

        total = Schedule.objects.count()
        self.stdout.write(self.style.SUCCESS(f'\n定时任务注册完成，当前共 {total} 个定时任务'))
        self.stdout.write(self.style.SUCCESS('启动 worker: python manage.py qcluster'))
