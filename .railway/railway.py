from railway_sdk import database
from railway_sdk import define_railway
from railway_sdk import github
from railway_sdk import project
from railway_sdk import redis
from railway_sdk import service
from railway_sdk import volume


@define_railway
def main(ctx=None):
    mergecal = github("mergecal/mergecal", branch="main", checkSuites=True)

    postgres_db = database(
        "Postgres",
        "postgres",
        image="ghcr.io/railwayapp-templates/postgres-ssl:17",
        region="us-east4-eqdc4a",
    )
    postgres_db = postgres_db.with_fields(
        deploy={"multiRegionConfig": {"us-east4-eqdc4a": {"numReplicas": 1}}},
    )
    redis_db = redis("Redis", region="us-east4-eqdc4a")
    redis_db = redis_db.with_fields(
        deploy={
            "multiRegionConfig": {"us-east4-eqdc4a": {"numReplicas": 1}},
            "startCommand": '/bin/sh -c "rm -rf $RAILWAY_VOLUME_MOUNT_PATH/lost+found/ && exec docker-entrypoint.sh redis-server --requirepass $REDIS_PASSWORD --save 60 1 --dir $RAILWAY_VOLUME_MOUNT_PATH"',
        },
    )
    postgres_volume = volume(
        "postgres-volume",
        {
            "alerts": {"usage": {"100": {}, "80": {}, "95": {}}},
            "allowOnlineResize": True,
            "region": "us-east4-eqdc4a",
            "sizeMB": 5000,
        },
    )
    redis_volume = volume(
        "redis-volume",
        {
            "alerts": {"usage": {"100": {}, "80": {}, "95": {}}},
            "allowOnlineResize": True,
            "region": "us-east4-eqdc4a",
            "sizeMB": 5000,
        },
    )
    beat = service(
        "Beat",
        build={"builder": "NIXPACKS"},
        start="REMAP_SIGTERM=SIGQUIT celery -A config.celery_app worker --beat --scheduler django --loglevel=info --concurrency 2",
        replicas={"us-east4-eqdc4a": 1},
        networking={"privateNetworkEndpoint": "beat"},
    )
    celery = service(
        "Celery",
        build={"builder": "RAILPACK"},
        start="celery -A liftoff mergecalweb -l info --concurrency=3",
        replicas={"us-east4-eqdc4a": 1},
        networking={"privateNetworkEndpoint": "virtuous-integrity"},
    )
    prefetch_cron = service(
        "mergecal prefetch calendars",
        source=mergecal,
        build={"buildEnvironment": "V3", "builder": "RAILPACK"},
        start="python manage.py prefetch_calendars",
        replicas={"us-east4-eqdc4a": 1},
        deploy={"cronSchedule": "*/30 * * * *", "restartPolicyType": "NEVER"},
        networking={"privateNetworkEndpoint": "mergecal-prefetch-calendars"},
    )
    web = service(
        "mergecal",
        source=github("mergecal/mergecal", branch="main", checkSuites=False),
        build={
            "builder": "RAILPACK",
            "buildCommand": "python manage.py collectstatic --noinput && python manage.py compress --force",
        },
        start="gunicorn config.wsgi:application --timeout 60",
        preDeploy="python manage.py migrate",
        healthcheck="/ht/",
        replicas={"us-east4-eqdc4a": 1},
        domains=[{"domain": "mergecal.org", "port": 8080}],
    )
    return project(
        "mergecal",
        variables={"managed": False},
        resources=[
            postgres_db,
            beat,
            celery,
            prefetch_cron,
            redis_db,
            web,
            postgres_volume,
            redis_volume,
        ],
    )
