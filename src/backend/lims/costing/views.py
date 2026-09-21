from lims.costing import models, serializers
from lims.shared.views import MasterViewSet


class CostTypeViewSet(MasterViewSet):
    queryset = models.CostType.objects.all()
    serializer_class = serializers.CostTypeSerializer


class CostItemViewSet(MasterViewSet):
    queryset = models.CostItem.objects.all()
    serializer_class = serializers.CostItemSerializer
    filter_fields = MasterViewSet.filter_fields + ['cost_type', 'unit']


class CostPackageViewSet(MasterViewSet):
    queryset = models.CostPackage.objects.prefetch_related('items__item').all()
    serializer_class = serializers.CostPackageSerializer
