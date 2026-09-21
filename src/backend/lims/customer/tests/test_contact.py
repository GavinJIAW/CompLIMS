from io import StringIO
from django.test import TestCase
from django.db import IntegrityError, transaction
from django.core.management import call_command
from rest_framework.test import APIClient
from coreadmin.system.models import Users, FieldPermission, Menu, MenuField
from coreadmin.foundation_tests.access_fixtures import grant
from lims.customer.models import Customer, CustomerContact
from lims.customer.access_contract import READ, WRITE


class ContactTests(TestCase):
    def setUp(self):
        self.admin=Users.objects.create(username='admin',is_superuser=True,pwd_change_count=1)
        self.actor=Users.objects.create(username='actor',pwd_change_count=1)
        self.client=APIClient();self.client.force_authenticate(self.admin)
        self.a=Customer.objects.create(number='A',name='A')
        self.b=Customer.objects.create(number='B',name='B')
        self.one=CustomerContact.objects.create(customer=self.a,name='One')
        self.two=CustomerContact.objects.create(customer=self.a,name='Two')

    def permit(self,resource,suffix,scope=3):
        return grant(self.actor, resource+':'+suffix, {'customer':'Customer','contact':'CustomerContact'}[resource], fields=READ[resource].split(), create=WRITE[resource].split(), update=WRITE[resource].split(), scope=scope)

    def post(self,**values):
        return self.client.post('/api/lims/contact/',dict(name='New',customer=self.a.pk,**values),format='json')

    def patch(self,obj,**data):
        return self.client.patch(f'/api/lims/contact/{obj.pk}/',data,format='json')

    def test_crud_audit(self):
        r=self.post(gender=2,mobile='123',email='a@example.com',title='Engineer',address='Office')
        self.assertEqual(r.status_code,200,r.data);pk=r.data['data']['id']
        obj=CustomerContact.objects.get(pk=pk);self.assertEqual(obj.creator_id,self.admin.pk)
        self.assertEqual(self.client.get(f'/api/lims/contact/{pk}/').status_code,200)
        self.assertEqual(self.patch(obj,name='Changed').status_code,200)
        obj.refresh_from_db();self.assertEqual(obj.modifier,str(self.admin.pk))
        self.assertEqual(self.client.delete(f'/api/lims/contact/{pk}/').status_code,200)

    def test_gender_validation_and_default(self):
        self.assertEqual(self.post().data['data']['gender'],0)
        for gender in (-1,3,'other'):
            self.assertEqual(self.post(gender=gender).status_code,400)

    def test_gender_database_constraint(self):
        with self.assertRaises(IntegrityError),transaction.atomic():
            CustomerContact.objects.create(customer=self.a,name='Invalid',gender=9)

    def test_legacy_fields_rejected(self):
        for key in ('phone','department','remark'):
            self.assertEqual(self.post(**{key:'old'}).status_code,400)
        data=self.client.get(f'/api/lims/contact/{self.one.pk}/').data['data']
        self.assertFalse({'phone','department','remark'} & set(data))

    def test_exact_customer_filter(self):
        other=CustomerContact.objects.create(customer=self.b,name='Other')
        r=self.client.get('/api/lims/contact/',{'customer':self.b.pk})
        self.assertEqual([x['id'] for x in r.data['data']],[other.pk])

    def test_shared_all_and_nonall(self):
        self.client.force_authenticate(self.actor)
        self.assertEqual(self.client.get('/api/lims/contact/').status_code,403)
        g=self.permit('contact','Search')
        for scope in (0,1,2,4):
            g.data_range=scope;g.save()
            self.assertEqual(self.client.get('/api/lims/contact/').status_code,403)
        g.data_range=3;g.save();self.assertEqual(self.client.get('/api/lims/contact/').status_code,200)

    def test_normal_crud(self):
        for action in ('Search','Retrieve','Create','Update','Delete'):self.permit('contact',action)
        self.permit('customer','Retrieve');self.client.force_authenticate(self.actor)
        r=self.post();self.assertEqual(r.status_code,200,r.data)
        obj=CustomerContact.objects.get(pk=r.data['data']['id'])
        self.assertEqual(self.patch(obj,title='Engineer').status_code,200)
        self.assertEqual(self.client.delete(f'/api/lims/contact/{obj.pk}/').status_code,200)

    def test_customer_reference_authority(self):
        self.permit('contact','Create');self.client.force_authenticate(self.actor)
        self.assertEqual(self.post().status_code,403)
        self.permit('customer','Retrieve');self.assertEqual(self.post().status_code,200)

    def test_supervisor_reference_authority(self):
        self.permit('contact','Create');self.permit('customer','Retrieve');self.client.force_authenticate(self.actor)
        self.assertEqual(self.post(direct_supervisor=self.one.pk).status_code,403)
        self.permit('contact','Retrieve');self.assertEqual(self.post(direct_supervisor=self.one.pk).status_code,200)

    def test_field_read_write_and_metadata(self):
        for action in ('Search','Retrieve','Create','Update'):self.permit('contact',action)
        self.permit('customer','Retrieve');self.client.force_authenticate(self.actor)
        FieldPermission.objects.filter(field__model='CustomerContact',field__field_name='mobile').update(is_query=False,is_create=False,is_update=False)
        self.assertNotIn('mobile',self.client.get(f'/api/lims/contact/{self.one.pk}/').data['data'])
        self.assertEqual(self.post(mobile='denied').status_code,400)
        self.assertEqual(self.patch(self.one,mobile='denied').status_code,400)
        r=self.client.get('/api/lims/contact/field_permission/')
        self.assertEqual(r.status_code,200,r.data)

    def test_query_side_channels(self):
        self.permit('contact','Search');self.client.force_authenticate(self.actor)
        FieldPermission.objects.filter(field__model='CustomerContact',field__field_name__in=['customer','mobile']).update(is_query=False)
        for query in ({'customer':self.a.pk},{'customer__name':'A'},{'ordering':'customer'},{'search':'123'}):
            self.assertEqual(self.client.get('/api/lims/contact/',query).status_code,400)

    def test_self_and_cross_customer_supervisor_rejected(self):
        self.assertEqual(self.patch(self.one,direct_supervisor=self.one.pk).status_code,400)
        other=CustomerContact.objects.create(customer=self.b,name='Other')
        self.assertEqual(self.patch(self.one,direct_supervisor=other.pk).status_code,400)

    def test_cycles_and_customer_reassignment(self):
        self.assertEqual(self.patch(self.two,direct_supervisor=self.one.pk).status_code,200)
        three=CustomerContact.objects.create(customer=self.a,name='Three',direct_supervisor=self.two)
        self.assertEqual(self.patch(self.one,direct_supervisor=three.pk).status_code,400)
        self.assertEqual(self.patch(self.one,customer=self.b.pk).status_code,400)
        self.assertEqual(self.patch(self.two,customer=self.b.pk).status_code,400)

    def test_default_lifecycle(self):
        self.assertEqual(self.patch(self.one,is_default=True).status_code,200)
        self.assertEqual(self.patch(self.two,is_default=True).status_code,400)
        self.assertEqual(self.patch(self.two,enabled=False,is_default=True).status_code,200)
        self.assertEqual(self.patch(self.two,enabled=True).status_code,400)
        self.assertEqual(self.patch(self.one,enabled=False).status_code,200)
        self.assertEqual(self.patch(self.two,enabled=True).status_code,200)

    def test_default_constraint(self):
        CustomerContact.objects.filter(pk=self.one.pk).update(is_default=True)
        with self.assertRaises(IntegrityError),transaction.atomic():
            CustomerContact.objects.filter(pk=self.two.pk).update(is_default=True)

    def test_delete_protect_set_null(self):
        self.two.direct_supervisor=self.one;self.two.save()
        self.assertEqual(self.client.delete(f'/api/lims/customer/{self.a.pk}/').status_code,409)
        self.assertEqual(self.client.delete(f'/api/lims/contact/{self.one.pk}/').status_code,200)
        self.two.refresh_from_db();self.assertIsNone(self.two.direct_supervisor_id)

    def test_disabled_customer_reference(self):
        self.a.enabled=False;self.a.save()
        self.assertEqual(self.post().status_code,400)
        self.assertEqual(self.patch(self.one,title='Allowed').status_code,200)
        self.assertEqual(self.patch(self.one,customer=self.a.pk).status_code,200)

    def test_disabled_supervisor_new_reference(self):
        self.one.enabled=False;self.one.save()
        self.assertEqual(self.patch(self.two,direct_supervisor=self.one.pk).status_code,400)

    def test_menu_independent_and_legacy_cleanup(self):
        call_command('init_lims',stdout=StringIO())
        customer=Menu.objects.get(component_name='lims_customer')
        MenuField.objects.create(menu=customer,model='CustomerContact',field_name='phone',title='Legacy')
        MenuField.objects.create(menu=customer,model='Customer',field_name='contacts',title='Legacy')
        call_command('init_lims',stdout=StringIO())
        contact=Menu.objects.get(component_name='lims_contact')
        self.assertEqual(contact.parent_id,customer.parent_id)
        self.assertEqual((customer.name,contact.name),('客户管理','联系人管理'))
        self.assertFalse(MenuField.objects.filter(menu=customer,model='CustomerContact').exists())
        self.assertFalse(MenuField.objects.filter(menu=customer,field_name='contacts').exists())
        self.assertTrue(MenuField.objects.filter(menu=contact,model='CustomerContact',field_name='mobile').exists())
        before=list(MenuField.objects.order_by('id').values_list('id',flat=True))
        call_command('init_lims',stdout=StringIO())
        self.assertEqual(before,list(MenuField.objects.order_by('id').values_list('id',flat=True)))
