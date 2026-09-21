from rest_framework.decorators import action
from coreadmin.utils.json_response import DetailResponse
from lims.commercial.aggregate_views import AggregateViewSet
from .models import Quotation, Contract
from .serializers import QuotationSerializer, ContractSerializer
from .services import transition, convert


class CommercialViewSet(AggregateViewSet):
    search_fields = ['number', 'customer_name_snapshot']

    def state_response(self, name):
        obj = transition(self, name)
        return DetailResponse(data=self.get_serializer(obj).data)


class QuotationViewSet(CommercialViewSet):
    resource = 'quotation'
    queryset = Quotation.objects.prefetch_related('schemes__items').all()
    serializer_class = QuotationSerializer
    filter_fields = ['number', 'customer', 'customer_name_snapshot', 'status', 'quotation_date', 'valid_until']
    ordering_fields = filter_fields + ['create_datetime']

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        return self.state_response('send')

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        return self.state_response('accept')

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        return self.state_response('reject')

    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        return self.state_response('void')

    @action(detail=True, methods=['post'])
    def create_contract(self, request, pk=None):
        obj = convert(self)
        # No implicit contract READ authority is granted by conversion.
        return DetailResponse(data={'id': obj.pk})


class ContractViewSet(CommercialViewSet):
    resource = 'contract'
    queryset = Contract.objects.prefetch_related('schemes__items').all()
    serializer_class = ContractSerializer
    filter_fields = ['number', 'customer', 'customer_name_snapshot', 'status', 'contract_date']
    ordering_fields = filter_fields + ['create_datetime']

    @action(detail=True, methods=['post'])
    def sign(self, request, pk=None):
        return self.state_response('sign')

    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        return self.state_response('void')
