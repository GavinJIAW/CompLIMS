"""Bounded structured redaction for operational logs, not an AuditTrail."""
import ast
import json
import math
from itertools import islice

MAX_LOG_STRING_LENGTH = 2048
MAX_LOG_COLLECTION_ITEMS = 50
MAX_LOG_DEPTH = 6
MAX_LOG_SERIALIZED_SIZE = 32768
# A global work limit also bounds wide, deeply nested collections.
MAX_LOG_NODES = 1024
REDACTED = '[REDACTED]'
TRUNCATED = '[TRUNCATED]'


def sensitive_key(key):
    normalized = str(key).lower().replace('_', '').replace('-', '')
    return ('password' in normalized or normalized.endswith('token') or 'secret' in normalized
            or normalized in {'passwd', 'pwd', 'authorization', 'access', 'refresh', 'apikey',
                              'credential', 'credentials', 'cookie', 'sessionid', 'captcha', 'captchakey'})


def bounded_string(value, limit=MAX_LOG_STRING_LENGTH):
    return value if len(value) <= limit else value[:max(0, limit - len(TRUNCATED))] + TRUNCATED


def parse_log_text(value):
    """Decode bounded JSON/legacy literal text without evaluating executable code.

    Oversized or malformed structured text must never fall back to a raw preview.
    Free text cannot be comprehensively secret-detected; reads remain superuser-only.
    """
    if not isinstance(value, str):
        return value
    stripped = value.lstrip()
    if not stripped.startswith(('{', '[', '(')):
        return value
    if len(value) > MAX_LOG_SERIALIZED_SIZE:
        return TRUNCATED
    try:
        return json.loads(value)
    except (ValueError, RecursionError):
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError, TypeError, RecursionError, MemoryError):
            return '[UNPARSEABLE STRUCTURED LOG]'


def sanitize_log_value(value):
    remaining = MAX_LOG_NODES

    def walk(item, depth):
        nonlocal remaining
        if remaining <= 0:
            return TRUNCATED
        remaining -= 1
        if depth > MAX_LOG_DEPTH:
            return '[MAX DEPTH]'
        if isinstance(item, dict):
            result = {}
            for key, child in islice(item.items(), MAX_LOG_COLLECTION_ITEMS):
                safe_key = bounded_string(str(key)) if isinstance(key, (str, int, float, bool)) else '[UNSUPPORTED KEY]'
                result[safe_key] = REDACTED if isinstance(key, str) and sensitive_key(key) else walk(child, depth + 1)
                if remaining <= 0:
                    break
            if len(item) > MAX_LOG_COLLECTION_ITEMS or remaining <= 0:
                result[TRUNCATED] = True
            return result
        if isinstance(item, (list, tuple)):
            result = []
            for child in islice(item, MAX_LOG_COLLECTION_ITEMS):
                result.append(walk(child, depth + 1))
                if remaining <= 0:
                    break
            if len(item) > MAX_LOG_COLLECTION_ITEMS or remaining <= 0:
                result.append(TRUNCATED)
            return result
        if isinstance(item, str):
            return bounded_string(item)
        if item is None or isinstance(item, (bool, int)):
            return item
        if isinstance(item, float):
            return item if math.isfinite(item) else '[NONFINITE NUMBER]'
        # Do not call repr/str on arbitrary objects (files, lazy objects, credentials).
        return '[UNSUPPORTED VALUE]'

    return walk(value, 0)


def serialize_log_value(value, *, historical=False):
    if historical:
        value = parse_log_text(value)
    encoded = json.dumps(sanitize_log_value(value), ensure_ascii=True)
    if len(encoded) > MAX_LOG_SERIALIZED_SIZE:
        # Only preview already-redacted JSON; reserve space for escaping/wrapper.
        encoded = json.dumps({'preview': encoded[:MAX_LOG_SERIALIZED_SIZE // 4], TRUNCATED: True}, ensure_ascii=True)
    return encoded
