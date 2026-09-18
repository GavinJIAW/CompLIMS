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
                from coreadmin.utils.authentication import must_change_gate
                must_change_gate(request.user, 'entry.options')
                return
            raise PermissionDenied()
        method = 'GET' if request.method == 'HEAD' else request.method
        entry = ENTRYPOINTS.get((request.path, method))
        if entry is None:
            raise PermissionDenied()
        if entry[1] != Policy.PUBLIC and not active:
            raise PermissionDenied()
        from coreadmin.utils.authentication import must_change_gate
        must_change_gate(request.user, entry[0], entry[1] == Policy.PUBLIC)

    def options(self, request, *args, **kwargs):
        return DetailResponse(data={})


from rest_framework import serializers
from coreadmin.system.services.auth import AuthService


class SessionRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)

    def validate(self, attrs):
        return AuthService.refresh(attrs['refresh'])


class CanonicalTokenRefreshView(CanonicalEntryMixin, TokenRefreshView):
    serializer_class = SessionRefreshSerializer
