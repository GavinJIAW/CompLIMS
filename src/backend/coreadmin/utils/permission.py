# -*- coding: utf-8 -*-


import re

from django.contrib.auth.models import AnonymousUser
from django.db.models import F
from rest_framework.permissions import BasePermission

from coreadmin.access.context import context_for


def ValidationApi(reqApi, validApi):
    """
    验证当前用户是否有接口权限
    :param reqApi: 当前请求的接口
    :param validApi: 用于验证的接口
    :return: True或者False
    """
    if validApi is not None:
        valid_api = validApi.replace('{id}', '.*?')
        matchObj = re.match(valid_api, reqApi, re.M | re.I)
        if matchObj:
            return True
        else:
            return False
    else:
        return False


class AnonymousUserPermission(BasePermission):
    """
    匿名用户权限
    """

    def has_permission(self, request, view):
        if isinstance(request.user, AnonymousUser):
            return False
        return True


class ActiveAuthenticatedPermission(BasePermission):
    """Authenticated reads require an active account."""

    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.is_active)


class SuperuserPermission(BasePermission):
    """
    超级管理员权限类
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(user.is_authenticated and user.is_active and user.is_superuser)


class AuthorizationMutationMixin:
    """Temporary P0 gate: authorization writes never consult legacy grants."""

    def get_permissions(self):
        if self.request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            return [SuperuserPermission()]
        return super().get_permissions()


class AdminPermission(BasePermission):
    """
    普通管理员权限类
    """

    def has_permission(self, request, view):
        if isinstance(request.user, AnonymousUser):
            return False
        # 判断是否是超级管理员
        is_superuser = request.user.is_superuser
        # 判断是否是管理员角色
        is_admin = request.user.role.values_list('coreadmin', flat=True)
        if is_superuser or True in is_admin:
            return True


def ReUUID(api):
    """
    将接口的uuid替换掉
    :param api:
    :return:
    """
    pattern = re.compile(r'[a-f\d]{4}(?:[a-f\d]{4}-){4}[a-f\d]{12}/$')
    m = pattern.search(api)
    if m:
        res = api.replace(m.group(0), ".*/")
        return res
    else:
        return None


class CustomPermission(BasePermission):
    """Compatibility name for canonical action policy; URL metadata has no authority."""

    def has_permission(self, request, view):
        return bool(view is not None and context_for(request, view).allowed())
