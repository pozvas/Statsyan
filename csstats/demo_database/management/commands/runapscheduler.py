import logging

from django.conf import settings

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from django.core.management.base import BaseCommand
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django_apscheduler import util
from demo_database.tasks import get_new_sharecodes, get_and_analize_new_demos

logger = logging.getLogger(__name__)


@util.close_old_connections
def get_and_analize_new_demos_job():
    get_and_analize_new_demos()


@util.close_old_connections
def delete_old_job_executions(max_age=604_800):
    DjangoJobExecution.objects.delete_old_job_executions(max_age)


class Command(BaseCommand):
    help = "Runs APScheduler."

    def handle(self, *args, **options):
        executors = {
            "default": ThreadPoolExecutor(20),
            "processpool": ProcessPoolExecutor(5),
        }
        scheduler = BackgroundScheduler(executors=executors)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        scheduler.add_job(
            get_and_analize_new_demos_job,
            "cron",
            hour=00,
            minute=00,
            id="get_and_analize_new_demos",
            replace_existing=True,
        )
        logger.info("Added job 'get_and_analize_new_demos_job'.")

        scheduler.add_job(
            delete_old_job_executions,
            trigger=CronTrigger(day_of_week="mon", hour="00", minute="00"),
            id="delete_old_job_executions",
            max_instances=1,
            replace_existing=True,
        )
        logger.info("Added weekly job: 'delete_old_job_executions'.")

        try:
            logger.info("Starting scheduler...")
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            scheduler.shutdown()
            logger.info("Scheduler shut down successfully!")
