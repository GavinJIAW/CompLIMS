# -*- coding: utf-8 -*-


import django_filters
from django_filters.rest_framework import BooleanFilter
from rest_framework import serializers
from rest_framework.views import APIView

from application import dispatch
from coreadmin.system.models import SystemConfig
from coreadmin.utils.json_response import DetailResponse, SuccessResponse, ErrorResponse
from coreadmin.utils.models import get_all_models_objects
from coreadmin.utils.serializers import CustomModelSerializer
from coreadmin.utils.validator import CustomValidationError
from coreadmin.utils.permission import SuperuserPermission
from coreadmin.utils.viewset import CustomModelViewSet, PatchAsUpdateFilterMixin


class SystemConfigCreateSerializer(CustomModelSerializer):
    """
    系统配置-新增时使用-序列化器
    """
    form_item_type_label = serializers.CharField(source='get_form_item_type_display', read_only=True)

    class Meta:
        model = SystemConfig
        fields = "__all__"
        read_only_fields = ["id"]

    def validate_key(self, value):
        """
        验证key是否允许重复
        parent为空时不允许重复,反之允许
        """
        instance = SystemConfig.objects.filter(key=value, parent__isnull=True).exists()
        if instance:
            raise CustomValidationError('已存在相同变量名')
        return value




class SystemConfigSerializer(CustomModelSerializer):
    """
    系统配置-序列化器
    """
    form_item_type_label = serializers.CharField(source='get_form_item_type_display', read_only=True)

    class Meta:
        model = SystemConfig
        fields = "__all__"
        read_only_fields = ["id"]


class SystemConfigChinldernSerializer(CustomModelSerializer):
    """
    系统配置子级-序列化器
    """
    children = serializers.SerializerMethodField()
    form_item_type_label = serializers.CharField(source='get_form_item_type_display', read_only=True)

    def get_children(self, instance):
        queryset = SystemConfig.objects.filter(parent=instance)
        serializer = SystemConfigSerializer(queryset, many=True)
        return serializer.data

    class Meta:
        model = SystemConfig
        fields = "__all__"
        read_only_fields = ["id"]


class SystemConfigListSerializer(CustomModelSerializer):
    """
    系统配置下模块的保存-序列化器
    """

    def update(self, instance, validated_data):
        instance_mapping = {obj.id: obj for obj in instance}
        data_mapping = {item['id']: item for item in validated_data}
        for obj_id, data in data_mapping.items():
            instance_obj = instance_mapping.get(obj_id, None)
            if instance_obj is None:
                return SystemConfig.objects.create(**data)
            else:
                return instance_obj.objects.update(**data)

    class Meta:
        model = SystemConfig
        fields = "__all__"
        read_only_fields = ["id"]


class SystemConfigSaveSerializer(serializers.Serializer):
    class Meta:
        read_only_fields = ["id"]
        list_serializer_class = SystemConfigListSerializer


class SystemConfigFilter(django_filters.rest_framework.FilterSet):
    """
    过滤器
    """
    parent__isnull = BooleanFilter(field_name='parent', lookup_expr="isnull")

    class Meta:
        model = SystemConfig
        fields = ['id', 'parent', 'status', 'parent__isnull']


class SystemConfigViewSet(PatchAsUpdateFilterMixin, CustomModelViewSet):
    """
    系统配置接口
    """
    queryset = SystemConfig.objects.order_by('sort', 'create_datetime')
    serializer_class = SystemConfigChinldernSerializer
    create_serializer_class = SystemConfigCreateSerializer
    retrieve_serializer_class = SystemConfigChinldernSerializer
    # filter_fields = ['id','parent']
    filter_class = SystemConfigFilter

    def get_permissions(self):
        if self.action == 'get_table_data':
            # Disabled for every actor, including anonymous callers.
            return []
        if self.request.method in ('POST', 'PUT', 'PATCH', 'DELETE') or self.action == 'get_association_table':
            return [SuperuserPermission()]
        return super().get_permissions()

    def save_content(self, request):
        body = request.data
        data_mapping = {item['id']: item for item in body}
        for obj_id, data in data_mapping.items():
            instance_obj = SystemConfig.objects.filter(id=obj_id).first()
            if instance_obj is None:
                # return SystemConfig.objects.create(**data)
                serializer = SystemConfigCreateSerializer(data=data)
            else:
                serializer = SystemConfigCreateSerializer(instance_obj, data=data)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
        return DetailResponse(msg="保存成功")

    def get_association_table(self, request):
        """
        获取所有的model及字段信息
        """
        res = [ele.get('table') for ele in get_all_models_objects().values()]
        return DetailResponse(msg="获取成功", data=res)

    def get_table_data(self, request, pk):
        return ErrorResponse(msg='Dynamic model lookup is temporarily disabled.', status=405)

    def get_relation_info(self, request):
        """
        查询关联的模板信息
        """
        body = request.query_params
        var_name = body.get('varName', None)
        table = body.get('table', None)
        instance = SystemConfig.objects.filter(key=var_name, setting__table=table).first()
        if instance is None:
            return ErrorResponse(msg="未获取到关联信息")
        relation_id = body.get('relationIds', None)
        relationIds = []
        if relation_id is None:
            return ErrorResponse(msg="未获取到关联信息")
        if instance.form_item_type in [13]:
            relationIds = [relation_id]
        elif instance.form_item_type in [14]:
            relationIds = relation_id.split(',')
        queryset = SystemConfig.objects.filter(value__in=relationIds).first()
        if queryset is None:
            return ErrorResponse(msg="未获取到关联信息")
        serializer = SystemConfigChinldernSerializer(queryset.parent)
        return DetailResponse(msg="查询成功", data=serializer.data)


class InitSettingsViewSet(APIView):
    """
    获取初始化配置
    """
    authentication_classes = []
    permission_classes = []

    # Exact UI consumers: login/index.vue, layout/logo/index.vue,
    # login/component/account.vue and utils/other.ts. Enabled != public.
    PUBLIC_KEYS = frozenset({
        'login.site_title', 'login.site_name', 'login.site_logo',
        'login.login_background', 'base.web_title', 'base.web_favicon',
        'base.captcha_state',
    })

    def filter_system_config_values(self, data: dict):
        allowed = self.PUBLIC_KEYS
        requested = self.request.query_params.get('key', '')
        if requested:
            allowed = allowed.intersection(requested.split('|'))
        return {key: value for key, value in data.items() if key in allowed}

    def get(self, request):
        data = dispatch.get_system_config()
        if not data:
            dispatch.refresh_system_config()
            data = dispatch.get_system_config()
        # 不返回后端专用配置
        backend_config = [f"{ele.get('parent__key')}.{ele.get('key')}" for ele in
                          SystemConfig.objects.filter(status=False, parent_id__isnull=False).values('parent__key',
                                                                                                    'key')]
        data = dict(filter(lambda x: x[0] not in backend_config, data.items()))
        data = self.filter_system_config_values(data=data)
        return DetailResponse(data=data)
