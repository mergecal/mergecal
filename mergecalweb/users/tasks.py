import logging

from celery import shared_task

from .models import User

logger = logging.getLogger(__name__)


@shared_task()
def get_users_count():
    """A pointless Celery task to demonstrate usage."""
    user_count = User.objects.count()
    logger.info(
        "Celery task executed successfully",
        extra={
            "task_name": "get_users_count",
            "user_count": user_count,
        },
    )
    return user_count
