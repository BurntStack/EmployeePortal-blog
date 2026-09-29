from django.core.management.base import BaseCommand
from apps.blog.editorial import publish_due, send_reminders


class Command(BaseCommand):
    help = "Publish due approved revisions and send deduplicated overdue review reminders. Run every minute."

    def handle(self, *args, **options):
        self.stdout.write(f"Published {publish_due()} posts; checked {send_reminders()} overdue reviews.")
