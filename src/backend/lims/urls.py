from rest_framework.routers import SimpleRouter
from lims.costing.views import CostTypeViewSet, CostItemViewSet, CostPackageViewSet
from lims.catalog.views import ServiceViewSet, ProductViewSet, SchemeViewSet
from lims.customer.views import CustomerViewSet
from lims.commercial.views import QuotationViewSet, ContractViewSet

router = SimpleRouter()
for resource, cls in [('cost_type', CostTypeViewSet), ('service', ServiceViewSet), ('cost_item', CostItemViewSet),
                      ('cost_package', CostPackageViewSet), ('product', ProductViewSet),
                      ('scheme', SchemeViewSet)]:
    router.register(resource, cls)
for resource, cls in [('customer', CustomerViewSet), ('quotation', QuotationViewSet), ('contract', ContractViewSet)]:
    router.register(resource, cls)
urlpatterns = router.urls
