from lims.costing import models, serializers
from lims.shared.views import MasterViewSet
from .services import save_master


class AppMasterViewSet(MasterViewSet):
    save_master = staticmethod(save_master)


class CostTypeViewSet(AppMasterViewSet):
    queryset = models.CostType.objects.all()
    serializer_class = serializers.CostTypeSerializer


class CostItemViewSet(AppMasterViewSet):
    queryset = models.CostItem.objects.all()
    serializer_class = serializers.CostItemSerializer
    filter_fields = MasterViewSet.filter_fields + ['cost_type', 'unit']


class CostPackageViewSet(AppMasterViewSet):
    queryset = models.CostPackage.objects.prefetch_related('items__item').all()
    serializer_class = serializers.CostPackageSerializer
