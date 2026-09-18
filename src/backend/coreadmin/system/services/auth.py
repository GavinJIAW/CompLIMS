"""Native credentials and the single server-side JWT session authority."""
import hashlib
import logging
import uuid
from datetime import datetime, timezone as dt_timezone
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from coreadmin.system.models import Users, AuthSession

logger = logging.getLogger(__name__)


class ResetRequired(AuthenticationFailed):
    default_detail = 'RESET REQUIRED'
    default_code = 'reset_required'


def password_policy(raw, user=None):
    if not isinstance(raw, str) or not raw:
        raise ValidationError({'password': 'Password is required.'})
    try:
        validate_password(raw, user=user)
    except DjangoValidationError as exc:
        raise ValidationError({'password': exc.messages})


def verify_credential(user, raw):
    if not isinstance(raw, str) or not user.password:
        raise ResetRequired()
    if user.credential_version == 'DJANGO_NATIVE':
        return check_password(raw, user.password)
    if user.credential_version != 'LEGACY_UNKNOWN':
        raise ResetRequired()
    first = hashlib.md5(raw.encode('utf-8')).hexdigest()
    second = hashlib.md5(first.encode('utf-8')).hexdigest()
    if check_password(first, user.password) or check_password(second, user.password):
        user.set_password(raw)
        return True
    if check_password(raw, user.password):
        raise ResetRequired()
    return False


def token_claims(token):
    try:
        user_id = token['user_id']
        if isinstance(user_id, bool) or not str(user_id).isdigit():
            raise ValueError()
        return int(user_id), uuid.UUID(str(token['sid']))
    except (KeyError, TypeError, ValueError, AttributeError):
        raise AuthenticationFailed('Invalid session.')


class AuthService:
    @staticmethod
    def _issue_locked(user):
        refresh = RefreshToken.for_user(user)
        session = AuthSession.objects.create(
            user=user, current_refresh_jti=refresh['jti'],
            expires_at=datetime.fromtimestamp(refresh['exp'], tz=dt_timezone.utc))
        refresh['sid'] = str(session.sid)
        return {'refresh': str(refresh), 'access': str(refresh.access_token)}

    @staticmethod
    def issue(user):
        """Internal issuance for already verified identities, also used by fixtures."""
        with transaction.atomic():
            user = Users.objects.select_for_update().get(pk=user.pk)
            if not user.is_active:
                raise AuthenticationFailed('User is inactive.')
            return AuthService._issue_locked(user)

    @staticmethod
    def credentials(username, raw, issue=False):
        failed = False
        with transaction.atomic():
            try:
                user = Users.objects.select_for_update().get(
                    Q(username=username) | Q(email=username) | Q(mobile=username))
            except (Users.DoesNotExist, Users.MultipleObjectsReturned):
                raise AuthenticationFailed('Invalid credentials.')
            if not user.is_active:
                raise AuthenticationFailed('User is inactive.')
            if not verify_credential(user, raw):
                failed = True
                user.login_error_count += 1
                if user.login_error_count >= 5:
                    user.is_active = False
                    AuthService.revoke_all_locked(user, 'credential_lock')
                user.save(update_fields=['login_error_count', 'is_active'])
            else:
                user.login_error_count = 0
                user.last_login = timezone.now()
                user.save(update_fields=['password', 'credential_version', 'login_error_count', 'last_login'])
                tokens = AuthService._issue_locked(user) if issue else None
        # A credential failure increments atomically without rolling it back.
        if failed:
            raise AuthenticationFailed('Invalid credentials.')
        return user, tokens

    @staticmethod
    def refresh(raw):
        try:
            token = RefreshToken(raw)
            user_id, sid = token_claims(token)
        except TokenError:
            raise AuthenticationFailed('Invalid refresh token.')
        with transaction.atomic():
            user = Users.objects.select_for_update().filter(pk=user_id).first()
            if user is None or not user.is_active:
                raise AuthenticationFailed('User is inactive.')
            session = AuthSession.objects.select_for_update().filter(sid=sid, user=user).first()
            if (session is None or session.revoked_at is not None or
                    session.expires_at <= timezone.now() or
                    session.current_refresh_jti != token.get('jti')):
                raise AuthenticationFailed('Invalid or consumed refresh token.')
            successor = RefreshToken.for_user(user)
            successor['sid'] = str(session.sid)
            session.current_refresh_jti = successor['jti']
            session.last_refreshed_at = timezone.now()
            session.expires_at = datetime.fromtimestamp(successor['exp'], tz=dt_timezone.utc)
            session.save(update_fields=['current_refresh_jti', 'last_refreshed_at', 'expires_at'])
            return {'refresh': str(successor), 'access': str(successor.access_token)}

    @staticmethod
    def revoke_all_locked(user, reason):
        # Caller holds User before acquiring any Session lock.
        sessions = list(AuthSession.objects.select_for_update().filter(user=user, revoked_at__isnull=True).order_by('sid'))
        AuthSession.objects.filter(sid__in=[s.sid for s in sessions]).update(
            revoked_at=timezone.now(), revoke_reason=reason)

    @staticmethod
    def logout(user, token):
        user_id, sid = token_claims(token)
        if user_id != user.pk:
            raise AuthenticationFailed('Invalid session.')
        with transaction.atomic():
            Users.objects.select_for_update().get(pk=user.pk)
            session = AuthSession.objects.select_for_update().filter(sid=sid, user=user).first()
            if session is None:
                raise AuthenticationFailed('Invalid session.')
            session.revoked_at = timezone.now()
            session.revoke_reason = 'logout'
            session.save(update_fields=['revoked_at', 'revoke_reason'])

    @staticmethod
    def change_password(user_id, old, new, confirmation):
        if new != confirmation:
            raise ValidationError({'password': 'Passwords do not match.'})
        with transaction.atomic():
            user = Users.objects.select_for_update().get(pk=user_id)
            if not verify_credential(user, old):
                raise ValidationError({'oldPassword': 'Invalid password.'})
            password_policy(new, user)
            user.set_password(new)
            user.pwd_change_count = max(1, user.pwd_change_count + 1)
            user.save(update_fields=['password', 'credential_version', 'pwd_change_count'])
            AuthService.revoke_all_locked(user, 'password_change')

    @staticmethod
    def reset_password(user_id, new, confirmation):
        if new != confirmation:
            raise ValidationError({'password': 'Passwords do not match.'})
        with transaction.atomic():
            user = Users.objects.select_for_update().get(pk=user_id)
            password_policy(new, user)
            user.set_password(new)
            user.pwd_change_count = 0
            user.save(update_fields=['password', 'credential_version', 'pwd_change_count'])
            AuthService.revoke_all_locked(user, 'password_reset')


class UserService:
    @staticmethod
    def create(validated_data, create):
        raw = validated_data.pop('password')
        proposed = Users(**{k:v for k,v in validated_data.items() if k not in ('role','post')})
        password_policy(raw, proposed)
        proposed.set_password(raw)
        validated_data.update(password=proposed.password, credential_version='DJANGO_NATIVE', pwd_change_count=0)
        with transaction.atomic():
            return create(validated_data)

    @staticmethod
    def update(instance, validated_data, update):
        with transaction.atomic():
            locked = Users.objects.select_for_update().get(pk=instance.pk)
            result = update(locked, validated_data)
            if not result.is_active:
                AuthService.revoke_all_locked(result, 'disabled')
            return result
