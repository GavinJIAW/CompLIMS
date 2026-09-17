# -*- coding: utf-8 -*-


from coreadmin.utils.permission import AuthorizationMutationMixin
from coreadmin.system.models import ApiWhiteList
from coreadmin.utils.serializers import CustomModelSerializer
from coreadmin.utils.viewset import CustomModelViewSet, PatchAsUpdateFilterMixin


class ApiWhiteListSerializer(CustomModelSerializer):
    """
    接口白名单-序列化器
    """

    class Meta:
        model = ApiWhiteList
        fields = "__all__"
        read_only_fields = ["id"]





class ApiWhiteListViewSet(AuthorizationMutationMixin, PatchAsUpdateFilterMixin, CustomModelViewSet):
    """
    接口白名单
    list:查询
    create:新增
    update:修改
    retrieve:单例
    destroy:删除
    """
    # B1 temporary opt-in, protected by AuthorizationMutationMixin.
    bulk_delete_enabled = True
    queryset = ApiWhiteList.objects.all()
    serializer_class = ApiWhiteListSerializer
    # permission_classes = []
