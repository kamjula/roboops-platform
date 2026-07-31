"""Shared service-layer exceptions for the Phase 3 CRUD services."""


class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""


class ConflictError(Exception):
    """Raised when an operation would violate a uniqueness or referential-integrity constraint."""


class InvalidReferenceError(Exception):
    """Raised when a referenced foreign-key id (e.g. site_id, model_id) does not exist."""
