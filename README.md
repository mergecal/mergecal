# calmerge

Merge multiple external calendars into a single sharable calendar

Availabe at https://calmerge.habet.dev/


### Development

Fork and clone this repo

Create a virtual environtment:   
```
virtualenv env
```
Activate the environtment:
```
source env/bin/activate
```
Install the dependancies:
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

### Deployment

![Project-Diagram](https://user-images.githubusercontent.com/82916197/205155655-4371301d-b5f7-42dc-a210-518e161c314e.png)


The following details how to deploy this application.

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Black code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

License: MIT

