from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.db import IntegrityError, close_old_connections, connection
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from lims.customer.models import Customer
from lims.commercial.models import Contract, Quotation
from lims.commercial.aggregate_views import AggregateViewSet
from . import test_workflow as workflow


class SourceReviewFixTests(TestCase):
    setUp = workflow.WorkflowTests.setUp
    api = workflow.WorkflowTests.api
    create = workflow.WorkflowTests.create

    def accepted(self):
        q = self.create()
        for action in ('send', 'accept'):
            self.api('post', 'quotation', {}, q['id'], action)
        return q

    def test_existing_direct_contract_number_is_controlled_conflict(self):
        existing = self.create('contract', 'C001')
        q = self.accepted()
        before = self.api('get', 'quotation', pk=q['id'])
        response = self.client.post(f"/api/lims/quotation/{q['id']}/create_contract/", {'number': 'C001', 'contract_date': '2026-09-20'}, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['msg'], 'Contract number already exists.')
        self.assertEqual(Contract.objects.filter(number='C001').count(), 1)
        self.assertFalse(Contract.objects.filter(source_quotation_id=q['id']).exists())
        self.assertEqual(self.api('get', 'contract', pk=existing['id']), existing)
        self.assertEqual(self.api('get', 'quotation', pk=q['id']), before)

    def test_unrelated_database_check_error_is_reraised(self):
        q = self.accepted()
        original = Contract.objects.create
        def invalid_total(**kwargs):
            return original(**{**kwargs, 'total_amount': '-1.00'})
        def propagate(view, exc):
            # Observe the command's original exception before Foundation turns
            # unhandled database failures into its generic HTTP response.
            raise exc
        with patch.object(Contract.objects, 'create', side_effect=invalid_total), patch.object(AggregateViewSet, 'handle_exception', new=propagate):
            with self.assertRaises(IntegrityError):
                self.client.post(f"/api/lims/quotation/{q['id']}/create_contract/", {'number': 'BAD-CHECK', 'contract_date': '2026-09-20'}, format='json')
        self.assertFalse(Contract.objects.exists())
        self.assertEqual(Quotation.objects.get(pk=q['id']).status, 'ACCEPTED')

    def assert_mixed_rejected(self, resource, representation, items=False):
        before = self.create(resource, 'DOC')
        group = before['schemes'][0]
        if items:
            original = group['items'][0]
            groups = [{'id': group['id'], 'name_snapshot': 'must rollback', 'items': [
                {'id': original['id'], 'sequence': 2, 'unit_price': '100.00'},
                {'sequence': representation, 'source_product': self.product.pk},
            ]}]
        else:
            groups = [
                {'id': group['id'], 'sequence': 2, 'name_snapshot': 'must rollback', 'items': []},
                {'sequence': representation, 'name_snapshot': 'new'},
            ]
        self.api('patch', resource, {'remark': 'must rollback', 'adjustment_amount': '9.00', 'schemes': groups}, before['id'], status=400)
        self.assertEqual(self.api('get', resource, pk=before['id']), before)
        model = Quotation if resource == 'quotation' else Contract
        self.assertEqual(model.objects.count(), 1)
        self.assertEqual(model.objects.get().schemes.count(), 1)
        self.assertEqual(model.objects.get().schemes.get().items.count(), 1)
        # Failed CREATE must not leave even the aggregate header behind.
        body = {'number': 'FAILED', 'customer': self.customer.pk, resource + '_date': '2026-09-20',
                'schemes': [{'sequence': 1, 'name_snapshot': 'new', 'items': [
                    {'sequence': 2, 'source_product': self.product.pk},
                    {'sequence': representation, 'source_product': self.product.pk},
                ]}] if items else [{'sequence': 2, 'name_snapshot': 'A'}, {'sequence': representation, 'name_snapshot': 'B'}]}
        self.api('post', resource, body, status=400)
        self.assertEqual(model.objects.count(), 1)

    def test_quotation_group_integer_and_string(self):
        self.assert_mixed_rejected('quotation', '2')

    def test_quotation_group_integer_and_zero_padded_string(self):
        self.assert_mixed_rejected('quotation', '02')

    def test_quotation_item_mixed_representations(self):
        self.assert_mixed_rejected('quotation', '02', items=True)

    def test_contract_group_mixed_representations(self):
        self.assert_mixed_rejected('contract', '2')

    def test_contract_item_mixed_representations(self):
        self.assert_mixed_rejected('contract', '02', items=True)

    def test_retained_group_and_item_reorder_and_omitted_sequence(self):
        for resource in ('quotation', 'contract'):
            with self.subTest(resource=resource):
                document = self.create(resource, resource, schemes=[
                    {'sequence': 1, 'name_snapshot': 'A', 'items': [
                        {'sequence': 1, 'source_product': self.product.pk},
                        {'sequence': 2, 'source_product': self.product.pk}]},
                    {'sequence': 2, 'name_snapshot': 'B'}])
                a, b = document['schemes']
                first, second = a['items']
                updated = self.api('patch', resource, {'schemes': [
                    {'id': a['id'], 'sequence': '02', 'items': [
                        {'id': first['id'], 'sequence': '2'}, {'id': second['id'], 'sequence': 1}]},
                    {'id': b['id'], 'sequence': '1'},
                ]}, document['id'])
                self.assertEqual([g['id'] for g in updated['schemes']], [b['id'], a['id']])
                self.assertEqual([r['id'] for r in updated['schemes'][1]['items']], [second['id'], first['id']])
                unchanged = self.api('patch', resource, {'schemes': [{'id': b['id']}, {'id': a['id'], 'items': [{'id': second['id']}, {'id': first['id']}]}]}, document['id'])
                self.assertEqual(unchanged['schemes'], updated['schemes'])

    def test_sequence_uses_model_serializer_validation(self):
        for value in (True, 2.5, 'invalid', None):
            with self.subTest(value=value):
                self.api('post', 'quotation', {'number': 'INVALID', 'customer': self.customer.pk, 'quotation_date': '2026-09-20',
                    'schemes': [{'sequence': value, 'name_snapshot': 'A'}]}, status=400)
        self.api('post', 'quotation', {'number': 'MISSING', 'customer': self.customer.pk, 'quotation_date': '2026-09-20',
            'schemes': [{'name_snapshot': 'A'}]}, status=400)
        self.assertFalse(Quotation.objects.exists())


class ContractNumberRaceTests(TransactionTestCase):
    setUp = workflow.WorkflowTests.setUp
    api = workflow.WorkflowTests.api
    create = workflow.WorkflowTests.create

    def test_different_quotations_same_number_real_postgresql_race(self):
        self.assertEqual(connection.vendor, 'postgresql')
        other_customer = Customer.objects.create(number='OTHER', name='Other customer')
        quotations = [self.create(number='QA'), self.create(number='QB', customer=other_customer.pk)]
        for quotation in quotations:
            for action in ('send', 'accept'):
                self.api('post', 'quotation', {}, quotation['id'], action)
        barrier = Barrier(2)
        original = Contract.objects.create
        def synchronized_insert(**kwargs):
            # Only synchronize entry: both actual PostgreSQL INSERTs execute.
            barrier.wait(timeout=15)
            return original(**kwargs)
        def worker(qid):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(self.admin)
                response = client.post(f'/api/lims/quotation/{qid}/create_contract/',
                    {'number': 'RACE-001', 'contract_date': '2026-09-20'}, format='json')
                if response.status_code == 409:
                    self.assertEqual(response.data['msg'], 'Contract number already exists.')
                return qid, response.status_code
            finally:
                close_old_connections()
        with patch.object(Contract.objects, 'create', side_effect=synchronized_insert):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(worker, [q['id'] for q in quotations]))
        self.assertEqual(sorted(status for _, status in results), [200, 409])
        self.assertEqual(Contract.objects.filter(number='RACE-001').count(), 1)
        winner = next(qid for qid, status in results if status == 200)
        self.assertEqual(Contract.objects.get(number='RACE-001').source_quotation_id, winner)
        self.assertEqual(Quotation.objects.filter(status='ACCEPTED').count(), 2)
