# -*- coding: utf-8 -*-
import pypinyin
from django.db.models import Q
from rest_framework import serializers

from coreadmin.system.models import Area
from coreadmin.utils.field_permission import FieldPermissionMixin
from coreadmin.utils.json_response import SuccessResponse
from coreadmin.utils.serializers import CustomModelSerializer
from coreadmin.utils.viewset import CustomModelViewSet


class AreaSerializer(CustomModelSerializer):
    """
    地区-序列化器
    """
    pcode_count = serializers.SerializerMethodField(read_only=True)
    hasChild = serializers.SerializerMethodField()
    pcode_info = serializers.SerializerMethodField()

    def get_pcode_info(self, instance):
        pcode = Area.objects.filter(code=instance.pcode_id).values("name", "code")
        return pcode

    def get_pcode_count(self, instance: Area):
        return Area.objects.filter(pcode=instance).count()

    def get_hasChild(self, instance):
        hasChild = Area.objects.filter(pcode=instance.code)
        if hasChild:
            return True
        return False

    class Meta:
        model = Area
        fields = "__all__"
        read_only_fields = ["id"]


class AreaParentField(serializers.PrimaryKeyRelatedField):
    """Retain legacy PK input and parent-code output for Area writes."""

    def use_pk_only_optimization(self):
        return False

    def to_representation(self, value):
        return value.code


class AreaCreateUpdateSerializer(CustomModelSerializer):
    """
    地区管理 创建/更新时的列化器
    """

    # The existing API accepts the parent's PK, while the model FK stores code.
    pcode = AreaParentField(queryset=Area.objects.all(), required=False, allow_null=True)

    def validate(self, attrs):
        # FieldPolicy has already checked the original client keys. Derived
        # values enter validated_data only here and are never client-writable.
        attrs = super().validate(attrs)
        name = attrs.get('name', getattr(self.instance, 'name', ''))
        parent = attrs.get('pcode', getattr(self.instance, 'pcode', None))
        pinyin = ''.join([''.join(i) for i in pypinyin.pinyin(name, style=pypinyin.NORMAL)])
        attrs.update(level=parent.level + 1 if parent else 1,
                     pinyin=pinyin, initials=pinyin[0].upper() if pinyin else '#')
        return attrs

    class Meta:
        model = Area
        fields = '__all__'
        read_only_fields = ['level', 'pinyin', 'initials']


class AreaViewSet(CustomModelViewSet, FieldPermissionMixin):
    """
    地区管理接口
    list:查询
    create:新增
    update:修改
    retrieve:单例
    destroy:删除
    """
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    create_serializer_class = AreaCreateUpdateSerializer
    update_serializer_class = AreaCreateUpdateSerializer
    partial_update_serializer_class = AreaCreateUpdateSerializer
    extra_filter_class = []

    def list(self, request, *args, **kwargs):
        self.request.query_params._mutable = True
        params = self.request.query_params
        known_params = {'page', 'limit', 'pcode'}
        # 使用集合操作检查是否有未知参数
        other_params_exist = any(param not in known_params for param in params)
        if other_params_exist:
            queryset = self.queryset.filter(enable=True)
        else:
            pcode = params.get('pcode', None)
            params['limit'] = 999
            if params and pcode:
                queryset = self.queryset.filter(enable=True, pcode=pcode)
            else:
                queryset = self.queryset.filter(enable=True, level=1)
        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, request=request)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True, request=request)
        return SuccessResponse(data=serializer.data, msg="获取成功")
