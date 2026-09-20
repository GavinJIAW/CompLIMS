from lims.shared.aggregate_views import AggregateViewSet
from .models import Customer
from .serializers import CustomerSerializer


class CustomerViewSet(AggregateViewSet):
    resource = 'customer'
    queryset = Customer.objects.prefetch_related('contacts').all()
    serializer_class = CustomerSerializer
    filter_fields = ['number', 'name', 'short_name', 'enabled']
    search_fields = ['number', 'name', 'short_name']
    ordering_fields = ['number', 'name', 'short_name', 'enabled', 'create_datetime']
