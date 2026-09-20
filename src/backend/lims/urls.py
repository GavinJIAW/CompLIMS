from rest_framework.routers import SimpleRouter
from lims.costing.views import CostItemViewSet, CostPackageViewSet
from lims.catalog.views import ServiceViewSet, ProductViewSet, SchemeViewSet

router = SimpleRouter()
for resource, cls in [('service', ServiceViewSet), ('cost_item', CostItemViewSet),
                      ('cost_package', CostPackageViewSet), ('product', ProductViewSet),
                      ('scheme', SchemeViewSet)]:
    router.register(resource, cls)
urlpatterns = router.urls
