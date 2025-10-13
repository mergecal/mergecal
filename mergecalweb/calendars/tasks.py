import logging

from celery import shared_task
from celery.utils.log import get_task_logger

from config import celery_app
from mergecalweb.calendars.models import Calendar
from mergecalweb.calendars.utils import combine_calendar

# Use Celery's task logger for better integration
task_logger = get_task_logger(__name__)
logger = logging.getLogger(__name__)

calendars = Calendar.objects.all()


@celery_app.task()
def combine_all_calendar_task():
    total_calendars = calendars.count()
    task_logger.info(
        "Celery task: Starting bulk calendar combine - total_calendars=%d",
        total_calendars,
    )

    queued = 0
    for cal in calendars:
        combine_calendar_task.delay(cal.id)
        queued += 1

    task_logger.info(
        "Celery task: Bulk calendar combine queued - queued=%d, total=%d",
        queued,
        total_calendars,
    )


@shared_task
def combine_calendar_task(cal_id):
    import time

    start_time = time.time()
    task_logger.info(
        "Celery task: Starting calendar combine - calendar_id=%s",
        cal_id,
    )

    try:
        calendar = Calendar.objects.get(pk=cal_id)
        task_logger.debug(
            "Celery task: Calendar loaded - calendar_id=%s, name=%s, owner=%s",
            cal_id,
            calendar.name,
            calendar.owner.username,
        )

        combine_calendar(calendar)

        duration = time.time() - start_time
        task_logger.info(
            "Celery task: Calendar combine SUCCESS - id=%s, name=%s, duration=%.2fs",
            cal_id,
            calendar.name,
            duration,
        )

    except Calendar.DoesNotExist:
        task_logger.exception(
            "Celery task: Calendar combine FAILED - calendar_id=%s not found",
            cal_id,
        )
        raise

    except Exception as e:
        duration = time.time() - start_time
        task_logger.exception(
            "Celery task: Calendar combine FAILED - id=%s, type=%s, duration=%.2fs",
            cal_id,
            type(e).__name__,
            duration,
        )
        raise
