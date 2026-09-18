"""Regression cases from the B2 read-only source audit."""
from django.test import TestCase
from rest_framework.test import APIClient

from coreadmin.foundation_tests.access_fixtures import grant
from coreadmin.system.models import Area, Dept, Users, Role, FieldPermission


class AreaRelationTests(TestCase):
    def setUp(self):
        self.actor = Users.objects.create(username='area-reader', pwd_change_count=1)
        self.admin = Users.objects.create(username='area-admin', is_superuser=True, pwd_change_count=1)
        self.department = Dept.objects.create(name='Parent scope')
        self.parent = Area.objects.create(name='Protected parent', code='parent-code', level=1,
                                          dept_belong_id=self.department.pk)
        self.child = Area.objects.create(name='Visible child', code='child-code', level=2,
                                         pcode=self.parent, creator=self.actor)
        self.client = APIClient()
        self.client.force_authenticate(self.actor)
        grant(self.actor, 'area:Retrieve', 'Area', fields=['name', 'code', 'pcode_info'], scope=0)

    def detail(self):
        response = self.client.get(f'/api/system/area/{self.child.pk}/')
        self.assertEqual(response.status_code, 200)
        return response.json()['data']

    def test_parent_out_of_scope_is_not_exposed(self):
        data = self.detail()
        self.assertEqual(data['name'], self.child.name)
        self.assertEqual(data['pcode_info'], [])
        self.assertNotIn(self.parent.name, str(data))
        self.assertNotIn(self.parent.code, str(data))

    def test_parent_uses_its_own_contributing_fields(self):
        grant(self.actor, 'area:Retrieve', 'Area', fields=['name'], scope=4,
              departments=[self.department])
        self.assertEqual(self.detail()['pcode_info'], [{'name': self.parent.name}])

    def test_authorized_parent_fields_are_preserved(self):
        grant(self.actor, 'area:Retrieve', 'Area', fields=['name', 'code'], scope=4,
              departments=[self.department])
        self.assertEqual(self.detail()['pcode_info'], [{'name': self.parent.name, 'code': self.parent.code}])

    def test_admin_relation_remains_compatible(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.detail()['pcode_info'], [{'name': self.parent.name, 'code': self.parent.code}])

    def test_list_relation_uses_current_action_not_retrieve_grants(self):
        grant(self.actor, 'area:Search', 'Area', fields=['name', 'pcode_info'], scope=0)
        grant(self.actor, 'area:Retrieve', 'Area', fields=['name', 'code'], scope=3)
        response = self.client.get('/api/system/area/', {'name': self.child.name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data'][0]['pcode_info'], [])


class DeptChildFieldTests(TestCase):
    def setUp(self):
        self.actor = Users.objects.create(username='dept-reader', pwd_change_count=1)
        self.parent = Dept.objects.create(name='Parent', creator=self.actor)
        self.child = Dept.objects.create(name='Protected child', parent=self.parent)
        Users.objects.create(username='child-member', dept=self.child, pwd_change_count=1)
        self.parent_grant = grant(self.actor, 'dept:HeaderInfo', 'Dept',
                                  fields=['name', 'sub_dept_map', 'dept_user'], scope=0)
        self.child_grant = grant(self.actor, 'dept:HeaderInfo', 'Dept', scope=4,
                                 departments=[self.child])
        self.client = APIClient()
        self.client.force_authenticate(self.actor)

    def data(self):
        response = self.client.get('/api/system/dept/dept_info/', {'dept_id': self.parent.pk})
        self.assertEqual(response.status_code, 200)
        return response.json()['data']

    def allow_child(self, names):
        from coreadmin.system.models import MenuField
        for name in names:
            field = MenuField.objects.get(menu=self.child_grant.menu_button.menu,
                                          model='Dept', field_name=name)
            FieldPermission.objects.create(role=self.child_grant.role, field=field, is_query=True)

    def test_child_does_not_borrow_parent_fields_or_count(self):
        self.assertEqual(self.data()['sub_dept_map'], [{}])
        self.assertNotIn(self.child.name, str(self.data()))

    def test_child_name_and_count_have_independent_field_permissions(self):
        self.allow_child(['name'])
        self.assertEqual(self.data()['sub_dept_map'], [{'name': self.child.name}])
        self.allow_child(['dept_user'])
        self.assertEqual(self.data()['sub_dept_map'], [{'name': self.child.name, 'count': 1}])

    def test_role_order_does_not_change_child_projection(self):
        self.allow_child(['name'])
        before = self.data()
        Role.objects.filter(pk=self.parent_grant.role_id).update(sort=99)
        Role.objects.filter(pk=self.child_grant.role_id).update(sort=-1)
        self.assertEqual(self.data(), before)

    def test_admin_child_output_remains_available(self):
        admin = Users.objects.create(username='dept-admin', is_superuser=True, pwd_change_count=1)
        self.client.force_authenticate(admin)
        self.assertEqual(self.data()['sub_dept_map'], [{'name': self.child.name, 'count': 1}])


class SystemConfigQueryTests(TestCase):
    def setUp(self):
        from coreadmin.system.models import SystemConfig
        self.admin = Users.objects.create(username='config-admin', is_superuser=True, pwd_change_count=1)
        self.normal = Users.objects.create(username='config-reader', pwd_change_count=1)
        self.root = SystemConfig.objects.create(title='Root', key='root')
        self.child = SystemConfig.objects.create(title='Child', key='child', parent=self.root)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_admin_parent_isnull_true_and_false(self):
        for value, expected in [('true', self.root.pk), ('false', self.child.pk)]:
            with self.subTest(value=value):
                response = self.client.get('/api/system/system_config/', {'parent__isnull': value})
                self.assertEqual(response.status_code, 200)
                self.assertEqual([row['id'] for row in response.json()['data']], [expected])

    def test_lookup_still_requires_underlying_field_read_permission(self):
        grant(self.normal, 'system_config:Search', 'SystemConfig', fields=['title'])
        self.client.force_authenticate(self.normal)
        url = '/api/system/system_config/'
        self.assertEqual(self.client.get(url, {'parent__isnull': 'true'}).status_code, 400)
        grant(self.normal, 'system_config:Search', 'SystemConfig', fields=['parent'])
        # Query fields are deliberately intersected across grant tuples.
        from coreadmin.system.models import MenuField
        field = MenuField.objects.get(model='SystemConfig', field_name='parent')
        for role in self.normal.role.all():
            FieldPermission.objects.update_or_create(role=role, field=field, defaults={'is_query': True})
        self.assertEqual(self.client.get(url, {'parent__isnull': 'true'}).status_code, 200)

    def test_unregistered_lookups_and_invalid_boolean_are_denied(self):
        for query in [{'secret__icontains': 'x'}, {'creator__password': 'x'},
                      {'arbitrary_relation__field': 'x'}, {'unknown__lookup': 'x'},
                      {'parent__name': 'Root'}, {'parent__isnull': 'invalid'}]:
            with self.subTest(query=query):
                self.assertEqual(self.client.get('/api/system/system_config/', query).status_code, 400)

    def test_dynamic_lookup_remains_shutdown(self):
        self.assertEqual(self.client.get(f'/api/system/system_config/get_table_data/{self.root.pk}/').status_code, 405)


class AreaDerivedWriteTests(TestCase):
    def setUp(self):
        self.actor = Users.objects.create(username='area-writer', pwd_change_count=1)
        self.parent = Area.objects.create(name='Parent', code='parent-not-pk', level=2, creator=self.actor)
        self.area = Area.objects.create(name='Before', code='before-code', level=3,
                                        pinyin='before', initials='B', pcode=self.parent, creator=self.actor)
        self.client = APIClient()
        self.client.force_authenticate(self.actor)
        for alias, mode in [('area:Create', 'create'), ('area:Update', 'update')]:
            grant(self.actor, alias, 'Area', fields=['name', 'code', 'pcode', 'level', 'pinyin', 'initials'],
                  scope=0, **{mode: ['name', 'code', 'pcode']})

    def test_create_derives_values_without_dynamic_write_permission(self):
        response = self.client.post('/api/system/area/', {'name': '北京', 'code': 'new-code', 'pcode': self.parent.pk}, format='json')
        self.assertEqual(response.status_code, 200)
        row = Area.objects.get(code='new-code')
        self.assertEqual(response.json()['data']['pcode'], self.parent.code)
        self.assertEqual((row.level, row.pinyin, row.initials), (3, 'beijing', 'B'))
        self.assertEqual(row.pcode_id, self.parent.code)
        self.assertEqual(row.creator_id, self.actor.pk)

    def test_update_and_patch_derive_values_without_dynamic_write_permission(self):
        url = f'/api/system/area/{self.area.pk}/'
        response = self.client.put(url, {'name': '上海', 'code': self.area.code, 'pcode': self.parent.pk}, format='json')
        self.assertEqual(response.status_code, 200)
        self.area.refresh_from_db()
        self.assertEqual((self.area.level, self.area.pinyin, self.area.initials), (3, 'shanghai', 'S'))
        self.assertEqual(self.client.patch(url, {'name': '北京'}, format='json').status_code, 200)
        self.area.refresh_from_db()
        self.assertEqual((self.area.level, self.area.pinyin, self.area.initials), (3, 'beijing', 'B'))
        self.assertEqual(self.client.patch(url, {'pcode': None}, format='json').status_code, 200)
        self.area.refresh_from_db()
        self.assertEqual(self.area.level, 1)

    def test_client_derived_or_other_unapproved_fields_rejected_without_writes(self):
        before = list(Area.objects.order_by('pk').values())
        for method, url in [('post', '/api/system/area/'), ('put', f'/api/system/area/{self.area.pk}/'),
                            ('patch', f'/api/system/area/{self.area.pk}/')]:
            for key, value in [('level', 99), ('pinyin', 'forged'), ('initials', 'X'),
                               ('description', 'not granted'), ('creator', self.actor.pk)]:
                with self.subTest(method=method, key=key):
                    response = getattr(self.client, method)(url, {'name': '北京', 'code': 'attempt', key: value}, format='json')
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(list(Area.objects.order_by('pk').values()), before)

    def test_dynamic_grants_cannot_expand_derived_field_ceiling(self):
        grant(self.actor, 'area:Create', 'Area', scope=0, create=['level', 'pinyin', 'initials'])
        self.assertEqual(self.client.post('/api/system/area/', {'name': '北京', 'code': 'forged', 'level': 9}, format='json').status_code, 400)
        admin = Users.objects.create(username='area-write-admin', is_superuser=True, pwd_change_count=1)
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.patch(f'/api/system/area/{self.area.pk}/', {'level': 9}, format='json').status_code, 400)


class MessageClosureTests(TestCase):
    def setUp(self):
        from coreadmin.system.models import MessageCenter, MessageCenterTargetUser
        from coreadmin.system.services.auth import AuthService
        self.recipient = Users.objects.create(username='message-recipient', pwd_change_count=1)
        self.sender = Users.objects.create(username='message-sender', pwd_change_count=1)
        self.other = Users.objects.create(username='message-other', pwd_change_count=1)
        self.content = '<script>window.__B2_FIX__=1</script>\n<b>Plain message</b>'
        self.own = MessageCenter.objects.create(title='Own', content=self.content, creator=self.sender)
        self.relation = MessageCenterTargetUser.objects.create(messagecenter=self.own, users=self.recipient, is_read=False)
        self.other_message = MessageCenter.objects.create(title='Other only', content='Other content', creator=self.sender)
        MessageCenterTargetUser.objects.create(messagecenter=self.other_message, users=self.other, is_read=False)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION='JWT ' + AuthService.issue(self.recipient)['access'])

    def snapshot(self):
        from coreadmin.system.models import MessageCenter, MessageCenterTargetUser
        return (list(MessageCenter.objects.order_by('pk').values()),
                list(MessageCenterTargetUser.objects.order_by('pk').values()))

    def test_existing_unread_relation_outside_action_scope_is_not_marked(self):
        # Action is granted, relation exists, but SELF excludes sender's row.
        grant(self.recipient, 'messageCenter:Retrieve', 'MessageCenter', fields=['title', 'content'], scope=0)
        before = self.snapshot()
        response = self.client.get(f'/api/system/message_center/{self.own.pk}/')
        self.assertEqual(response.status_code, 404)
        self.relation.refresh_from_db()
        self.assertFalse(self.relation.is_read)
        self.assertEqual(self.snapshot(), before)

    def test_normal_mutations_denied_and_all_message_rows_unchanged(self):
        # Even legacy mutation grants and a recipient relationship cannot
        # delegate the FIXED_SUPERUSER actions.
        for alias in ['messageCenter:Create', 'messageCenter:Update', 'messageCenter:Delete']:
            grant(self.recipient, alias, 'MessageCenter', scope=3,
                  create=['title', 'content'], update=['title', 'content'])
        before = self.snapshot()
        for method, url in [('post', '/api/system/message_center/'),
                            ('put', f'/api/system/message_center/{self.own.pk}/'),
                            ('patch', f'/api/system/message_center/{self.own.pk}/'),
                            ('delete', f'/api/system/message_center/{self.own.pk}/')]:
            with self.subTest(method=method):
                response = getattr(self.client, method)(url, {'title': 'Forged', 'content': 'Changed'}, format='json')
                self.assertEqual(response.status_code, 403)
                self.assertEqual(self.snapshot(), before)

    def test_real_jwt_recipient_full_plain_text_positive_flow(self):
        grant(self.recipient, 'messageCenter:Retrieve', 'MessageCenter', fields=['title', 'content'], scope=3)
        receive = '/api/system/message_center/get_self_receive/'
        response = self.client.get(receive)
        self.assertEqual(response.status_code, 200)
        rows = {row['id']: row for row in response.json()['data']}
        self.assertEqual(set(rows), {self.own.pk})
        self.assertEqual(rows[self.own.pk]['content'], self.content)
        self.assertFalse(rows[self.own.pk]['is_read'])
        newest = self.client.get('/api/system/message_center/get_newest_msg/')
        self.assertEqual(newest.status_code, 200)
        self.assertEqual(newest.json()['data']['id'], self.own.pk)
        self.assertEqual(newest.json()['data']['content'], self.content)
        self.assertFalse(newest.json()['data']['is_read'])
        detail = self.client.get(f'/api/system/message_center/{self.own.pk}/')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()['data']['content'], self.content)
        self.relation.refresh_from_db()
        self.assertTrue(self.relation.is_read)
        again = self.client.get(receive)
        self.assertEqual(again.status_code, 200)
        rows = {row['id']: row for row in again.json()['data']}
        self.assertEqual(set(rows), {self.own.pk})
        self.assertTrue(rows[self.own.pk]['is_read'])
        self.own.refresh_from_db()
        self.assertEqual(self.own.content, self.content)
        self.other_message.refresh_from_db()
        self.assertEqual(self.other_message.content, 'Other content')
        self.recipient.refresh_from_db()
        self.assertTrue(self.recipient.is_active)
        self.assertFalse(self.recipient.is_superuser)
