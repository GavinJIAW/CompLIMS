"""Operational log boundaries through real Django/DRF middleware paths."""
import copy
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.test import TestCase, SimpleTestCase, RequestFactory, override_settings
from django.urls import path, include
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from coreadmin.system.models import OperationLog, LoginLog, Users, Role, ApiWhiteList
from coreadmin.system.views.role import RoleViewSet
from coreadmin.utils.middleware import ApiLoggingMiddleware
from coreadmin.utils.request_util import save_login_log
from coreadmin.foundation_tests.test_grant_management import database_snapshot


class EchoView(APIView):
    permission_classes = []

    def post(self, request):
        return Response({'code': 2000, 'msg': 'done', 'data': request.data}, headers={'X-B1D': 'original'})

    patch = post


class BrokenView(APIView):
    permission_classes = []

    def post(self, request):
        raise RuntimeError('B1D_SECRET_SENTINEL')


urlpatterns = [path('b1d/echo/', EchoView.as_view()), path('b1d/broken/', BrokenView.as_view()),
               path('', include('application.urls'))]


@override_settings(API_LOG_ENABLE=True, API_LOG_METHODS='ALL', ROOT_URLCONF=__name__)
class MiddlewareTrustTests(TestCase):
    def setUp(self):
        self.user = Users.objects.create(username='b1d-user', password='!')
        self.admin = Users.objects.create(username='b1d-admin', password='!', is_superuser=True)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def request(self, payload=None):
        request = RequestFactory().post('/b1d/echo/', payload or {}, content_type='application/json')
        request.user = self.user
        request.session = {}
        return request

    def test_process_view_has_no_insert_and_does_not_inject_id(self):
        middleware = ApiLoggingMiddleware(lambda request: HttpResponse())
        request = self.request({'name': 'original'})
        middleware.process_request(request)
        with patch.object(OperationLog.objects, 'create') as create, patch.object(OperationLog.objects, 'update_or_create') as update, patch.object(OperationLog, 'save') as save:
            middleware.process_view(request, RoleViewSet.as_view({'post': 'create'}), (), {})
            create.assert_not_called()
            update.assert_not_called()
            save.assert_not_called()
        self.assertEqual(OperationLog.objects.count(), 0)
        self.assertNotIn('log_id', getattr(request, 'request_data', {}))

    def test_client_id_cannot_overwrite_history_request_values_survive(self):
        old = OperationLog.objects.create(request_body='historical', request_path='/old/')
        before = OperationLog.objects.filter(pk=old.pk).values().get()
        payload = {'log_id': old.pk, 'password': 'CLIENT_SECRET', 'nested': {'access_token': 'TOKEN_SENTINEL', 'items': [{'clientSecret': 'SECRET_SENTINEL'}]}, 'name': 'visible'}
        response = self.client.post('/b1d/echo/', payload, format='json', HTTP_USER_AGENT='B1D test')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['data'] == payload, 'Business payload was altered')
        self.assertEqual(response['X-B1D'], 'original')
        self.assertTrue(before == OperationLog.objects.filter(pk=old.pk).values().get(), 'Historical log overwritten')
        self.assertEqual(OperationLog.objects.count(), 2)
        row = OperationLog.objects.exclude(pk=old.pk).get()
        for secret in ('CLIENT_SECRET', 'TOKEN_SENTINEL', 'SECRET_SENTINEL'):
            self.assertTrue(secret not in row.request_body)
        self.assertIn('[REDACTED]', row.request_body)
        self.assertTrue(row.status)

    def test_query_redaction(self):
        response = self.client.get('/api/system/dept/dept_info/?access_token=QUERY_SECRET&name=visible&dept_id=')
        self.assertEqual(response.status_code, 200)
        body = OperationLog.objects.get().request_body
        self.assertTrue('QUERY_SECRET' not in body)
        self.assertIn('visible', body)

    def test_patch_final_log(self):
        response = self.client.patch('/b1d/echo/', {'newPassword': 'TEST_SECRET'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(OperationLog.objects.count(), 1)
        self.assertTrue('TEST_SECRET' not in OperationLog.objects.get().request_body)

    def test_persistence_failure_preserves_business_response(self):
        with patch.object(OperationLog.objects, 'create', side_effect=RuntimeError('LOG_DB_FAILURE')) as create, patch('coreadmin.utils.middleware.logger') as logger:
            response = self.client.post('/b1d/echo/', {'name': 'safe'}, format='json')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, {'code': 2000, 'msg': 'done', 'data': {'name': 'safe'}})
            self.assertEqual(response['X-B1D'], 'original')
            create.assert_called_once()
            logger.exception.assert_called_once()

    def test_request_and_response_are_not_mutated_or_stream_consumed(self):
        responses = [HttpResponse(b'original', headers={'X-Test': 'yes'}), JsonResponse({'msg': {'accessToken': 'SENTINEL'}}), Response({'code': 2000, 'msg': {'password': 'SENTINEL'}}), HttpResponse(b'\x00\xff', content_type='application/octet-stream')]
        for response in responses:
            with self.subTest(response=type(response).__name__):
                middleware = ApiLoggingMiddleware(lambda request: response)
                request = self.request()
                request.request_data = {'password': 'ORIGINAL', 'log_id': 987, 'nested': {'token': 'ORIGINAL'}}
                original = copy.deepcopy(request.request_data)
                before = (response.status_code, dict(response.headers), copy.deepcopy(getattr(response, 'data', None)), hasattr(response, 'data'))
                content = response.content if not isinstance(response, Response) else None
                middleware.process_request(request)
                returned = middleware.process_response(request, response)
                self.assertIs(returned, response)
                self.assertTrue(request.request_data == original)
                self.assertEqual(before, (response.status_code, dict(response.headers), getattr(response, 'data', None), hasattr(response, 'data')))
                if content is not None:
                    self.assertEqual(response.content, content)
        consumed = []
        def stream():
            consumed.append(True)
            yield b'body'
        response = StreamingHttpResponse(stream())
        request = self.request()
        middleware.process_request(request)
        self.assertIs(middleware.process_response(request, response), response)
        self.assertFalse(consumed)

    def test_denied_mutations_only_add_final_operational_log(self):
        role = Role.objects.create(name='Target', key='b1d-target')
        for actor, url, payload, status in ((self.user, f'/api/system/role/{role.pk}/', {'name': 'attack'}, 403), (self.admin, '/api/system/dept/multiple_delete/', {'keys': [1]}, 405)):
            with self.subTest(status=status):
                self.client.force_authenticate(actor)
                before = database_snapshot()
                response = self.client.delete(url, payload, format='json')
                after = database_snapshot()
                self.assertEqual(response.status_code, status)
                label = OperationLog._meta.label
                self.assertEqual(len(after.pop(label)), len(before.pop(label)) + 1)
                self.assertTrue(before == after, 'Denied mutation altered business/M2M state')
                log = OperationLog.objects.latest('id')
                self.assertFalse(log.status)
                self.assertTrue(log.request_path)

    def test_generic_exception_is_generic_500_and_log_is_safe(self):
        with patch('coreadmin.utils.exception.logger') as logger:
            response = self.client.post('/b1d/broken/', {}, format='json')
            self.assertEqual(response.status_code, 500)
            self.assertEqual(set(response.data), {'code', 'msg', 'data'})
            self.assertEqual(response.data['msg'], '接口服务器异常，请联系管理员')
            self.assertTrue('B1D_SECRET_SENTINEL' not in response.content.decode())
            logger.exception.assert_called_once()
        log = OperationLog.objects.get()
        self.assertFalse(log.status)
        self.assertTrue('B1D_SECRET_SENTINEL' not in log.json_result)

    def test_http_status_takes_precedence_over_success_code(self):
        middleware = ApiLoggingMiddleware(lambda request: HttpResponse())
        for status, data, expected in ((403, {'code': 2000}, False), (200, {'code': 4000}, False), (201, {}, True), (302, {}, True)):
            request = self.request()
            middleware.process_request(request)
            middleware.process_response(request, Response(data, status=status))
            self.assertEqual(OperationLog.objects.latest('id').status, expected)

    def test_duplicate_response_hook_does_not_repeat_or_retry_insert(self):
        middleware = ApiLoggingMiddleware(lambda request: HttpResponse())
        request = self.request()
        middleware.process_request(request)
        response = HttpResponse('done')
        middleware.process_response(request, response)
        middleware.process_response(request, response)
        self.assertEqual(OperationLog.objects.count(), 1)
        request = self.request()
        with patch.object(OperationLog.objects, 'create', side_effect=RuntimeError('TEST LOG FAILURE')) as create, patch('coreadmin.utils.middleware.logger'):
            middleware.process_response(request, response)
            middleware.process_response(request, response)
            create.assert_called_once()

    def test_persisted_payload_bounds_and_minimal_response_summary(self):
        from coreadmin.utils.log_sanitization import MAX_LOG_SERIALIZED_SIZE
        values = ({'long': 'x' * 3000}, {'items': list(range(100))},
                  {str(i): 'y' * 2048 for i in range(50)})
        for payload in values:
            response = self.client.post('/b1d/echo/', payload, format='json')
            self.assertEqual(response.status_code, 200)
            log = OperationLog.objects.latest('id')
            self.assertLessEqual(len(log.request_body.encode('utf-8')), MAX_LOG_SERIALIZED_SIZE)
            self.assertIn('[TRUNCATED]', log.request_body)
            self.assertEqual(set(json.loads(log.json_result)), {'code', 'msg', 'http_status'})

    def test_no_user_agent_still_creates_one_final_log(self):
        response = self.client.post('/b1d/echo/', {'safe': 'value'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(OperationLog.objects.count(), 1)

    def test_response_summary_and_request_msg_are_recursively_redacted(self):
        middleware = ApiLoggingMiddleware(lambda request: HttpResponse())
        request = self.request()
        request.session = {'request_msg': {'credential': 'REQUEST_MSG_SECRET'}}
        middleware.process_request(request)
        middleware.process_response(request, Response({'code': 2000, 'msg': {'refreshToken': 'RESPONSE_MSG_SECRET'}, 'data': 'DO_NOT_COLLECT'}))
        row = OperationLog.objects.get()
        self.assertTrue('REQUEST_MSG_SECRET' not in row.request_msg)
        self.assertTrue('RESPONSE_MSG_SECRET' not in row.json_result)
        self.assertTrue('DO_NOT_COLLECT' not in row.json_result)
        self.assertIn('[REDACTED]', row.request_msg)
        self.assertIn('[REDACTED]', row.json_result)

    def test_multipart_is_not_parsed_before_permission(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_authenticate(self.admin)
        with patch('django.core.files.uploadhandler.TemporaryFileUploadHandler.new_file', side_effect=AssertionError('Upload parser entered')) as upload:
            response = self.client.post('/api/system/file/', {'file': SimpleUploadedFile('test.txt', b'test')}, format='multipart')
            self.assertEqual(response.status_code, 405)
            upload.assert_not_called()
        self.assertEqual(OperationLog.objects.count(), 1)


class LogAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.normal = Users.objects.create(username='log-normal', password='!')
        cls.inactive = Users.objects.create(username='log-inactive', password='!', is_superuser=True, is_active=False)
        cls.admin = Users.objects.create(username='log-admin', password='!', is_superuser=True)
        cls.operation_log = OperationLog.objects.create(request_path='/historical/')
        cls.login_log = LoginLog.objects.create(username='historical')
        for method in (0, 1, 2, 3, 5):
            ApiWhiteList.objects.create(url='/api/system/.*', method=method, enable_datasource=False)

    def test_internal_writes_and_missing_user_agent(self):
        before = LoginLog.objects.count()
        request = RequestFactory().post('/login/')
        request.user = self.admin
        save_login_log(request)
        self.assertEqual(LoginLog.objects.count(), before + 1)
        self.assertEqual(LoginLog.objects.latest('id').creator_id, self.admin.pk)
        OperationLog.objects.create(request_path='/server/')
        self.assertEqual(OperationLog.objects.count(), 2)

    def test_field_permission_legacy_action_is_closed(self):
        client = APIClient()
        client.force_authenticate(self.admin)
        self.assertEqual(client.get('/api/system/login_log/field_permission/').status_code, 405)

    def test_history_redacted_and_bounded_without_database_rewrite(self):
        # TextFields historically received both Python repr and JSON strings.
        values = {'password': 'OLD_PASSWORD_SECRET', 'nested': {'access_token': 'OLD_ACCESS_TOKEN', 'clientSecret': 'OLD_CLIENT_SECRET'}, 'long': 'x' * 10000}
        for body in (str(values), json.dumps(values)):
            self.operation_log.request_body = body
            self.operation_log.json_result = str({'msg': {'refresh_token': 'OLD_REFRESH_TOKEN'}})
            self.operation_log.save()
            before = OperationLog.objects.filter(pk=self.operation_log.pk).values().get()
            client = APIClient()
            client.force_authenticate(self.admin)
            for suffix in ('', f'{self.operation_log.pk}/'):
                response = client.get('/api/system/operation_log/' + suffix)
                self.assertEqual(response.status_code, 200)
                content = response.content.decode()
                for secret in ('OLD_PASSWORD_SECRET', 'OLD_ACCESS_TOKEN', 'OLD_CLIENT_SECRET', 'OLD_REFRESH_TOKEN'):
                    self.assertTrue(secret not in content)
                self.assertIn('[REDACTED]', content)
                self.assertIn('[TRUNCATED]', content)
            self.assertTrue(before == OperationLog.objects.filter(pk=self.operation_log.pk).values().get())


def log_api_test(resource, actor, method, action):
    def test(self):
        client = APIClient()
        if actor != 'anonymous':
            client.force_authenticate(getattr(self, actor))
        row = getattr(self, resource)
        suffix = f'{row.pk}/' if action == 'detail' else (action + '/' if action else '')
        before = database_snapshot()
        with patch('coreadmin.utils.import_export_mixin.import_to_data') as importer, patch('openpyxl.load_workbook') as workbook:
            payload = {} if method in ('get', 'head') else {'keys': [row.pk], 'username': 'forged'}
            response = getattr(client, method)(f'/api/system/{resource}/{suffix}', payload, format='json')
            expected = (200,) if actor == 'admin' and method == 'get' and action in ('', 'detail') else ((405,) if actor == 'admin' else ((401, 403) if actor == 'anonymous' else (403,)))
            self.assertIn(response.status_code, expected)
            importer.assert_not_called()
            workbook.assert_not_called()
        self.assertTrue(before == database_snapshot(), 'Log API altered stored history')
    return test


for resource in ('operation_log', 'login_log'):
    for actor in ('anonymous', 'normal', 'inactive', 'admin'):
        for method, action in (('get', ''), ('get', 'detail'), ('post', ''), ('put', 'detail'), ('patch', 'detail'), ('delete', 'detail'), ('delete', 'multiple_delete'), ('get', 'import_data'), ('post', 'import_data'), ('head', 'import_data'), ('get', 'export_data'), ('head', 'export_data'), ('get', 'update_template')):
            setattr(LogAPITests, f'test_{resource}_{actor}_{method}_{action or "collection"}', log_api_test(resource, actor, method, action))


class SanitizerTests(SimpleTestCase):
    def test_recursive_key_normalization_and_fixed_marker(self):
        from coreadmin.utils.log_sanitization import sanitize_log_value
        keys = ('password', 'passwd', 'pwd', 'old_password', 'oldPassword', 'newPassword', 'confirmPassword', 'password1', 'password2', 'token', 'access', 'access_token', 'refresh', 'refreshToken', 'authorization', 'api-key', 'apiKey', 'secret', 'clientSecret', 'credential', 'credentials', 'cookie', 'session_id', 'captcha', 'captchaKey')
        for key in keys:
            data = {'items': [{key.upper(): 'TEST_ONLY_SECRET'}], 'normal': 'visible'}
            result = sanitize_log_value(data)
            self.assertEqual(result['items'][0][key.upper()], '[REDACTED]')
            self.assertEqual(result['normal'], 'visible')
            self.assertEqual(data['items'][0][key.upper()], 'TEST_ONLY_SECRET')

    def test_all_bounds_and_safe_total_preview(self):
        from coreadmin.utils.log_sanitization import sanitize_log_value, serialize_log_value, MAX_LOG_STRING_LENGTH, MAX_LOG_COLLECTION_ITEMS, MAX_LOG_SERIALIZED_SIZE, MAX_LOG_DEPTH
        long = 'x' * (MAX_LOG_STRING_LENGTH + 100)
        self.assertIn('[TRUNCATED]', sanitize_log_value(long))
        self.assertLessEqual(len(sanitize_log_value(long)), MAX_LOG_STRING_LENGTH)
        for value in (list(range(MAX_LOG_COLLECTION_ITEMS + 20)), {str(i): i for i in range(MAX_LOG_COLLECTION_ITEMS + 20)}):
            self.assertIn('[TRUNCATED]', json.dumps(sanitize_log_value(value)))
        deep = {'password': 'DEEP_SECRET'}
        for _ in range(MAX_LOG_DEPTH + 5):
            deep = {'nested': deep}
        self.assertIn('[MAX DEPTH]', json.dumps(sanitize_log_value(deep)))
        data = {str(i): {'secret': 'TOTAL_SECRET', 'visible': long} for i in range(50)}
        result = serialize_log_value(data)
        self.assertLessEqual(len(result.encode('utf-8')), MAX_LOG_SERIALIZED_SIZE)
        self.assertTrue('TOTAL_SECRET' not in result)
        self.assertIn('[TRUNCATED]', result)
        self.assertIsInstance(json.loads(result), (dict, list, str))
