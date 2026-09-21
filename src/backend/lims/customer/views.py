from lims.shared.views import MasterViewSet
from .models import Customer, CustomerContact
from .serializers import CustomerSerializer, ContactSerializer
from .services import save_master


class CustomerViewSet(MasterViewSet):
    resource = 'customer'
    save_master = staticmethod(save_master)
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    filter_fields = ['number', 'name', 'short_name', 'enabled']
    search_fields = ['number', 'name', 'short_name']
    ordering_fields = ['number', 'name', 'short_name', 'enabled', 'create_datetime']


class ContactViewSet(MasterViewSet):
    resource = 'contact'
    save_master = staticmethod(save_master)
    queryset = CustomerContact.objects.select_related('customer', 'direct_supervisor').all()
    serializer_class = ContactSerializer
    filter_fields = ['customer', 'gender', 'enabled', 'is_default']
    search_fields = ['name', 'mobile', 'email']
    ordering_fields = ['name', 'customer', 'enabled', 'create_datetime']
