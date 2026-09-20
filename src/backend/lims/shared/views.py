from django.db.models import ProtectedError
from rest_framework.exceptions import APIException
from rest_framework.decorators import action
from coreadmin.utils.viewset import CustomModelViewSet
from coreadmin.utils.field_permission import FieldPermissionMixin
from lims.shared.services import master_command, save_aggregate


class ReferencedMaster(APIException):
    status_code = 409
    default_detail = 'This master is referenced; disable it or remove its references first.'


class MasterViewSet(FieldPermissionMixin, CustomModelViewSet):
    filter_fields = ['number', 'name', 'enabled']
    ordering_fields = ['number', 'name', 'enabled', 'create_datetime', 'update_datetime']
    search_fields = ['number', 'name']

    @action(methods=['get'], detail=False)
    def field_permission(self, request):
        from coreadmin.access.projection import field_metadata
        from coreadmin.access.registry import resource_for, REGISTRY
        from coreadmin.access.context import AccessContext
        from coreadmin.utils.json_response import DetailResponse
        from lims.shared.authority import row_fields
        resource = resource_for(self)
        result = field_metadata(request.user, resource, self.queryset.model)
        row_model = self.serializer_class.row_model
        if row_model:
            result['_rows'] = {}
            for name, method, mode, flag in [('retrieve', 'GET', 'read', 'is_query'), ('create', 'POST', 'create', 'is_create'), ('update', 'PUT', 'update', 'is_update')]:
                context = AccessContext(request.user, REGISTRY[resource, name, method])
                if context.allowed():
                    for key in row_fields(context, row_model, mode):
                        result['_rows'].setdefault(key, {})[flag] = True
        return DetailResponse(data=result)

    def create(self, request, *args, **kwargs):
        with master_command():
            return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        with master_command():
            return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        with master_command():
            try:
                return super().destroy(request, *args, **kwargs)
            except ProtectedError:
                from coreadmin.utils.json_response import ErrorResponse
                return ErrorResponse(msg=str(ReferencedMaster.default_detail), status=409, code=409)

    def get_serializer(self, *args, **kwargs):
        if isinstance(kwargs.get('data'), list):
            from rest_framework.exceptions import ValidationError
            raise ValidationError('M1 master writes require one object.')
        return super().get_serializer(*args, **kwargs)

    def perform_create(self, serializer):
        save_aggregate(serializer, **self.access_context.create_attribution())

    def perform_update(self, serializer):
        save_aggregate(serializer, modifier=str(self.request.user.pk))
