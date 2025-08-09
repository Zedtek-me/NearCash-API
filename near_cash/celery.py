import os
import logging
from celery import Celery, Task

from utils.helpers.logs import logger

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'near_cash.settings')

class BaseTask(Task):
    """Base task class for all Celery tasks."""

    retry_backoff = True
    autoretry_for = (Exception,)
    max_retries = 5

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.exception(f"Task {self.name} failed: {exc}")
        super().on_failure(exc, task_id, args, kwargs, einfo)


app = Celery(
    'near_cash', 
    include=["background_tasks"],
    task_cls=BaseTask,
    namespace="CELERY"
)

app.config_from_object("django.conf:settings")
app.autodiscover_tasks()
