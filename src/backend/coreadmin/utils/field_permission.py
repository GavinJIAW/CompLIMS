# -*- coding: utf-8 -*-
from django.db.models import F
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from coreadmin.system.models import FieldPermission, MenuField
from coreadmin.utils.json_response import DetailResponse


def merge_permission(data):
    """
    合并权限
    """
    result = {}
    for item in data:
        field_name = item.pop('field_name')
        if field_name not in result:
            result[field_name] = item
        else:
            for key, value in item.items():
                result[field_name][key] = result[field_name][key] or value
    return result


class FieldPermissionMixin:
    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated])
    def field_permission(self, request):
        """
        获取字段权限
        """
        from coreadmin.access.projection import field_metadata
        from coreadmin.access.registry import resource_for
        return DetailResponse(data=field_metadata(request.user, resource_for(self), self.serializer_class.Meta.model))
