from config import celery_app

from .models import Calendar
from .utils import combine_calendar

calendars = Calendar.objects.all()


@celery_app.task()
def combine_all_calendar_task():
    for cal in calendars:
        combine_calendar(cal)
