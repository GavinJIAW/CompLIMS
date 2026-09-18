from collections.abc import Mapping

import re

from django_restql.fields import DynamicSerializerMethodField
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db import connection
from django.db.models import Q, Case, When, Value, IntegerField
from application import dispatch
from coreadmin.system.models import Users, Role, Dept
from coreadmin.system.views.role import RoleSerializer
from coreadmin.utils.json_response import ErrorResponse, DetailResponse, SuccessResponse
from coreadmin.utils.serializers import CustomModelSerializer
from coreadmin.utils.validator import CustomUniqueValidator
from coreadmin.utils.viewset import CustomModelViewSet, PatchAsUpdateFilterMixin


def recursion(instance, parent, result):
    new_instance = getattr(instance, parent, None)
    res = []
    data = getattr(instance, result, None)
    if data:
        res.append(data)
    if new_instance:
        array = recursion(new_instance, parent, result)
        res += array
    return res

class UserSerializer(CustomModelSerializer):
    """
    用户管理-序列化器
    """
    dept_name = serializers.CharField(source='dept.name', read_only=True)
    role_info = DynamicSerializerMethodField()
    dept_name_all = serializers.SerializerMethodField()

    class Meta:
        model = Users
        read_only_fields = ["id"]
        exclude = ["password"]
        extra_kwargs = {
            "post": {"required": False},
            "mobile": {"required": False},
        }

    def get_dept_name_all(self, instance):
        dept_name_all = recursion(instance.dept, "parent", "name")
        dept_name_all.reverse()
        return "/".join(dept_name_all)

    def get_role_info(self, instance, parsed_query):
        roles = instance.role.all()
        # You can do what ever you want in here
        # `parsed_query` param is passed to BookSerializer to allow further querying
        serializer = RoleSerializer(
            roles,
            many=True,
            parsed_query=parsed_query
        )
        return serializer.data


class UserWriteSerializer(CustomModelSerializer):
    """A fixed input ceiling, independent of dynamic field presentation."""

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown = set(data) - set(self.Meta.fields)
            if unknown:
                raise serializers.ValidationError({key: ["不允许通过用户接口写入此字段"] for key in sorted(unknown)})
        return super().to_internal_value(data)

    def create(self, validated_data):
        if self.request and self.request.user.is_authenticated:
            validated_data['creator'] = self.request.user
            validated_data['modifier'] = self.request.user.pk
        return super().create(validated_data)


class UserCreateSerializer(UserWriteSerializer):
    """
    用户新增-序列化器
    """

    username = serializers.CharField(
        max_length=50,
        validators=[
            CustomUniqueValidator(queryset=Users.objects.all(), message="账号必须唯一")
        ],
    )
    password = serializers.CharField(
        required=True, write_only=True, trim_whitespace=False,
    )

    def validate_password(self, value):
        from coreadmin.system.services.auth import password_policy
        password_policy(value)
        return value

    def create(self, validated_data):
        from coreadmin.system.services.auth import UserService
        return UserService.create(validated_data, super().create)

    class Meta:
        model = Users
        fields = ('username', 'password', 'name', 'email', 'mobile', 'avatar',
                  'gender', 'user_type', 'is_active')
        extra_kwargs = {"mobile": {"required": False}}


class UserUpdateSerializer(UserWriteSerializer):
    """
    用户修改-序列化器
    """

    username = serializers.CharField(
        max_length=50,
        validators=[
            CustomUniqueValidator(queryset=Users.objects.all(), message="账号必须唯一")
        ],
    )

    def update(self, instance, validated_data):
        # Server-controlled reset; client-supplied counters are rejected above.
        if validated_data.get('is_active'):
            validated_data['login_error_count'] = 0
        from coreadmin.system.services.auth import UserService
        return UserService.update(instance, validated_data, super().update)

    class Meta:
        model = Users
        fields = ('username', 'name', 'email', 'mobile', 'avatar',
                  'gender', 'user_type', 'is_active')
        extra_kwargs = {"mobile": {"required": False}}


class UserInfoUpdateSerializer(CustomModelSerializer):
    """
    用户修改-序列化器
    """
    mobile = serializers.CharField(
        max_length=50,
        validators=[
            CustomUniqueValidator(queryset=Users.objects.all(), message="手机号必须唯一")
        ],
        allow_blank=True
    )

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)

    class Meta:
        model = Users
        fields = ['email', 'mobile', 'avatar', 'name', 'gender']
        extra_kwargs = {
            "post": {"required": False, "read_only": True},
            "mobile": {"required": False},
        }


class ExportUserProfileSerializer(CustomModelSerializer):
    """
    用户导出 序列化器
    """

    last_login = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S", required=False, read_only=True
    )
    is_active = serializers.SerializerMethodField(read_only=True)
    dept_name = serializers.CharField(source="dept.name", default="")
    dept_owner = serializers.CharField(source="dept.owner", default="")
    gender = serializers.CharField(source="get_gender_display", read_only=True)

    def get_is_active(self, instance):
        return "启用" if instance.is_active else "停用"

    class Meta:
        model = Users
        fields = (
            "username",
            "name",
            "email",
            "mobile",
            "gender",
            "is_active",
            "last_login",
            "dept_name",
            "dept_owner",
        )


class UserProfileImportSerializer(CustomModelSerializer):
    password = serializers.CharField(read_only=True, required=False)

    class Meta:
        model = Users
        exclude = (
            "post",
            "user_permissions",
            "groups",
            "is_superuser",
            "date_joined",
        )


class UserViewSet(PatchAsUpdateFilterMixin, CustomModelViewSet):
    """
    用户接口
    list:查询
    create:新增
    update:修改
    retrieve:单例
    destroy:删除
    """

    queryset = Users.objects.exclude(is_superuser=1).all()
    serializer_class = UserSerializer
    create_serializer_class = UserCreateSerializer
    update_serializer_class = UserUpdateSerializer
    partial_update_serializer_class = UserUpdateSerializer

    def get_permissions(self):
        if self.action == 'import_data':
            return []  # Both URL aliases return the same disabled-endpoint response.
        return super().get_permissions()

    @action(methods=['get', 'post'], detail=False)
    def import_data(self, request, *args, **kwargs):
        return ErrorResponse(msg="用户导入暂时禁用", status=405)

    filter_fields = ["name", "username", "gender", "is_active", "dept", "user_type"]
    search_fields = ["username", "name", "dept__name", "role__name"]
    # 导出
    export_field_label = {
        "username": "用户账号",
        "name": "用户名称",
        "email": "用户邮箱",
        "mobile": "手机号码",
        "gender": "用户性别",
        "is_active": "帐号状态",
        "last_login": "最后登录时间",
        "dept_name": "部门名称",
        "dept_owner": "部门负责人",
    }
    export_serializer_class = ExportUserProfileSerializer
    # 导入
    import_serializer_class = UserProfileImportSerializer
    import_field_dict = {
        "username": "登录账号",
        "name": "用户名称",
        "email": "用户邮箱",
        "mobile": "手机号码",
        "gender": {
            "title": "用户性别",
            "choices": {
                "data": {"未知": 2, "男": 1, "女": 0},
            }
        },
        "is_active": {
            "title": "帐号状态",
            "choices": {
                "data": {"启用": True, "禁用": False},
            }
        },
        "dept": {"title": "部门", "choices": {"queryset": Dept.objects.filter(status=True), "values_name": "name"}},
        "role": {"title": "角色", "choices": {"queryset": Role.objects.filter(status=True), "values_name": "name"}},
    }

    @action(methods=["GET"], detail=False, permission_classes=[IsAuthenticated])
    def user_info(self, request):
        """获取当前用户信息"""
        user = request.user
        result = {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "mobile": user.mobile,
            "user_type": user.user_type,
            "gender": user.gender,
            "email": user.email,
            "avatar": user.avatar,
            "dept": user.dept_id,
            "is_superuser": user.is_superuser,
            "role": user.role.filter(status=True).values_list('id', flat=True),
            "pwd_change_count":user.pwd_change_count
        }
        if hasattr(connection, 'tenant'):
            result['tenant_id'] = connection.tenant and connection.tenant.id
            result['tenant_name'] = connection.tenant and connection.tenant.name
        dept = getattr(user, 'dept', None)
        if dept:
            result['dept_info'] = {
                'dept_id': dept.id,
                'dept_name': dept.name
            }
        else:
            result['dept_info'] = {
                'dept_id': None,
                'dept_name': "暂无部门"
            }
        role = getattr(user, 'role', None)
        if role:
            result['role_info'] = role.filter(status=True).values('id', 'name', 'key')
        return DetailResponse(data=result, msg="获取成功")

    @action(methods=["PUT"], detail=False, permission_classes=[IsAuthenticated])
    def update_user_info(self, request):
        """修改当前用户信息"""
        serializer = UserInfoUpdateSerializer(request.user, data=request.data, request=request)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return DetailResponse(data=None, msg="修改成功")

    @action(methods=["PUT"], detail=False, permission_classes=[IsAuthenticated])
    def change_password(self, request, *args, **kwargs):
        from coreadmin.system.services.auth import AuthService
        AuthService.change_password(request.user.pk, request.data.get('oldPassword'),
            request.data.get('newPassword'), request.data.get('newPassword2'))
        return DetailResponse(msg="密码已修改，请重新登录")

    @action(methods=["post"], detail=False, permission_classes=[IsAuthenticated])
    def login_change_password(self, request, *args, **kwargs):
        # First-login clients now use change_password with the current password.
        return ErrorResponse(msg="Use change_password with the current password.", status=405)

    @action(methods=["PUT"], detail=True, permission_classes=[IsAuthenticated])
    def reset_to_default_password(self, request, pk):
        return ErrorResponse(msg="Shared default passwords are disabled.", status=405)

    @action(methods=["PUT"], detail=True)
    def reset_password(self, request, pk):
        from coreadmin.system.services.auth import AuthService
        AuthService.reset_password(pk, request.data.get('newPassword'), request.data.get('newPassword2'))
        return DetailResponse(msg="密码已重置，用户需要重新登录并改密")

    def list(self, request, *args, **kwargs):
        from coreadmin.access.context import context_for, descendants
        from rest_framework.exceptions import ValidationError
        queryset = context_for(request, self).scope(self.get_queryset())
        dept_id = request.query_params.get('dept')
        show_all = request.query_params.get('show_all', '0')
        if show_all not in ('0', '1', ''):
            raise ValidationError({'show_all': 'Expected 0 or 1.'})
        if dept_id and show_all == '1':
            try:
                queryset = queryset.filter(dept_id__in=descendants(int(dept_id)))
            except (TypeError, ValueError):
                raise ValidationError({'dept': 'Invalid department ID.'})
        queryset = self.filter_queryset(queryset).exclude(id=request.user.id).distinct()
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True, request=request).data)
        return SuccessResponse(data=self.get_serializer(queryset, many=True, request=request).data, msg="获取成功")
