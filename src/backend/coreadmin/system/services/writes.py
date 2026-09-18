"""Transaction/lock boundaries for existing write entrypoints."""
from contextlib import contextmanager
from functools import wraps
from django.db import transaction
from rest_framework.exceptions import ValidationError
from coreadmin.system.models import Role, Dept


@contextmanager
def command(view):
    resource = view.access_context.action.resource
    with transaction.atomic():
        # Authorization writers share one stable role lock hierarchy, including
        # generic CRUD/bulk deletion and reassignment of grant ownership.
        if resource in {'role', 'role_menu_permission', 'role_menu_button_permission', 'column'}:
            list(Role.objects.select_for_update().order_by('pk'))
        if resource == 'dept':
            # Serializes reparenting and the ancestor walk, preventing concurrent
            # complementary moves from constructing a cycle.
            list(Dept.objects.select_for_update().order_by('pk'))
        yield


def atomic_command(method):
    @wraps(method)
    def wrapped(view, request, *args, **kwargs):
        with command(view):
            return method(view, request, *args, **kwargs)
    return wrapped


def validate_dept_parent(instance, parent):
    seen = {instance.pk} if instance is not None else set()
    while parent is not None:
        if parent.pk in seen:
            raise ValidationError({'parent': 'Department cycle is not allowed.'})
        seen.add(parent.pk)
        parent = parent.parent
