import logging
import time

from celery import shared_task
from celery.utils.log import get_task_logger

from config import celery_app
from mergecalweb.calendars.models import Calendar
from mergecalweb.calendars.utils import combine_calendar

# Use Celery's task logger for better integration
task_logger = get_task_logger(__name__)
logger = logging.getLogger(__name__)


@celery_app.task()
def combine_all_calendar_task():
    # Fetch calendars at task execution time, not module load time
    calendars = Calendar.objects.all()
    total_calendars = calendars.count()

    task_logger.info(
        "Starting bulk calendar combine task",
        extra={
            "event": "bulk_calendar_combine_start",
            "total_calendars": total_calendars,
        },
    )

    queued = 0
    for cal in calendars:
        combine_calendar_task.delay(cal.id)
        queued += 1

    task_logger.info(
        "Bulk calendar combine tasks queued",
        extra={
            "event": "bulk_calendar_combine_queued",
            "queued": queued,
            "total_calendars": total_calendars,
        },
    )


@shared_task
def combine_calendar_task(cal_id):
    start_time = time.time()
    task_logger.info(
        "Starting calendar combine task",
        extra={
            "event": "calendar_combine_task_start",
            "calendar_id": cal_id,
        },
    )

    try:
        calendar = Calendar.objects.get(pk=cal_id)
        task_logger.debug(
            "Calendar loaded for combine task",
            extra={
                "event": "calendar_combine_loaded",
                "calendar_id": cal_id,
                "calendar_uuid": calendar.uuid,
                "calendar_name": calendar.name,
                "owner_id": calendar.owner.pk,
                "owner_username": calendar.owner.username,
            },
        )

        combine_calendar(calendar)

        duration = time.time() - start_time
        task_logger.info(
            "Calendar combine task completed successfully",
            extra={
                "event": "calendar_combine_task_success",
                "calendar_id": cal_id,
                "calendar_uuid": calendar.uuid,
                "calendar_name": calendar.name,
                "duration_seconds": round(duration, 2),
            },
        )

    except Calendar.DoesNotExist:
        task_logger.exception(
            "Calendar combine task failed, calendar not found",
            extra={
                "event": "calendar_combine_task_not_found",
                "calendar_id": cal_id,
            },
        )
        raise

    except Exception as e:
        duration = time.time() - start_time
        task_logger.exception(
            "Calendar combine task failed with error",
            extra={
                "event": "calendar_combine_task_error",
                "calendar_id": cal_id,
                "error_type": type(e).__name__,
                "duration_seconds": round(duration, 2),
            },
        )
        raise
