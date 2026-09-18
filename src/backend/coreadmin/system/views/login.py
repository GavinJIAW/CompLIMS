import base64
import logging
from datetime import datetime, timedelta
from captcha.views import CaptchaStore, captcha_image
from django.contrib import auth
from django.contrib.auth import login
from django.db import transaction
from django.shortcuts import redirect
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from coreadmin.system.models import SystemConfig
from coreadmin.system.services.auth import AuthService
from coreadmin.utils.json_response import ErrorResponse, DetailResponse
from coreadmin.utils.request_util import save_login_log
from coreadmin.access.entrypoints import CanonicalEntryMixin

logger = logging.getLogger(__name__)


def captcha_enabled():
    # Security decisions never use the process-local configuration cache.
    return bool(SystemConfig.objects.filter(parent__key='base', key='captcha_state')
                .values_list('value', flat=True).first())


class CaptchaView(CanonicalEntryMixin, APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        data = {}
        if captcha_enabled():
            hashkey = CaptchaStore.generate_key()
            key = CaptchaStore.objects.get(hashkey=hashkey).pk
            picture = captcha_image(request, hashkey)
            data = {'key': key, 'image_base': 'data:image/png;base64,' +
                    base64.b64encode(picture.content).decode('utf-8')}
        return DetailResponse(data=data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    captcha = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    captchaKey = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        if captcha_enabled():
            key = attrs.get('captchaKey')
            if not key or not key.isdigit():
                raise ValidationError({'captcha': 'Invalid captcha key.'})
            image = CaptchaStore.objects.filter(pk=int(key)).first()
            valid = (image is not None and
                     datetime.now() - timedelta(minutes=5) <= image.expiration and
                     attrs.get('captcha') in (image.response, image.challenge))
            if image is not None:
                image.delete()
            if not valid:
                raise ValidationError({'captcha': 'Invalid or expired captcha.'})
        user, tokens = AuthService.credentials(attrs['username'], attrs['password'], issue=True)
        request = self.context['request']
        request.user = user
        try:
            with transaction.atomic():
                save_login_log(request)
        except Exception:
            logger.error('Operational login log persistence failed', exc_info=False)
        data = dict(tokens, username=user.username, name=user.name, userId=user.pk,
                    avatar=user.avatar, user_type=user.user_type,
                    pwd_change_count=user.pwd_change_count,
                    role_info=list(user.role.filter(status=True).values('id', 'name', 'key')))
        if user.dept_id:
            data['dept_info'] = {'dept_id': user.dept_id, 'dept_name': user.dept.name}
        return data


class LoginView(CanonicalEntryMixin, APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return DetailResponse(data=serializer.validated_data)


class LoginTokenView(LoginView):
    """Unregistered legacy entrypoint cannot mint sid-less JWT."""
    def post(self, request):
        return ErrorResponse(msg='This legacy entrypoint is disabled.', status=405)


class LogoutView(CanonicalEntryMixin, APIView):
    def post(self, request):
        AuthService.logout(request.user, request.auth)
        return DetailResponse(msg='Logged out.')


class ApiLogin(APIView):
    """DEBUG-only session login; shares the raw credential verifier."""
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        user = auth.authenticate(request, username=request.data.get('username'),
                                 password=request.data.get('password'))
        if user:
            login(request, user)
            return redirect('/')
        return ErrorResponse(msg='Invalid credentials.')
