from __future__ import annotations


class DreameSmartlifeError(Exception):
    """Base Dreame Smart Life exception."""


class DreameSmartlifeAuthError(DreameSmartlifeError):
    """Authentication failed."""


class DreameSmartlifeApiError(DreameSmartlifeError):
    """Remote API error."""
