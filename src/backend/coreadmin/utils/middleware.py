"""
日志 django中间件
"""
import json
import logging

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, HttpResponseServerError
from django.utils.deprecation import MiddlewareMixin

from coreadmin.system.models import OperationLog
from coreadmin.utils.request_util import get_request_ip, get_request_path, get_os, get_browser, get_verbose_name
from coreadmin.utils.log_sanitization import serialize_log_value, bounded_string, MAX_LOG_SERIALIZED_SIZE, TRUNCATED

logger = logging.getLogger(__name__)


class ApiLoggingMiddleware(MiddlewareMixin):
    """Best-effort final-response operational logging; never a business audit trail."""

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.enable = bool(getattr(settings, 'API_LOG_ENABLE', False))
        self.methods = getattr(settings, 'API_LOG_METHODS', ())

    def eligible(self, request):
        return self.enable and (self.methods == 'ALL' or request.method in self.methods
                               or (request.method == 'PATCH' and 'PUT' in self.methods))

    def process_request(self, request):
        if not self.eligible(request):
            return
        try:
            metadata = {'ip': get_request_ip(request), 'path': get_request_path(request)}
            # Cache only bounded JSON bytes so DRF can still read the original stream.
            # Never force multipart parsing, file reads, or request.POST before permission.
            length = int(request.META.get('CONTENT_LENGTH') or 0)
            if request.content_type == 'application/json':
                if 0 < length <= MAX_LOG_SERIALIZED_SIZE:
                    metadata['body'] = request.body
                elif length > MAX_LOG_SERIALIZED_SIZE:
                    metadata['body_omitted'] = True
            request._operation_log_metadata = metadata
        except Exception:
            logger.exception('Operational log metadata collection failed')

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not self.eligible(request):
            return
        try:
            metadata = getattr(request, '_operation_log_metadata', {})
            view = getattr(view_func, 'cls', None)
            queryset = getattr(view, 'queryset', None)
            metadata['module'] = get_verbose_name(queryset) if queryset is not None else ''
            request._operation_log_metadata = metadata
        except Exception:
            logger.exception('Operational log route collection failed')

    def request_payload(self, request, metadata):
        # Build a separate dictionary; never inject/pop a client log_id.
        query = {key: values if len(values) > 1 else values[0] for key, values in request.GET.lists()}
        supplied = getattr(request, 'request_data', None)
        if supplied is not None:
            return {'query': query, 'body': supplied}
        if metadata.get('body_omitted'):
            return {'query': query, 'body': TRUNCATED}
        body = metadata.get('body')
        if body:
            try:
                body = json.loads(body)
            except (ValueError, UnicodeError, RecursionError):
                body = '[UNPARSEABLE BODY]'
        else:
            # Only inspect forms that the business endpoint already parsed.
            post = getattr(request, '_post', None)
            body = dict(post.lists()) if post is not None else {}
        return {'query': query, 'body': body}

    def response_summary(self, response):
        data = getattr(response, 'data', None)
        if not isinstance(data, dict):
            data = {}
            if not getattr(response, 'streaming', False) and 'json' in response.get('Content-Type', ''):
                content = response.content
                if len(content) <= MAX_LOG_SERIALIZED_SIZE:
                    try:
                        decoded = json.loads(content)
                        if isinstance(decoded, dict):
                            data = decoded
                    except (ValueError, UnicodeError, RecursionError):
                        pass
        return data

    def process_response(self, request, response):
        if not self.eligible(request) or getattr(request, '_operation_log_finished', False):
            return response
        # No retry: even a persistence error must not duplicate a possibly saved row.
        request._operation_log_finished = True
        try:
            metadata = getattr(request, '_operation_log_metadata', {})
            data = self.response_summary(response)
            user = getattr(request, 'user', None)
            creator = user if getattr(user, 'is_authenticated', False) else None
            path = metadata.get('path', request.path)
            module = metadata.get('module') or getattr(settings, 'API_MODEL_MAP', {}).get(path, '')
            session = getattr(request, 'session', {})
            code = data.get('code')
            info = {
                'request_ip': bounded_string(str(metadata.get('ip', 'unknown')), 32),
                'creator': creator,
                'dept_belong_id': getattr(creator, 'dept_id', None),
                'request_method': bounded_string(request.method, 8),
                'request_path': bounded_string(path, 400),
                'request_modular': bounded_string(str(module), 64),
                'request_body': serialize_log_value(self.request_payload(request, metadata)),
                'request_target': getattr(request, '_operation_log_request_target', None),
                'response_code': bounded_string(str(code), 32) if isinstance(code, (str, int)) else None,
                'request_os': bounded_string(get_os(request), 64),
                'request_browser': bounded_string(get_browser(request), 64),
                'request_msg': serialize_log_value(session.get('request_msg')),
                'status': 200 <= response.status_code < 400 and ('code' not in data or code == 2000),
                'json_result': serialize_log_value({'code': code, 'msg': data.get('msg'), 'http_status': response.status_code}),
            }
            # Savepoint isolates a log DB error from any enclosing transaction.
            with transaction.atomic():
                OperationLog.objects.create(**info)
        except Exception:
            logger.exception('Operational log persistence failed')
        return response

health_logger = logging.getLogger("healthz")
class HealthCheckMiddleware(object):
    """
    存活检查中间件
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        if request.method == "GET":
            if request.path == "/readiness":
                return self.readiness(request)
            elif request.path == "/healthz":
                return self.healthz(request)
        return self.get_response(request)

    def healthz(self, request):
        """
        Returns that the server is alive.
        """
        return HttpResponse("OK")

    def readiness(self, request):
        # Connect to each database and do a generic standard SQL query
        # that doesn't write any data and doesn't depend on any tables
        # being present.
        try:
            from django.db import connections
            for name in connections:
                cursor = connections[name].cursor()
                cursor.execute("SELECT 1;")
                row = cursor.fetchone()
                if row is None:
                    return HttpResponseServerError("db: invalid response")
        except Exception as e:
            health_logger.exception(e)
            return HttpResponseServerError("db: cannot connect to database.")

        # Call get_stats() to connect to each memcached instance and get it's stats.
        # This can effectively check if each is online.
        try:
            from django.core.cache import caches
            from django.core.cache.backends.memcached import BaseMemcachedCache
            for cache in caches.all():
                if isinstance(cache, BaseMemcachedCache):
                    stats = cache._cache.get_stats()
                    if len(stats) != len(cache._servers):
                        return HttpResponseServerError("cache: cannot connect to cache.")
        except Exception as e:
            health_logger.exception(e)
            return HttpResponseServerError("cache: cannot connect to cache.")

        return HttpResponse("OK")
