import os
from django.core.management import call_command
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def startup_scheduler(sender, **kwargs):
    if sender.name == "demo_database":
        from django.conf import settings

        if not settings.DEBUG or os.environ.get("RUN_MAIN") == "true":
            call_command("runapscheduler")
