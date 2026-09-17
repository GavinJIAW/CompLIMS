# -*- coding: utf-8 -*-
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from coreadmin.system.models import Dept, RoleMenuButtonPermission, Users
from coreadmin.utils.filters import DataLevelPermissionsFilter
from coreadmin.utils.json_response import DetailResponse, SuccessResponse, ErrorResponse
from coreadmin.utils.serializers import CustomModelSerializer
from coreadmin.utils.permission import ActiveAuthenticatedPermission, SuperuserPermission
from coreadmin.utils.viewset import CustomModelViewSet


class DeptSerializer(CustomModelSerializer):
    """
    部门-序列化器
    """
    parent_name = serializers.CharField(read_only=True, source='parent.name')
    status_label = serializers.SerializerMethodField()
    has_children = serializers.SerializerMethodField()
    hasChild = serializers.SerializerMethodField()

    dept_user_count = serializers.SerializerMethodField()

    def get_dept_user_count(self, obj: Dept):
        return Users.objects.filter(dept=obj).count()

    def get_hasChild(self, instance):
        hasChild = Dept.objects.filter(parent=instance.id)
        if hasChild:
            return True
        return False

    def get_status_label(self, obj: Dept):
        if obj.status:
            return "启用"
        return "禁用"

    def get_has_children(self, obj: Dept):
        return Dept.objects.filter(parent_id=obj.id).count()

    class Meta:
        model = Dept
        fields = '__all__'
        read_only_fields = ["id"]


class DeptImportSerializer(CustomModelSerializer):
    """
    部门-导入-序列化器
    """

    class Meta:
        model = Dept
        fields = '__all__'
        read_only_fields = ["id"]


class DeptCreateUpdateSerializer(CustomModelSerializer):
    """
    部门管理 创建/更新时的列化器
    """

    def create(self, validated_data):
        value = validated_data.get('parent', None)
        if value is None:
            validated_data['parent'] = self.request.user.dept
        dept_obj = Dept.objects.filter(parent=self.request.user.dept).order_by('-sort').first()
        last_sort = dept_obj.sort if dept_obj else 0
        validated_data['sort'] = last_sort + 1
        instance = super().create(validated_data)
        instance.dept_belong_id = instance.id
        instance.save()
        return instance

    class Meta:
        model = Dept
        fields = '__all__'


class DeptViewSet(CustomModelViewSet):
    """
    部门管理接口
    list:查询
    create:新增
    update:修改
    retrieve:单例
    destroy:删除
    """
    queryset = Dept.objects.all()
    serializer_class = DeptSerializer
    create_serializer_class = DeptCreateUpdateSerializer
    update_serializer_class = DeptCreateUpdateSerializer
    filter_fields = ['name', 'id', 'parent']
    search_fields = []
    # extra_filter_class = []
    import_serializer_class = DeptImportSerializer
    import_field_dict = {
        "name": "部门名称",
        "key": "部门标识",
    }

    def list(self, request, *args, **kwargs):
        # 如果懒加载，则只返回父级
        request.query_params._mutable = True
        params = request.query_params
        parent = params.get('parent', None)
        page = params.get('page', None)
        limit = params.get('limit', None)
        if page:
            del params['page']
        if limit:
            del params['limit']
        if params and parent:
            queryset = self.queryset.filter(status=True, parent=parent)
        else:
            queryset = self.queryset.filter(status=True)
        queryset = self.filter_queryset(queryset)
        serializer = DeptSerializer(queryset, many=True, request=request)
        data = serializer.data
        return SuccessResponse(data=data)

    @action(methods=["GET"], detail=False, permission_classes=[IsAuthenticated])
    def all_dept(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        data = []
        for obj in queryset.filter(status=True).order_by('sort'):
            values = {'name': obj.name, 'id': obj.id, 'parent': obj.parent_id}
            data.append({key: value for key, value in values.items() if key in self.field_policy.allowed(obj)})
        return DetailResponse(data=data, msg="获取成功")

    @action(methods=['POST'], detail=False, permission_classes=[SuperuserPermission])
    def move_up(self, request):
        """部门上移"""
        dept_id = request.data.get('dept_id')
        try:
            dept = Dept.objects.get(id=dept_id)
        except Dept.DoesNotExist:
            return ErrorResponse(msg="部门不存在")
        previous_menu = Dept.objects.filter(sort__lt=dept.sort, parent=dept.parent).order_by('-sort').first()
        if previous_menu:
            previous_menu.sort, dept.sort = dept.sort, previous_menu.sort
            previous_menu.save()
            dept.save()
        return SuccessResponse(data=[], msg="上移成功")

    @action(methods=['POST'], detail=False, permission_classes=[SuperuserPermission])
    def move_down(self, request):
        """部门下移"""
        dept_id = request.data['dept_id']
        try:
            dept = Dept.objects.get(id=dept_id)
        except Dept.DoesNotExist:
            return ErrorResponse(msg="部门不存在")
        next_menu = Dept.objects.filter(sort__gt=dept.sort, parent=dept.parent).order_by('sort').first()
        if next_menu:
            next_menu.sort, dept.sort = dept.sort, next_menu.sort
            next_menu.save()
            dept.save()
        return SuccessResponse(data=[], msg="下移成功")

    @action(methods=['GET'], detail=False, permission_classes=[ActiveAuthenticatedPermission])
    def dept_info(self, request):
        """部门信息"""
        from coreadmin.access.context import descendants
        from django.shortcuts import get_object_or_404
        from rest_framework.exceptions import ValidationError
        authorized = self.access_context.scope(self.get_queryset())
        dept_obj = get_object_or_404(authorized, pk=request.query_params.get('dept_id'))
        show_all = request.query_params.get('show_all', '0')
        if show_all not in ('0', '1', ''):
            raise ValidationError({'show_all': 'Expected 0 or 1.'})
        dept_ids = descendants(dept_obj.pk) if show_all == '1' else {dept_obj.pk}
        permitted_ids = authorized.filter(pk__in=dept_ids).values_list('pk', flat=True)
        users = Users.objects.exclude(is_superuser=True).filter(dept_id__in=permitted_ids)
        data = {
            'dept_name': dept_obj.name, 'dept_user': users.count(),
            'owner': dept_obj.owner, 'description': dept_obj.description,
            'gender': {'male': users.filter(gender=1).count(),
                       'female': users.filter(gender=2).count(),
                       'unknown': users.filter(gender=0).count()},
            'sub_dept_map': [],
        }
        for child in authorized.filter(parent=dept_obj):
            child_fields = self.field_policy.allowed(child)
            child_data = {}
            if 'name' in child_fields:
                child_data['name'] = child.name
            # The subtree user count is field-governed, under the same
            # dept_user permission as this endpoint's top-level count.
            if 'dept_user' in child_fields:
                child_ids = authorized.filter(pk__in=descendants(child.pk)).values_list('pk', flat=True)
                child_data['count'] = Users.objects.exclude(is_superuser=True).filter(dept_id__in=child_ids).count()
            data['sub_dept_map'].append(child_data)
        if not request.user.is_superuser:
            allowed = self.field_policy.allowed(dept_obj)
            aliases = {'dept_name': 'name'}
            data = {key: value for key, value in data.items() if aliases.get(key, key) in allowed}
        return SuccessResponse(data)
