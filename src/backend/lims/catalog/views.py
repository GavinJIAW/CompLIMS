from lims.catalog import models, serializers
from lims.shared.views import MasterViewSet


class ServiceViewSet(MasterViewSet):
    queryset = models.Service.objects.all()
    serializer_class = serializers.ServiceSerializer
    filter_fields = MasterViewSet.filter_fields + ['service_type', 'internal_name', 'name_en']
    search_fields = ['number', 'internal_name', 'name', 'name_en']
    ordering_fields = MasterViewSet.ordering_fields + ['internal_name', 'name_en']


class ProductViewSet(MasterViewSet):
    queryset = models.Product.objects.select_related('service').prefetch_related('packages__package__items__item').all()
    serializer_class = serializers.ProductSerializer
    filter_fields = MasterViewSet.filter_fields + ['service', 'internal_name', 'name_en']
    search_fields = ServiceViewSet.search_fields
    ordering_fields = ServiceViewSet.ordering_fields + ['reference_price']


class SchemeViewSet(MasterViewSet):
    queryset = models.Scheme.objects.prefetch_related('items__product__service', 'items__product__packages__package__items__item').all()
    serializer_class = serializers.SchemeSerializer
    filter_fields = MasterViewSet.filter_fields + ['internal_name', 'name_en']
    search_fields = ServiceViewSet.search_fields
    ordering_fields = ServiceViewSet.ordering_fields
