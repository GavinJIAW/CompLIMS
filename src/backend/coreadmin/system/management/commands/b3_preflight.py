from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction
from coreadmin.system.migrations._b3_preflight import inspect_data


class Command(BaseCommand):
    help = 'Read-only B3 constraint preflight; never repairs data.'

    def handle(self, *args, **options):
        with transaction.atomic():
            with connections['default'].cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute("SET LOCAL statement_timeout = '10s'")
                cursor.execute("SET LOCAL lock_timeout = '2s'")
            problems = inspect_data(apps, 'default')
            transaction.set_rollback(True)
        if problems:
            raise CommandError('Data Cleanup Task required: ' + str(problems))
        self.stdout.write('B3 preflight PASS (READ ONLY; ROLLBACK)')
