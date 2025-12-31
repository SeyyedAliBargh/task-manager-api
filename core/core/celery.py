import os
from celery import Celery
from celery.schedules import crontab


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
app = Celery('myproject')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Schedules for tasks
app.conf.beat_schedule = {
    'delete-unverified-users-daily': {
        'task': 'accounts.tasks.delete_unverified_users',
        'schedule': crontab(hour=0, minute=0),  # every night at 00:00
    },
}
