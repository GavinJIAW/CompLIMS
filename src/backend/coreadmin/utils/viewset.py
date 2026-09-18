from django.db import transaction, connection
from coreadmin.system.services.writes import atomic_command
# -*- coding: utf-8 -*-


from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, MethodNotAllowed, ValidationError
from rest_framework.viewsets import ModelViewSet

from coreadmin.utils.filters import DataLevelPermissionsFilter, CoreModelFilterBankend
from coreadmin.utils.import_export_mixin import ExportSerializerMixin, ImportSerializerMixin
from coreadmin.utils.json_response import SuccessResponse, ErrorResponse, DetailResponse
from coreadmin.utils.permission import CustomPermission
from django_restql.mixins import QueryArgumentsMixin
from coreadmin.access.context import context_for
from coreadmin.access.registry import Policy


class ReadOnlyAPIMixin:
    """B1 temporary API freeze; internal ORM writes remain available."""
    http_method_names = ['get', 'head', 'options']

    def http_method_not_allowed(self, request, *args, **kwargs):
        # Return an explicit status; the legacy generic exception handler folds 405.
        return ErrorResponse(msg='This legacy API is read-only.', status=405)


class PatchAsUpdateFilterMixin:
    """Compatibility import only. Canonical policy handles PATCH without rewriting it."""


class CustomModelViewSet(ModelViewSet, ImportSerializerMixin, ExportSerializerMixin, QueryArgumentsMixin):
    """
    自定义的ModelViewSet:
    统一标准的返回格式;新增,查询,修改可使用不同序列化器
    (1)ORM性能优化, 尽可能使用values_queryset形式
    (2)xxx_serializer_class 某个方法下使用的序列化器(xxx=create|update|list|retrieve|destroy)
    (3)filter_fields = '__all__' 默认支持全部model中的字段查询(除json字段外)
    (4)import_field_dict={} 导入时的字段字典 {model值: model的label}
    (5)export_field_label = [] 导出时的字段
    """
    values_queryset = None
    bulk_delete_enabled = False
    ordering_fields = '__all__'
    create_serializer_class = None
    update_serializer_class = None
    filter_fields = '__all__'
    search_fields = ()
    extra_filter_class = [CoreModelFilterBankend]
    permission_classes = [CustomPermission]
    import_field_dict = {}
    export_field_label = {}

    def check_permissions(self, request):
        # Central entrypoint also covers actions with old decorator overrides.
        context = context_for(request, self)
        if not context.allowed():
            raise PermissionDenied()
        if context.action.policy == Policy.B1_SHUTDOWN:
            raise MethodNotAllowed(request.method)
        from coreadmin.utils.authentication import must_change_gate
        must_change_gate(request.user, context.action.code, context.action.policy == Policy.PUBLIC)
        from coreadmin.access.targets import validate_targets
        validate_targets(self, request, context)
        request._canonical_access_view = self
        from coreadmin.access.fields import FieldPolicy, SELF_READ
        self.field_policy = FieldPolicy(context, self.queryset.model)
        if (context.action.policy == Policy.ROLE_GRANTABLE or context.action.code in SELF_READ
                or context.action.name in {'list', 'retrieve', 'export_data', 'update_template'}):
            self.field_policy.validate_query(request, self)

    def handle_exception(self, exc):
        if isinstance(exc, MethodNotAllowed):
            return ErrorResponse(msg='This API action is disabled.', status=405)
        return super().handle_exception(exc)

    def options(self, request, *args, **kwargs):
        return DetailResponse(data={}, msg='Metadata available only through approved projections.')

    def get_object(self):
        obj = super().get_object()
        if connection.in_atomic_block and self.request.method in ('PUT', 'PATCH', 'DELETE'):
            # Lock the object, then repeat B2 resolution against its current state.
            from django.shortcuts import get_object_or_404
            get_object_or_404(self.queryset.model.objects.select_for_update(), pk=obj.pk)
            self.access_context.__dict__.pop('grants', None)
            self.access_context.__dict__.pop('child_depts', None)
            self.field_policy.__dict__.pop('configured', None)
            obj = super().get_object()
        return obj

    def filter_queryset(self, queryset):
        queryset = context_for(self.request, self).scope(queryset)
        backends = dict.fromkeys([*self.filter_backends, *(self.extra_filter_class or [])])
        for backend in backends:
            if backend is DataLevelPermissionsFilter:
                continue
            queryset = backend().filter_queryset(self.request, queryset, self)
        if not self.access_context.admin and not self.request.query_params.get('ordering'):
            queryset = queryset.order_by('pk')
        return queryset

    def get_queryset(self):
        if getattr(self, 'values_queryset', None):
            return self.values_queryset
        return super().get_queryset()

    def get_serializer_class(self):
        action_serializer_name = f"{self.action}_serializer_class"
        action_serializer_class = getattr(self, action_serializer_name, None)
        if action_serializer_class:
            return action_serializer_class
        return super().get_serializer_class()

    # 通过many=True直接改造原有的API，使其可以批量创建
    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs.setdefault('context', self.get_serializer_context())
        # 全部以可见字段为准
        can_see = sorted(self.field_policy.query_fields()) if hasattr(self, 'field_policy') else []
        self.request.permission_fields = can_see
        if 'data' in kwargs and hasattr(self, 'field_policy'):
            data = kwargs['data']
            rows = data if isinstance(data, list) else [data]
            for row in rows:
                self.field_policy.validate_write(row, args[0] if args else kwargs.get('instance'))
                from coreadmin.access.targets import validate_write_relations
                validate_write_relations(self.access_context, row)
        if isinstance(self.request.data, list):
            kwargs.setdefault('many', True)
        return serializer_class(*args, **kwargs)

    @atomic_command
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, request=request)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return DetailResponse(data=serializer.data, msg="新增成功")

    def perform_create(self, serializer):
        # Use the exact proposed scope context, independently of RESTQL's
        # presentation field selection. Clients cannot supply attribution.
        if self.access_context.action.resource == 'message_center':
            from coreadmin.system.services.messages import MessageService
            MessageService.create(serializer, **self.access_context.create_attribution())
        else:
            serializer.save(**self.access_context.create_attribution())

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, request=request)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True, request=request)
        return SuccessResponse(data=serializer.data, msg="获取成功")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data, msg="获取成功")

    @atomic_command
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, request=request, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}
        return DetailResponse(data=serializer.data, msg="更新成功")

    @atomic_command
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return DetailResponse(data=[], msg="删除成功")

    keys = openapi.Schema(description='主键列表', type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING))
    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['keys'],
        properties={'keys': keys}
    ), operation_summary='批量删除')
    @action(methods=['delete'], detail=False)
    @atomic_command
    def multiple_delete(self, request, *args, **kwargs):
        if not self.bulk_delete_enabled:
            return ErrorResponse(msg='Bulk deletion is temporarily disabled.', status=405)
        request_data = request.data
        keys = request_data.get('keys', None)
        if keys:
            if not isinstance(keys, list) or any(isinstance(key, bool) for key in keys):
                raise ValidationError({'keys': 'Expected a list of IDs.'})
            from coreadmin.access.targets import ids
            keys = ids(keys)
            targets = context_for(request, self).scope(self.get_queryset()).filter(pk__in=keys)
            if set(targets.values_list('pk', flat=True)) != keys:
                raise NotFound()
            list(self.queryset.model.objects.select_for_update().filter(pk__in=keys).order_by('pk'))
            targets = context_for(request, self).scope(self.get_queryset()).filter(pk__in=keys)
            if set(targets.values_list('pk', flat=True)) != keys:
                raise NotFound()
            targets.delete()
            return SuccessResponse(data=[], msg="删除成功")
        else:
            return ErrorResponse(msg="未获取到keys字段")
