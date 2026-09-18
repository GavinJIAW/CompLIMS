from django.contrib.auth.backends import ModelBackend
from rest_framework.exceptions import AuthenticationFailed
from coreadmin.system.services.auth import AuthService, ResetRequired


class CustomBackend(ModelBackend):
    """Debug/session entrypoints share the same native/legacy credential verifier."""
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user, _ = AuthService.credentials(username, password)
            return user
        except ResetRequired:
            return None
        except AuthenticationFailed:
            return None
