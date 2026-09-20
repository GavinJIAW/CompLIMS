from django.db import transaction
from django.db.models import ProtectedError
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, ValidationError
from coreadmin.utils.viewset import CustomModelViewSet
from coreadmin.utils.json_response import DetailResponse, ErrorResponse
from coreadmin.access.context import AccessContext
from coreadmin.access.registry import REGISTRY
from coreadmin.access.projection import field_metadata
from lims.shared.aggregate_authority import child_fields
from lims.shared.m2_contract import CHILDREN


class Conflict(APIException):
    status_code = 409
    default_detail = 'The document state conflicts with this operation.'


class AggregateViewSet(CustomModelViewSet):
    """P0 authority plus aggregate-only writes; no inherited bulk write surface."""
    def handle_exception(self, exc):
        if isinstance(exc, (Conflict, ProtectedError)):
            return ErrorResponse(msg=str(exc), status=409, code=409)
        return super().handle_exception(exc)

    def get_serializer(self, *args, **kwargs):
        if 'data' in kwargs and not isinstance(kwargs['data'], dict):
            raise ValidationError('Expected one aggregate object.')
        return super().get_serializer(*args, **kwargs)

    @action(methods=['get'], detail=False)
    def field_permission(self, request):
        resource = self.resource
        result = field_metadata(request.user, resource, self.queryset.model)
        result['_children'] = {}
        # Projection is a UI hint; actual object writes/read use contributing grants.
        from coreadmin.system.models import FieldPermission
        from lims.shared.m2_contract import CHILD_READ, CHILD_CREATE, CHILD_UPDATE
        for model in CHILDREN[resource]:
            metadata = result['_children'][model] = {}
            for name, method, mode, flag in [('retrieve', 'GET', 'read', 'is_query'), ('create', 'POST', 'create', 'is_create'), ('update', 'PUT', 'update', 'is_update')]:
                ctx = AccessContext(request.user, REGISTRY[resource, name, method])
                ceiling = set({'read': CHILD_READ, 'create': CHILD_CREATE, 'update': CHILD_UPDATE}[mode][model].split())
                fields = set()
                if ctx.allowed():
                    if ctx.admin:
                        fields = ceiling
                    else:
                        for grant in ctx.grants:
                            fields.update(FieldPermission.objects.filter(role_id=grant.role_id, field__menu_id=grant.menu_id, field__model=model, **{flag: True}).values_list('field__field_name', flat=True))
                for key in fields & ceiling:
                    metadata.setdefault(key, {})[flag] = True
        return DetailResponse(data=result)

    def perform_create(self, serializer):
        serializer.save(**self.access_context.create_attribution())

    def perform_update(self, serializer):
        serializer.save(modifier=str(self.request.user.pk))

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if hasattr(obj, 'status') and obj.status != 'DRAFT':
            raise Conflict('Only DRAFT documents can be deleted.')
        obj.delete()
        return DetailResponse(data=[])
