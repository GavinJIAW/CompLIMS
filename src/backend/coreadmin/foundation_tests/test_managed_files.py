"""B5 private-file contracts on disposable PostgreSQL and temporary storage."""
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase, override_settings
from coreadmin.system.models import ManagedFile, Users
from coreadmin.system.services import managed_files as service


class StorageTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.public = tempfile.TemporaryDirectory()
        self.addCleanup(self.public.cleanup)
        self.settings_override = override_settings(MANAGED_FILE_ROOT=self.temp.name,
            MEDIA_ROOT=self.public.name, MANAGED_FILE_MAX_SIZE_BYTES=8)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.user = Users.objects.create(username='file-owner', pwd_change_count=1)

    def put(self, content=b'example', name='sample.dat'):
        return service.upload(SimpleUploadedFile(name, content), self.user)

    def files(self):
        return list((Path(self.temp.name) / 'managed').glob('*'))

    def test_streamed_hash_size_and_random_key(self):
        obj = self.put()
        self.assertEqual(obj.size, 7)
        self.assertEqual(obj.sha256, hashlib.sha256(b'example').hexdigest())
        self.assertRegex(obj.storage_key, r'^managed/[0-9a-f]{32}$')
        self.assertEqual((Path(self.temp.name) / obj.storage_key).read_bytes(), b'example')
        self.assertEqual(obj.uploader_id, self.user.pk)

    def test_zero_and_limit(self):
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError): self.put(b'')
        self.assertEqual(self.put(b'12345678').size, 8)
        with self.assertRaises(service.FileTooLarge): self.put(b'123456789')
        self.assertEqual(ManagedFile.objects.count(), 1)
        self.assertEqual(len(self.files()), 1)

    def test_no_declared_size_uses_chunks(self):
        class Stream:
            name = 'machine.raw'
            content_type = None
            def chunks(self):
                yield b'1234'
                yield b'56789'
        with self.assertRaises(service.FileTooLarge): service.upload(Stream(), self.user)
        self.assertFalse(ManagedFile.objects.exists())
        self.assertFalse(self.files())

    def test_same_name_and_content_never_overwrite(self):
        a,b,c = self.put(b'first'),self.put(b'second'),self.put(b'first')
        self.assertEqual(len({x.pk for x in [a,b,c]}), 3)
        self.assertEqual(len({x.storage_key for x in [a,b,c]}), 3)
        self.assertEqual((Path(self.temp.name) / a.storage_key).read_bytes(), b'first')

    def test_database_failure_removes_only_new_file(self):
        old = self.put()
        with patch.object(ManagedFile.objects, 'create', side_effect=IntegrityError('test failure')):
            with self.assertRaises(IntegrityError): self.put(b'new')
        self.assertEqual(ManagedFile.objects.count(), 1)
        self.assertEqual(self.files(), [Path(self.temp.name) / old.storage_key])

    def test_storage_failure_has_no_row_and_cleans_partial(self):
        class Broken:
            name = 'broken.dat'
            def chunks(self):
                yield b'part'
                raise OSError('simulated disk failure')
        with self.assertRaises(OSError): service.upload(Broken(), self.user)
        self.assertFalse(ManagedFile.objects.exists())
        self.assertFalse(self.files())

    def test_collision_preserves_existing_bytes(self):
        old = self.put()
        with patch.object(service.uuid, 'uuid4') as uid:
            uid.return_value.hex = old.storage_key.split('/')[1]
            with self.assertRaises(FileExistsError): self.put(b'new')
        self.assertEqual((Path(self.temp.name) / old.storage_key).read_bytes(), b'example')
        self.assertEqual(ManagedFile.objects.count(), 1)

    def test_private_root_cannot_be_media(self):
        from django.core.exceptions import ImproperlyConfigured
        for root in [self.temp.name, str(Path(self.temp.name) / 'child'), str(Path(self.temp.name).parent)]:
            with override_settings(MEDIA_ROOT=self.temp.name, MANAGED_FILE_ROOT=root):
                with self.assertRaises(ImproperlyConfigured): self.put()

    def test_bad_names(self):
        from rest_framework.exceptions import ValidationError
        for name in ['', '.', '..', '../x', 'a/b', 'a\\b', 'C:\\x', '/x', 'x\x00y']:
            with self.subTest(name=name), self.assertRaises(ValidationError): service.validate_name(name)


from rest_framework.test import APIClient
from django.test import TransactionTestCase
from coreadmin.system.models import OperationLog, FileList, DownloadCenter


class APITests(TestCase):
    url = '/api/system/managed_file/'

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.public = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.public.cleanup)
        override = override_settings(MANAGED_FILE_ROOT=self.temp.name, MEDIA_ROOT=self.public.name,
            MANAGED_FILE_MAX_SIZE_BYTES=8)
        override.enable(); self.addCleanup(override.disable)
        self.owner = Users.objects.create(username='owner', pwd_change_count=1)
        self.other = Users.objects.create(username='other', pwd_change_count=1)
        self.admin = Users.objects.create(username='admin', is_superuser=True, pwd_change_count=1)
        self.client = APIClient(); self.client.force_authenticate(self.owner)

    def post(self, data=b'example', name='sample.raw', **extra):
        return self.client.post(self.url, {'file': SimpleUploadedFile(name, data), **extra}, format='multipart')

    def upload(self):
        response = self.post()
        self.assertEqual(response.status_code, 200, response.data)
        return ManagedFile.objects.get(pk=response.data['data']['id'])

    def test_normal_upload_and_fixed_metadata(self):
        response = self.post()
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data['data']
        self.assertEqual(set(data), {'id','original_name','size','sha256','content_type','uploader','created_at'})
        self.assertEqual(data['original_name'], 'sample.raw')
        self.assertEqual(data['size'], 7)
        self.assertEqual(data['sha256'], hashlib.sha256(b'example').hexdigest())
        self.assertEqual(data['uploader'], self.owner.pk)

    def test_superuser_upload(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.upload().uploader_id, self.admin.pk)

    def test_anonymous_and_inactive_denied(self):
        for actor in [None, self.other]:
            if actor:
                actor.is_active=False;actor.save(update_fields=['is_active'])
            self.client.force_authenticate(actor)
            self.assertIn(self.post().status_code, [401,403])
            self.assertIn(self.client.get(self.url).status_code, [401,403])
        self.assertFalse(ManagedFile.objects.exists())

    def test_missing_file_and_client_metadata_rejected(self):
        self.assertEqual(self.client.post(self.url, {}, format='multipart').status_code,400)
        for field in ['id','storage_key','uploader','sha256','size','content_type','created_at']:
            self.assertEqual(self.post(**{field:'client-value'}).status_code,400,field)
        self.assertFalse(ManagedFile.objects.exists())

    def test_empty_max_and_over(self):
        self.assertEqual(self.post(b'').status_code,400)
        self.assertEqual(self.post(b'12345678').status_code,200)
        self.assertEqual(self.post(b'123456789').status_code,413)
        self.assertEqual(ManagedFile.objects.count(),1)

    def test_raw_multipart_path_names_rejected_before_sanitization(self):
        for name in ['../x', 'a/b', 'a\\b', 'C:\\x', '/absolute', 'a\x00b']:
            body = ('--boundary\r\nContent-Disposition: form-data; name="file"; filename="'+name+
                '"\r\nContent-Type: application/octet-stream\r\n\r\nx\r\n--boundary--\r\n').encode()
            r=self.client.generic('POST',self.url,body,content_type='multipart/form-data; boundary=boundary')
            self.assertEqual(r.status_code,400,name)
        self.assertFalse(ManagedFile.objects.exists())

    def test_owner_and_cross_user_metadata_download_scope(self):
        obj=self.upload()
        detail=self.url+str(obj.pk)+'/'
        self.assertEqual(self.client.get(detail).status_code,200)
        self.assertEqual(self.client.get(self.url).data['data'][0]['id'],obj.pk)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(self.url).data['data'],[])
        self.assertEqual(self.client.get(detail).status_code,404)
        with patch.object(Path,'open', side_effect=AssertionError('unauthorized file open')):
            self.assertEqual(self.client.get(detail+'download/').status_code,404)
        for actor in [self.owner,self.admin]:
            self.client.force_authenticate(actor)
            self.assertEqual(self.client.get(detail).status_code,200)
            response=self.client.get(detail+'download/')
            self.assertEqual(response.status_code,200)
            self.assertIn('attachment;',response['Content-Disposition'])
            self.assertEqual(b''.join(response.streaming_content),b'example')

    def test_missing_record_and_missing_backing_file(self):
        self.assertEqual(self.client.get(self.url+'99999/').status_code,404)
        self.assertEqual(self.client.get(self.url+'99999/download/').status_code,404)
        obj=self.upload();(Path(self.temp.name)/obj.storage_key).unlink()
        self.assertEqual(self.client.get(self.url+str(obj.pk)+'/download/').status_code,404)

    def test_mutations_disabled(self):
        obj=self.upload()
        for actor in [self.owner,self.admin]:
            self.client.force_authenticate(actor)
            for method in ['put','patch','delete']:
                self.assertEqual(getattr(self.client,method)(self.url+str(obj.pk)+'/',{},format='json').status_code,405)
            self.assertEqual(self.client.delete(self.url+'multiple_delete/',{'keys':[obj.pk]},format='json').status_code,405)
        self.assertEqual((Path(self.temp.name)/obj.storage_key).read_bytes(),b'example')

    def test_private_file_not_in_media_even_with_debug_serving(self):
        from django.views.static import serve
        from django.test import RequestFactory
        from django.http import Http404
        obj=self.upload()
        self.assertFalse((Path(self.public.name)/obj.storage_key).exists())
        with self.assertRaises(Http404):
            serve(RequestFactory().get('/media/'+obj.storage_key),obj.storage_key,document_root=self.public.name)
        self.assertEqual(self.client.get('/media/'+obj.storage_key).status_code,404)

    @override_settings(API_LOG_ENABLE=True, API_LOG_METHODS=['POST'])
    def test_upload_operational_target(self):
        import json
        obj=self.upload()
        log=OperationLog.objects.latest('id')
        self.assertEqual(log.creator_id,self.owner.pk)
        self.assertTrue(log.status)
        self.assertEqual(json.loads(log.request_target),{'managedfile':[obj.pk]})

    def test_must_change_gate_not_bypassed(self):
        self.owner.pwd_change_count=0;self.owner.save(update_fields=['pwd_change_count'])
        self.assertEqual(self.post().status_code,403)
        self.assertEqual(self.client.get(self.url).status_code,403)

    def test_legacy_shutdown(self):
        self.client.force_authenticate(self.admin)
        old=FileList.objects.create(name='legacy',url='old/file.dat',file_url='media/old/file.dat',size='3',md5sum='legacy')
        for base,pk in [('/api/system/file/',old.pk),('/api/system/download_center/',1)]:
            self.assertEqual(self.client.post(base,{},format='json').status_code,405)
            for method in ['put','patch','delete']:
                self.assertEqual(getattr(self.client,method)(base+str(pk)+'/',{},format='json').status_code,405)
            self.assertEqual(self.client.delete(base+'multiple_delete/',{},format='json').status_code,405)
        self.assertEqual(self.client.get('/api/system/file/').status_code,200)
        self.assertEqual(self.client.get('/api/system/file/'+str(old.pk)+'/').status_code,200)
        for resource in ['user','dept']:
            self.assertEqual(self.client.post('/api/system/'+resource+'/import_data/',{},format='json').status_code,405)
        old.refresh_from_db();self.assertEqual(old.file_url,'media/old/file.dat')


class LengthlessUploadTests(TestCase):
    setUp = APITests.setUp
    url = APITests.url
    # Exercise the actual view with a server-provided ASGI body stream and no
    # Content-Length, rather than merely deleting a header on a WSGI test client.
    def test_lengthless_asgi_stream_limit(self):
        from io import BytesIO
        from django.core.handlers.asgi import ASGIRequest
        from rest_framework.test import force_authenticate
        from coreadmin.system.views.managed_file import ManagedFileViewSet
        for content, status in [(b'12345678',200),(b'123456789',413)]:
            body=(b'--bound\r\nContent-Disposition: form-data; name="file"; filename="machine.raw"\r\n'
                  b'Content-Type: application/octet-stream\r\n\r\n'+content+b'\r\n--bound--\r\n')
            request=ASGIRequest({'type':'http','method':'POST','path':self.url,'query_string':b'',
                'headers':[(b'content-type',b'multipart/form-data; boundary=bound')],
                'server':('testserver',80),'client':('127.0.0.1',1234)},BytesIO(body))
            self.assertNotIn('CONTENT_LENGTH',request.META)
            force_authenticate(request,self.owner)
            response=ManagedFileViewSet.as_view({'post':'create'})(request)
            self.assertEqual(response.status_code,status,getattr(response,'data',None))
            request.close()
        self.assertEqual(ManagedFile.objects.count(),1)


class MigrationTests(TransactionTestCase):
    def test_b4_upgrade_preserves_all_existing_data(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        old=[('system','0003_operationlog_request_target')]
        executor=MigrationExecutor(connection)
        latest=executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(old)
            registry=executor.loader.project_state(old).apps
            registry.get_model('system','Users').objects.create(username='historical-file-owner')
            registry.get_model('system','FileList').objects.create(name='historical',url='legacy.dat',
                file_url='media/legacy.dat',size='3',md5sum='legacy')
            registry.get_model('system','Role').objects.create(name='preserved',key='preserved')
            registry.get_model('system','SystemConfig').objects.create(title='preserved',key='preserved',value='value')
            def snapshot(registry, labels):
                return {label:list(registry.get_model(label).objects.order_by('pk').values()) for label in labels}
            labels=[m._meta.label for m in registry.get_app_config('system').get_models(include_auto_created=True)]
            before=snapshot(registry,labels)
            MigrationExecutor(connection).migrate(latest)
            current=MigrationExecutor(connection).loader.project_state(latest).apps
            self.assertEqual(before,snapshot(current,labels))
            self.assertFalse(ManagedFile.objects.exists())
            with connection.cursor() as cursor:
                cursor.execute('SELECT contype FROM pg_constraint WHERE conrelid=%s::regclass',[ManagedFile._meta.db_table])
                kinds=[row[0] for row in cursor.fetchall()]
                for kind in ['p','u','f','c']: self.assertIn(kind,kinds)
        finally:
            MigrationExecutor(connection).migrate(latest)


class ConstraintTests(TestCase):
    def test_required_fk_unique_key_and_positive_size(self):
        from django.db import connection, transaction
        from django.db.models.deletion import ProtectedError
        user=Users.objects.create(username='constraint-owner')
        fields=dict(original_name='file',storage_key='managed/'+'a'*32,size=1,
            sha256='b'*64,content_type='application/octet-stream',uploader=user)
        obj=ManagedFile.objects.create(**fields)
        for changes in [{'storage_key':obj.storage_key}, {'storage_key':'managed/'+'c'*32,'size':0},
                        {'storage_key':'managed/'+'d'*32,'uploader_id':999999}]:
            values={**fields,**changes}
            if 'uploader_id' in changes: values.pop('uploader')
            with self.assertRaises(IntegrityError),transaction.atomic():
                ManagedFile.objects.create(**values)
                connection.check_constraints()
        with self.assertRaises(ProtectedError): user.delete()
