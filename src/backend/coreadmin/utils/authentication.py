import uuid
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from coreadmin.system.models import AuthSession


class SessionJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        try:
            sid = uuid.UUID(str(validated_token['sid']))
        except (KeyError, ValueError, TypeError, AttributeError):
            raise AuthenticationFailed('Invalid session.')
        if not AuthSession.objects.filter(
                sid=sid, user=user, revoked_at__isnull=True, expires_at__gt=timezone.now()).exists():
            raise AuthenticationFailed('Session is revoked or expired.')
        return user


def must_change_gate(user, action_code, public=False):
    if public or not getattr(user, 'is_authenticated', False):
        return
    if user.pwd_change_count == 0 and action_code not in {
            'user.user_info', 'user.change_password', 'logout.create'}:
        raise PermissionDenied('Password change required.')
