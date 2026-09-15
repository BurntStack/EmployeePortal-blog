"""Create fixed dev/test accounts for local development and the E2E suite.

Not for production use — passwords are fixed and public in this file.

Usage:  python manage.py create_test_accounts
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

ACCOUNTS = [
    {"username": "admin", "password": "AdminPass123!", "first_name": "Carol", "last_name": "Admin", "is_staff": True},
    {"username": "alice.employee", "password": "EmployeePass123!", "first_name": "Alice", "last_name": "Employee"},
    {"username": "bob.employee", "password": "EmployeePass123!", "first_name": "Bob", "last_name": "Employee"},
]


class Command(BaseCommand):
    help = "Idempotently create fixed dev/test accounts (local development and E2E only)."

    def handle(self, *args, **options):
        for account in ACCOUNTS:
            username = account["username"]
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": account["first_name"],
                    "last_name": account["last_name"],
                    "is_staff": account.get("is_staff", False),
                },
            )
            user.set_password(account["password"])
            user.is_staff = account.get("is_staff", False)
            user.save()
            status = "created" if created else "updated"
            self.stdout.write(self.style.SUCCESS(f"{status}: {username}"))
