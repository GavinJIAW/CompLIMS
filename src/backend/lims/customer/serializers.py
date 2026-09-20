from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from coreadmin.utils.serializers import CustomModelSerializer
from lims.shared.m2_contract import READ, WRITE, CONTACT
from lims.shared.aggregate_authority import child_fields, check_child, proposed
from lims.shared.aggregate_rows import collection, validate_row
from .models import Customer, CustomerContact


class CustomerSerializer(CustomModelSerializer):
    contacts = serializers.JSONField(required=False, write_only=True)

    class Meta:
        model = Customer
        fields = READ['customer'].split()
        read_only_fields = list(set(fields) - set(WRITE['customer'].split()))

    def validate(self, attrs):
        if 'contacts' in attrs and not isinstance(attrs['contacts'], list):
            raise ValidationError({'contacts': 'Expected a target collection.'})
        if self.instance and attrs.get('number', self.instance.number) != self.instance.number:
            raise ValidationError({'number': 'Number cannot change after creation.'})
        return attrs

    def persist(self, instance, data):
        ctx = self.request._canonical_access_view.access_context
        parent = instance or proposed(ctx)
        raw = data.pop('contacts', None)
        rows = None
        if raw is not None:
            existing = {r.pk: r for r in instance.contacts.all()} if instance else {}
            rows = collection(raw, existing)
            prepared = []
            for row, old in rows:
                check_child(ctx, parent, CustomerContact, row, old)
                values = validate_row(CustomerContact, {k: v for k, v in row.items() if k != 'id'}, old, CONTACT.split())
                prepared.append((values, old))
            if sum(bool(values.get('enabled', old.enabled if old else True) and values.get('is_default', old.is_default if old else False)) for values, old in prepared) > 1:
                raise ValidationError({'contacts': 'Only one enabled default contact is allowed.'})
            rows = prepared
        if instance:
            for key, value in data.items():
                setattr(instance, key, value)
            instance.save()
        else:
            instance = Customer.objects.create(**data)
        if rows is not None:
            retained = [old.pk for _, old in rows if old]
            instance.contacts.exclude(pk__in=retained).delete()
            # Release the conditional unique slot before assigning the target set.
            # Retained objects preserve their identity and values in memory.
            instance.contacts.filter(is_default=True, enabled=True).update(is_default=False)
            for values, old in rows:
                if old:
                    for key, value in values.items():
                        setattr(old, key, value)
                    old.save()
                else:
                    instance.contacts.create(**values)
        instance._prefetched_objects_cache = {}
        return instance

    def create(self, validated_data):
        return self.persist(None, validated_data)

    def update(self, instance, validated_data):
        return self.persist(instance, validated_data)

    def to_representation(self, instance):
        result = super().to_representation(instance)
        view = self.request._canonical_access_view
        if 'contacts' in view.field_policy.allowed(instance):
            allowed = child_fields(view.access_context, instance, CustomerContact, 'read')
            result['contacts'] = [{key: getattr(row, key) for key in allowed} for row in instance.contacts.all()]
        return result
