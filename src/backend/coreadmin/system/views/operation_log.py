# -*- coding: utf-8 -*-
from coreadmin.system.models import OperationLog
from rest_framework.decorators import action
from coreadmin.utils.json_response import ErrorResponse
from coreadmin.utils.log_sanitization import serialize_log_value
from coreadmin.utils.permission import SuperuserPermission
from coreadmin.utils.serializers import CustomModelSerializer
from coreadmin.utils.viewset import CustomModelViewSet, ReadOnlyAPIMixin


class LogReadOnlyMixin(ReadOnlyAPIMixin):
    """Temporary security-control-plane reads; ORM logging remains available."""

    def get_permissions(self):
        # Action-level legacy permissions must not bypass this boundary.
        return [SuperuserPermission()]

    @action(methods=['get', 'post'], detail=False)
    def import_data(self, request, *args, **kwargs):
        return ErrorResponse(msg='Log import is disabled.', status=405)

    @action(methods=['get'], detail=False)
    def update_template(self, request, *args, **kwargs):
        return ErrorResponse(msg='Log templates are disabled.', status=405)

    @action(methods=['get'], detail=False)
    def export_data(self, request, *args, **kwargs):
        return ErrorResponse(msg='Log export is disabled.', status=405)


class OperationLogSerializer(CustomModelSerializer):
    """Defensive read-time redaction; never rewrite historical rows."""

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field in ('request_body', 'json_result', 'request_msg'):
            if field in data:
                data[field] = serialize_log_value(getattr(instance, field), historical=True)
        return data

    class Meta:
        model = OperationLog
        fields = "__all__"
        read_only_fields = ["id"]


class OperationLogCreateUpdateSerializer(CustomModelSerializer):
    """
    操作日志  创建/更新时的列化器
    """

    class Meta:
        model = OperationLog
        fields = '__all__'


class OperationLogViewSet(LogReadOnlyMixin, CustomModelViewSet):
    """
    操作日志接口
    list:查询
    create:新增
    update:修改
    retrieve:单例
    destroy:删除
    """
    queryset = OperationLog.objects.order_by('-create_datetime')
    serializer_class = OperationLogSerializer
    # permission_classes = []
