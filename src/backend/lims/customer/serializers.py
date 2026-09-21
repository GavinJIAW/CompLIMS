from rest_framework import serializers
from lims.shared.serializers import MasterSerializer
from lims.shared.authority import reference, readable
from .access_contract import READ, WRITE
from .models import Customer, CustomerContact
from .services import validate_contact


class CustomerSerializer(MasterSerializer):
    resource = 'customer'
    class Meta:
        model = Customer
        fields = READ['customer'].split()
        read_only_fields = list(set(fields) - set(WRITE['customer'].split()))


class ContactSerializer(MasterSerializer):
    resource = 'contact'
    customer_name = serializers.SerializerMethodField()
    direct_supervisor_name = serializers.SerializerMethodField()

    def get_customer_name(self, instance):
        customer = instance.customer
        return customer.name if readable(self.request.user, 'customer', customer, ['name']) else None

    def get_direct_supervisor_name(self, instance):
        supervisor = instance.direct_supervisor
        if supervisor and readable(self.request.user, 'contact', supervisor, ['name']):
            return supervisor.name
        return None

    class Meta:
        model = CustomerContact
        fields = READ['contact'].split()
        read_only_fields = list(set(fields) - set(WRITE['contact'].split()))
        validators = []  # Conditional default validation runs under the master lock.

    def validate(self, attrs):
        attrs = super().validate(attrs)
        for key, resource in [('customer', 'customer'), ('direct_supervisor', 'contact')]:
            if attrs.get(key) is not None:
                obj = attrs[key]
                reference(self.request.user, resource, obj,
                          bool(self.instance and getattr(self.instance, key + '_id') == obj.pk))
        validate_contact(self.instance, attrs)
        return attrs

    def to_representation(self, instance):
        result = super().to_representation(instance)
        for key, resource in [('customer', 'customer'), ('direct_supervisor', 'contact')]:
            obj = getattr(instance, key)
            if key in result and obj and not readable(self.request.user, resource, obj, ['id']):
                result[key] = None
        return result
