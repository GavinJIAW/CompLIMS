"""Server-owned operational target metadata; never an authorization decision."""
import json
import logging

logger = logging.getLogger(__name__)


def record_targets(request, targets):
    """Accept only already-resolved integer PKs, without log-body size limits.

    Called after existing authorization/target checks. Metadata failures must
    never change the outcome of a business command.
    """
    if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
        return
    try:
        raw_request = getattr(request, '_request', request)
        combined = {key: set(values) for key, values in
                    getattr(raw_request, '_operation_log_targets', {}).items()}
        for key, values in targets.items():
            if not isinstance(key, str) or any(type(pk) is not int for pk in values):
                raise ValueError('Expected resolved integer PKs')
            combined.setdefault(key, set()).update(values)
        ordered = {key: sorted(values) for key, values in sorted(combined.items())}
        encoded = json.dumps(ordered, separators=(',', ':'))
        raw_request._operation_log_targets = ordered
        raw_request._operation_log_request_target = encoded
    except Exception:
        logger.error('Operational target metadata collection failed', exc_info=False)
