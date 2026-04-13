import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enlidea.settings')

app = Celery('enlidea')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@app.task(bind=True)
def debug_task(self):
    logger.info(f'Request: {self.request!r}')
