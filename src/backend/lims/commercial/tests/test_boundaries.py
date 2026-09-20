from copy import deepcopy
from unittest.mock import patch
from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from coreadmin.system.models import FieldPermission, Users, OperationLog
from lims.customer.models import CustomerContact
from lims.commercial.models import Quotation, Contract, ContractSchemeItem
from lims.commercial.services import requirements
from rest_framework.exceptions import ValidationError
from . import test_workflow as workflow


class BoundaryTests(TestCase):
    setUp = workflow.WorkflowTests.setUp
    api = workflow.WorkflowTests.api
    create = workflow.WorkflowTests.create
    permit = workflow.WorkflowTests.permit
    permit_sources = workflow.WorkflowTests.permit_sources

    def test_contact_conditional_constraint_database(self):
        CustomerContact.objects.create(customer=self.customer, name='A', is_default=True)
        contact = CustomerContact.objects.create(customer=self.customer, name='B', is_default=True, enabled=False)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CustomerContact.objects.filter(pk=contact.pk).update(enabled=True)

    def test_customer_protect(self):
        self.create()
        self.api('delete', 'customer', pk=self.customer.pk, status=409)

    def test_child_creation_requires_real_product(self):
        self.api('post', 'quotation', {'number':'Q', 'customer':self.customer.pk,'quotation_date':'2026-09-20','schemes':[{'sequence':1,'name_snapshot':'Group','items':[{'sequence':1}]}]}, status=400)

    def test_duplicate_group_sequence(self):
        self.api('post', 'quotation', {'number':'Q','customer':self.customer.pk,'quotation_date':'2026-09-20','schemes':[{'sequence':1,'name_snapshot':'A'},{'sequence':1,'name_snapshot':'B'}]},status=400)

    def test_duplicate_item_sequence(self):
        self.api('post', 'quotation', {'number':'Q','customer':self.customer.pk,'quotation_date':'2026-09-20','schemes':[{'sequence':1,'name_snapshot':'A','items':[{'sequence':1,'source_product':self.product.pk},{'sequence':1,'source_product':self.product.pk}]}]},status=400)

    def test_null_collections_rejected(self):
        q=self.create()
        self.api('patch','quotation',{'schemes':None},q['id'],status=400)
        self.api('patch','quotation',{'schemes':[{'id':q['schemes'][0]['id'],'items':None}]},q['id'],status=400)

    def test_table_partial_columns_and_invalid_structure(self):
        schema=[{'key':'rows','label':'Rows','type':'table','required':True,'columns':[{'key':'value','label':'Value','type':'float','required':True}]}]
        requirements(schema,{})
        requirements(schema,{'rows':[{}, {'value':1.5}]})
        for value in ({'rows':'bad'},{'rows':[{'unknown':1}]},{'rows':[{'value':'bad'}]}):
            with self.assertRaises(ValidationError):requirements(schema,value)

    def test_actual_file_entities_rejected(self):
        for kind in ('file','image','csv'):
            schema=[{'key':'file','label':'File','type':kind,'required':False}]
            requirements(schema,{})
            for value in (1,[1],{'id':1},'file-id'):
                with self.assertRaises(ValidationError):requirements(schema,{'file':value})

    def test_stored_requirement_schema_is_authority(self):
        q=self.create();group=q['schemes'][0];row=group['items'][0]
        self.service.requirement_template=[];self.service.save()
        self.api('patch','quotation',{'schemes':[{'id':group['id'],'items':[{'id':row['id'],'requirement_data':{'count':9}}]}]},q['id'])

    def test_scheme_identity_cannot_change(self):
        q=self.create()
        self.api('patch','quotation',{'schemes':[{'id':q['schemes'][0]['id'],'source_scheme':self.scheme.pk}]},q['id'],status=400)

    def test_new_disabled_product_rejected(self):
        q=self.create();self.product.enabled=False;self.product.save()
        self.api('patch','quotation',{'schemes':[{'id':q['schemes'][0]['id'],'items':[{'sequence':1,'source_product':self.product.pk}]}]},q['id'],status=400)

    def test_new_disabled_scheme_rejected(self):
        self.scheme.enabled=False;self.scheme.save()
        self.api('post','quotation',{'number':'Q','customer':self.customer.pk,'quotation_date':'2026-09-20','schemes':[{'sequence':1,'source_scheme':self.scheme.pk}]},status=400)

    def test_source_product_field_permission_required(self):
        self.permit_sources();self.permit('quotation','Create')
        FieldPermission.objects.filter(field__model='Product',field__field_name='reference_price').update(is_query=False)
        self.client.force_authenticate(self.actor)
        self.api('post','quotation',{'number':'Q','customer':self.customer.pk,'quotation_date':'2026-09-20','schemes':[{'sequence':1,'source_scheme':self.scheme.pk}]},status=403)

    def test_source_service_template_permission_required(self):
        self.permit_sources();self.permit('quotation','Create')
        FieldPermission.objects.filter(field__model='Service',field__field_name='requirement_template').update(is_query=False)
        self.client.force_authenticate(self.actor)
        self.api('post','quotation',{'number':'Q','customer':self.customer.pk,'quotation_date':'2026-09-20','schemes':[{'sequence':1,'source_scheme':self.scheme.pk}]},status=403)

    def test_nested_update_uses_only_contributing_grants(self):
        q=self.create();obj=Quotation.objects.get(pk=q['id']);obj.dept_belong_id=self.dept.pk;obj.save()
        permitted=self.permit('quotation','Update',2);self.permit('quotation','Update',0)
        FieldPermission.objects.filter(role=permitted.role,field__model='QuotationSchemeItem',field__field_name='unit_price').update(is_update=False)
        self.client.force_authenticate(self.actor)
        self.api('patch','quotation',{'schemes':[{'id':q['schemes'][0]['id'],'items':[{'id':q['schemes'][0]['items'][0]['id'],'unit_price':'2'}]}]},q['id'],status=400)

    def test_header_write_field_denied(self):
        q=self.create();permission=self.permit('quotation','Update')
        FieldPermission.objects.filter(role=permission.role,field__field_name='remark').update(is_update=False)
        self.client.force_authenticate(self.actor)
        self.api('patch','quotation',{'remark':'no'},q['id'],status=400)

    def test_conversion_rejects_nonaccepted_and_no_target_authority(self):
        q=self.create()
        self.api('post','quotation',{'number':'C','contract_date':'2026-09-20'},q['id'],'create_contract',status=409)
        for action in ('send','accept'):self.api('post','quotation',{},q['id'],action)
        self.permit('quotation','CreateContract');self.client.force_authenticate(self.actor)
        self.api('post','quotation',{'number':'C','contract_date':'2026-09-20'},q['id'],'create_contract',status=403)

    def test_conversion_source_read_field_denied(self):
        q=self.create()
        for action in ('send','accept'):self.api('post','quotation',{},q['id'],action)
        permission=self.permit('quotation','CreateContract');self.permit('contract','Create');self.permit('customer','Retrieve')
        FieldPermission.objects.filter(role=permission.role,field__field_name='requirement_schema').update(is_query=False)
        self.client.force_authenticate(self.actor)
        self.api('post','quotation',{'number':'C','contract_date':'2026-09-20'},q['id'],'create_contract',status=403)

    def test_conversion_failure_rolls_back_all_layers(self):
        q=self.create()
        for action in ('send','accept'):self.api('post','quotation',{},q['id'],action)
        with patch.object(ContractSchemeItem,'save',side_effect=ValidationError('Injected late validation failure')):
            self.api('post','quotation',{'number':'C','contract_date':'2026-09-20'},q['id'],'create_contract',status=400)
        self.assertFalse(Contract.objects.exists())

    def test_conversion_does_not_reauthorize_snapshot_masters(self):
        q=self.create()
        for action in ('send','accept'):self.api('post','quotation',{},q['id'],action)
        self.permit('quotation','CreateContract');self.permit('contract','Create');self.permit('customer','Retrieve')
        self.client.force_authenticate(self.actor)
        self.api('post','quotation',{'number':'C','contract_date':'2026-09-20'},q['id'],'create_contract')

    def test_conversion_copy_not_linked_json(self):
        q=self.create()
        for action in ('send','accept'):self.api('post','quotation',{},q['id'],action)
        c=self.api('post','quotation',{'number':'C','contract_date':'2026-09-20'},q['id'],'create_contract')
        contract=Contract.objects.get(pk=c['id']);row=contract.schemes.get().items.get()
        self.api('patch','contract',{'schemes':[{'id':row.contract_scheme_id,'items':[{'id':row.pk,'requirement_data':{'count':10}}]}]},c['id'])
        self.assertEqual(Quotation.objects.get(pk=q['id']).schemes.get().items.get().requirement_data['count'],6)

    def test_empty_target_collection_deletes_groups(self):
        q=self.create()
        result=self.api('patch','quotation',{'schemes':[]},q['id'])
        self.assertEqual(result['schemes'],[]);self.assertEqual(result['subtotal'],'0.00')


class ConversionConcurrencyTests(TransactionTestCase):
    setUp = workflow.WorkflowTests.setUp
    api = workflow.WorkflowTests.api
    create = workflow.WorkflowTests.create

    def race(self, qid, action, bodies):
        barrier=Barrier(2)
        def worker(body):
            from django.db import close_old_connections
            close_old_connections()
            try:
                client=APIClient();client.force_authenticate(Users.objects.get(pk=self.admin.pk))
                barrier.wait(timeout=10)
                return client.post(f'/api/lims/quotation/{qid}/{action}/',body,format='json').status_code
            finally:close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:return sorted(pool.map(worker,bodies))

    def test_concurrent_send_only_one_transition(self):
        q=self.create()
        self.assertEqual(self.race(q['id'],'send',[{},{}]),[200,409])

    def test_concurrent_conversion_only_one_contract(self):
        q=self.create()
        for action in ('send','accept'):self.api('post','quotation',{},q['id'],action)
        self.assertEqual(self.race(q['id'],'create_contract',[{'number':'C1','contract_date':'2026-09-20'},{'number':'C2','contract_date':'2026-09-20'}]),[200,409])
        self.assertEqual(Contract.objects.count(),1)
