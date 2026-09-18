"""Commit-after operational projections; no security authority."""
import logging
from django.db import transaction

logger = logging.getLogger(__name__)


def after_commit(callback):
    def run():
        try:
            callback()
        except Exception:
            # Do not log callback arguments or configuration/credential values.
            logger.error("Committed projection refresh failed", exc_info=False)
    transaction.on_commit(run)
