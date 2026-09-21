"""Customer/Contact writes participate in the shared master transaction lock."""
from rest_framework.exceptions import ValidationError
from .models import CustomerContact
from lims.shared.services import save_aggregate


def validate_contact(instance, attrs):
    customer = attrs.get('customer', getattr(instance, 'customer', None))
    supervisor = attrs.get('direct_supervisor', getattr(instance, 'direct_supervisor', None))
    if supervisor:
        if supervisor.customer_id != customer.pk:
            raise ValidationError({'direct_supervisor': 'Supervisor must belong to the same customer.'})
        seen = {instance.pk} if instance else set()
        node = supervisor
        while node:
            if node.pk in seen:
                raise ValidationError({'direct_supervisor': 'Supervisor relationships cannot contain a cycle.'})
            seen.add(node.pk)
            node = node.direct_supervisor
    if instance and instance.customer_id != customer.pk and instance.direct_reports.exists():
        raise ValidationError({'customer': 'Reassign direct reports before changing this contact customer.'})
    enabled = attrs.get('enabled', getattr(instance, 'enabled', True))
    default = attrs.get('is_default', getattr(instance, 'is_default', False))
    if enabled and default:
        existing = CustomerContact.objects.filter(customer=customer, enabled=True, is_default=True)
        if instance:
            existing = existing.exclude(pk=instance.pk)
        if existing.exists():
            raise ValidationError({'is_default': 'Only one enabled default contact is allowed per customer.'})


def save_master(serializer, **audit):
    return save_aggregate(serializer, **audit)
