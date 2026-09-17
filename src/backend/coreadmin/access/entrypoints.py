"""Canonical policy for the existing non-ViewSet production API entrypoints."""
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.views import TokenRefreshView

from coreadmin.access.registry import ENTRYPOINTS, Policy
from coreadmin.utils.json_response import DetailResponse


class CanonicalEntryMixin:
    def check_permissions(self, request):
        registered = any(path == request.path for path, _ in ENTRYPOINTS)
        active = bool(request.user.is_authenticated and request.user.is_active)
        if request.method == 'OPTIONS':
            if registered and active:
                return
            raise PermissionDenied()
        method = 'GET' if request.method == 'HEAD' else request.method
        entry = ENTRYPOINTS.get((request.path, method))
        if entry is None:
            raise PermissionDenied()
        if entry[1] != Policy.PUBLIC and not active:
            raise PermissionDenied()

    def options(self, request, *args, **kwargs):
        return DetailResponse(data={})


class CanonicalTokenRefreshView(CanonicalEntryMixin, TokenRefreshView):
    """Retains SimpleJWT refresh behavior; only entry authorization is explicit."""
