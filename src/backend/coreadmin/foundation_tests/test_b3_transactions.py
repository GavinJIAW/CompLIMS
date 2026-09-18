"""Real rollback boundaries: TransactionTestCase, never a wrapping TestCase."""
from unittest.mock import patch
from django.db import transaction
from django.test import TransactionTestCase
from django.conf import settings
from rest_framework.test import APIClient
from coreadmin.system.models import (Users, Role, Menu, MenuButton, Dept,
    RoleMenuPermission, RoleMenuButtonPermission, MenuField, FieldPermission,
    MessageCenter, MessageCenterTargetUser, SystemConfig)
from application import dispatch


class TransactionTests(TransactionTestCase):
    def setUp(self):
        self.admin = Users.objects.create(username='admin', is_superuser=True, pwd_change_count=1)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.role = Role.objects.create(name='role', key='role')
        self.menu = Menu.objects.create(name='menu')
        self.other = Menu.objects.create(name='other')
        self.button = MenuButton.objects.create(menu=self.menu, name='button', value='button', api='/')
        self.dept = Dept.objects.create(name='dept')

    def test_batch_create_second_failure(self):
        from coreadmin.system.views.role import RoleCreateUpdateSerializer
        original = RoleCreateUpdateSerializer.create
        def fail(serializer, data):
            if data['key'] == 'second':
                raise RuntimeError('injected')
            return original(serializer, data)
        with patch.object(RoleCreateUpdateSerializer, 'create', fail):
            result = self.client.post('/api/system/role/', [{'name':'first','key':'first'}, {'name':'second','key':'second'}], format='json')
        self.assertEqual(result.status_code, 500)
        self.assertFalse(Role.objects.filter(key__in=['first','second']).exists())

    def test_save_auth_delete_create_rollback(self):
        from coreadmin.system.views.role_menu import RoleMenuPermissionSerializer
        old = RoleMenuPermission.objects.create(role=self.role, menu=self.menu)
        with patch.object(RoleMenuPermissionSerializer, 'create', side_effect=RuntimeError('injected')):
            result = self.client.post('/api/system/role_menu_permission/save_auth/',
                {'role':self.role.pk, 'menu':[self.other.pk]}, format='json')
        self.assertEqual(result.status_code, 500)
        self.assertEqual(list(RoleMenuPermission.objects.values_list('pk',flat=True)), [old.pk])

    def test_config_nth_failure_and_cache(self):
        parent = SystemConfig.objects.create(title='root',key='root')
        first = SystemConfig.objects.create(title='a',key='a',value='old',parent=parent)
        second = SystemConfig.objects.create(title='b',key='b',value='old',parent=parent)
        original = SystemConfig.save
        def fail(obj,*a,**kw):
            if obj.pk == second.pk: raise RuntimeError('injected')
            return original(obj,*a,**kw)
        with patch.object(SystemConfig,'save',fail):
            response = self.client.put('/api/system/system_config/save_content/',
                [dict(id=x.pk,title=x.title,key=x.key,parent=parent.pk,value='new') for x in [first,second]],format='json')
        self.assertEqual(response.status_code,500)
        first.refresh_from_db()
        self.assertEqual(first.value,'old')
        self.assertEqual(settings.SYSTEM_CONFIG['root.a'],'old')

    def test_message_recipient_failure(self):
        from coreadmin.system.views.message_center import MessageCenterTargetUserSerializer
        with patch.object(MessageCenterTargetUserSerializer,'create',side_effect=RuntimeError('injected')):
            response=self.client.post('/api/system/message_center/',
                {'title':'failed','content':'text','target_type':0,'target_user':[self.admin.pk]},format='json')
        self.assertEqual(response.status_code,500)
        self.assertFalse(MessageCenter.objects.exists())

    def test_custom_dept_save_failure(self):
        grant=RoleMenuButtonPermission.objects.create(role=self.role,menu_button=self.button,data_range=4)
        grant.dept.set([self.dept])
        original=RoleMenuButtonPermission.save
        def fail(obj,*a,**kw):
            if obj.pk==grant.pk: raise RuntimeError('injected')
            return original(obj,*a,**kw)
        with patch.object(RoleMenuButtonPermission,'save',fail):
            response=self.client.put('/api/system/role_menu_button_permission/set_role_menu_btn_data_range/',
                {'role_menu_btn_perm_id':grant.pk,'data_range':3,'dept':[]},format='json')
        self.assertEqual(response.status_code,500)
        grant.refresh_from_db()
        self.assertEqual(grant.data_range,4)
        self.assertEqual(list(grant.dept.values_list('pk',flat=True)),[self.dept.pk])

    def test_grant_m2m_failure(self):
        sample=RoleMenuButtonPermission.objects.create(role=self.role,menu_button=self.button)
        manager=type(sample.dept)
        sample.delete()
        with patch.object(manager,'set',side_effect=RuntimeError('injected')):
            response=self.client.put('/api/system/role_menu_button_permission/set_role_menu_btn/',
                {'roleId':self.role.pk,'btnId':self.button.pk,'isCheck':True,'data_range':4,'dept':[self.dept.pk]},format='json')
        self.assertEqual(response.status_code,500)
        self.assertFalse(RoleMenuButtonPermission.objects.exists())

    def test_field_batch_failure(self):
        a=MenuField.objects.create(menu=self.menu,model='Users',field_name='name',title='name')
        b=MenuField.objects.create(menu=self.menu,model='Users',field_name='email',title='email')
        original=FieldPermission.save
        def fail(obj,*args,**kwargs):
            if obj.field_id==b.pk: raise RuntimeError('injected')
            return original(obj,*args,**kwargs)
        with patch.object(FieldPermission,'save',fail):
            response=self.client.put(f'/api/system/role_menu_button_permission/{self.role.pk}/set_role_menu_field/',
                [dict(id=x.pk,is_query=True,is_create=False,is_update=False) for x in [a,b]],format='json')
        self.assertEqual(response.status_code,500)
        self.assertFalse(FieldPermission.objects.exists())

    def test_config_rollback_and_callback_failure(self):
        parent=SystemConfig.objects.create(title='root',key='root')
        obj=SystemConfig.objects.create(title='a',key='a',parent=parent,value='old')
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                obj.value='new';obj.save()
                raise RuntimeError('rollback')
        obj.refresh_from_db()
        self.assertEqual(obj.value,'old')
        self.assertEqual(settings.SYSTEM_CONFIG['root.a'],'old')
        with patch.object(dispatch,'refresh_system_config',side_effect=RuntimeError('projection')):
            with transaction.atomic():
                obj.value='committed';obj.save()
        obj.refresh_from_db()
        self.assertEqual(obj.value,'committed')

    def test_read_serialization_failure_rolls_back_mark(self):
        from coreadmin.system.views.message_center import MessageCenterSerializer
        msg=MessageCenter.objects.create(title='message',content='text')
        relation=MessageCenterTargetUser.objects.create(users=self.admin,messagecenter=msg)
        with patch.object(MessageCenterSerializer,'to_representation',side_effect=RuntimeError('injected')):
            response=self.client.get(f'/api/system/message_center/{msg.pk}/')
        self.assertEqual(response.status_code,500)
        relation.refresh_from_db()
        self.assertFalse(relation.is_read)

    def test_menu_button_nth_failure_rolls_back(self):
        original=MenuButton.save
        calls=[]
        def fail(obj,*args,**kwargs):
            calls.append(obj)
            if len(calls)==2:raise RuntimeError('injected')
            return original(obj,*args,**kwargs)
        self.menu.component_name='probe';self.menu.save()
        before=MenuButton.objects.count()
        with patch.object(MenuButton,'save',fail):
            response=self.client.post('/api/system/menu_button/batch_create/',{'menu':self.menu.pk},format='json')
        self.assertEqual(response.status_code,500)
        self.assertEqual(MenuButton.objects.count(),before)

    def test_auto_match_nth_failure_rolls_back(self):
        original=MenuField.save
        calls=[]
        def fail(obj,*args,**kwargs):
            calls.append(obj)
            if len(calls)==2:raise RuntimeError('injected')
            return original(obj,*args,**kwargs)
        with patch.object(MenuField,'save',fail):
            response=self.client.post('/api/system/column/auto_match_fields/',{'menu':self.menu.pk,'model':'Users'},format='json')
        self.assertEqual(response.status_code,500)
        self.assertFalse(MenuField.objects.exists())

    def test_menu_sort_second_write_rolls_back(self):
        self.menu.sort=1;self.menu.save()
        self.other.sort=2;self.other.save()
        original=Menu.save
        def fail(obj,*args,**kwargs):
            if obj.pk==self.other.pk:raise RuntimeError('injected')
            return original(obj,*args,**kwargs)
        with patch.object(Menu,'save',fail):
            response=self.client.post('/api/system/menu/move_up/',{'menu_id':self.other.pk},format='json')
        self.assertEqual(response.status_code,500)
        self.menu.refresh_from_db();self.other.refresh_from_db()
        self.assertEqual((self.menu.sort,self.other.sort),(1,2))

    def test_dept_two_step_create_rolls_back(self):
        original=Dept.save
        def fail(obj,*args,**kwargs):
            if obj.pk and obj.name=='newdept':raise RuntimeError('injected')
            return original(obj,*args,**kwargs)
        with patch.object(Dept,'save',fail):
            response=self.client.post('/api/system/dept/',{'name':'newdept'},format='json')
        self.assertEqual(response.status_code,500)
        self.assertFalse(Dept.objects.filter(name='newdept').exists())

    def test_dept_cycle_service_rejects(self):
        child=Dept.objects.create(name='child',parent=self.dept)
        response=self.client.patch(f'/api/system/dept/{self.dept.pk}/',{'parent':child.pk},format='json')
        self.assertEqual(response.status_code,400)
        self.dept.refresh_from_db();self.assertIsNone(self.dept.parent_id)

    def test_generic_update_m2m_rolls_back_scalar(self):
        grant=RoleMenuButtonPermission.objects.create(role=self.role,menu_button=self.button,data_range=4)
        grant.dept.set([self.dept])
        manager=type(grant.dept)
        with patch.object(manager,'set',side_effect=RuntimeError('injected')):
            response=self.client.patch(f'/api/system/role_menu_button_permission/{grant.pk}/',
                {'data_range':3,'dept':[]},format='json')
        self.assertEqual(response.status_code,500)
        grant.refresh_from_db();self.assertEqual(grant.data_range,4)
        self.assertEqual(list(grant.dept.values_list('pk',flat=True)),[self.dept.pk])

    def test_bulk_delete_signal_failure_rolls_back_all(self):
        from django.db.models.signals import post_delete
        a=RoleMenuPermission.objects.create(role=self.role,menu=self.menu)
        b=RoleMenuPermission.objects.create(role=self.role,menu=self.other)
        def fail(sender,instance,**kwargs):
            if instance.pk==a.pk:raise RuntimeError('injected')
        post_delete.connect(fail,sender=RoleMenuPermission,weak=False)
        try:
            response=self.client.delete('/api/system/role_menu_permission/multiple_delete/',{'keys':[a.pk,b.pk]},format='json')
        finally:
            post_delete.disconnect(fail,sender=RoleMenuPermission)
        self.assertEqual(response.status_code,500)
        self.assertEqual(RoleMenuPermission.objects.filter(pk__in=[a.pk,b.pk]).count(),2)

    def test_message_recipients_unique_across_roles(self):
        r=Role.objects.create(name='other',key='other');self.admin.role.add(r,self.role)
        response=self.client.post('/api/system/message_center/',{'title':'unique','content':'text',
            'target_type':1,'target_role':[r.pk,self.role.pk]},format='json')
        self.assertEqual(response.status_code,200)
        self.assertEqual(MessageCenterTargetUser.objects.count(),1)

    def test_duplicate_command_returns_409(self):
        RoleMenuPermission.objects.create(role=self.role,menu=self.menu)
        response=self.client.put('/api/system/role_menu_button_permission/set_role_menu/',
            {'roleId':self.role.pk,'menuId':self.menu.pk,'isCheck':True},format='json')
        self.assertEqual(response.status_code,409)
        self.assertEqual(RoleMenuPermission.objects.count(),1)
