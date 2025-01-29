from celery import shared_task

from config import celery_app
from mergecalweb.calendars.models import Calendar
from mergecalweb.calendars.utils import combine_calendar

calendars = Calendar.objects.all()


@celery_app.task()
def combine_all_calendar_task():
    for cal in calendars:
        combine_calendar_task.delay(cal.id)


@shared_task
def combine_calendar_task(cal_id):
    calendar = Calendar.objects.get(pk=cal_id)
    combine_calendar(calendar)
