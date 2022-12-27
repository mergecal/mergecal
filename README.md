# Calmerge
a Django app to merge ical feeds

Available at https://calmerge.habet.dev/

### Explanation
Every so often the web-app fetch's the events from all the given ical feeds, merges them into a single calendar and saves it to the database

The web-app then exposes a copy-able link which leads to a downloadable file containing the merged events from the database

The magic happens when you put that link in your calendar client like google calendar
where the events simply show up

Here's a [blog post](https://happyandeffective.notion.site/Blog-Post-Draft-Community-Calendars-897779ae1fb041d3a2e4a6b8829b1deb) written by [Casey Watts](https://github.com/caseywatts) detailing the problem and multiple approaches how to solve it.
### Deployment

![Project-Diagram](https://user-images.githubusercontent.com/82916197/205155655-4371301d-b5f7-42dc-a210-518e161c314e.png)


The following details how to deploy this application.


### Development

Fork and clone this repo

Create a virtual environment:
```
virtualenv env
```
Activate the environment:
```
source env/bin/activate
```
Install the dependencies:
```
pip install -r requirements/local.txt
```
Run the migrations:
```
python manage.py migrate
```
Start the server:
```
python manage.py runserver
```

This app comes with Celery.

To run a celery worker with celerybeat:

``` bash
celery -A config.celery_app worker -l info
```
```bash
celery -A config.celery_app beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Black code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

License: MIT
