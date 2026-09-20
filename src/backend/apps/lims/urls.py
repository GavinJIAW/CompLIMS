from rest_framework.routers import SimpleRouter
from apps.lims import views

router = SimpleRouter()
for resource, cls in [('service', views.ServiceViewSet), ('cost_item', views.CostItemViewSet),
                      ('cost_package', views.CostPackageViewSet), ('product', views.ProductViewSet),
                      ('scheme', views.SchemeViewSet)]:
    router.register(resource, cls)
urlpatterns = router.urls
