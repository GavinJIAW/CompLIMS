# -*- coding: utf-8 -*-


from coreadmin.system.models import LoginLog
from coreadmin.utils.serializers import CustomModelSerializer
from coreadmin.utils.viewset import CustomModelViewSet
from coreadmin.system.views.operation_log import LogReadOnlyMixin
from coreadmin.utils.json_response import ErrorResponse
from rest_framework.decorators import action


class LoginLogSerializer(CustomModelSerializer):
    """
    登录日志权限-序列化器
    """

    class Meta:
        model = LoginLog
        fields = "__all__"
        read_only_fields = ["id"]


class LoginLogViewSet(LogReadOnlyMixin, CustomModelViewSet):
    """
    登录日志接口
    list:查询
    create:新增
    update:修改
    retrieve:单例
    destroy:删除
    """
    queryset = LoginLog.objects.all()
    serializer_class = LoginLogSerializer
    # extra_filter_class = []

    @action(methods=['get'], detail=False)
    def field_permission(self, request):
        return ErrorResponse(msg='Log field-permission lookup is disabled.', status=405)
