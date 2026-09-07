"""Temporary current-user helpers until real authentication exists.

Prefer importing ``CurrentUserDep`` / ``get_current_user`` from ``app.api.deps``.
"""

from __future__ import annotations

USER_ID_HEADER = "X-User-ID"
