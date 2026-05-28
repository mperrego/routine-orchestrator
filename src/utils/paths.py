"""Path utilities — ecosystem-shaped, promotion candidate for sync_core."""

import os
import re
import time


_MY_DRIVE_RE = re.compile(r'[\\/]My Drive(?=$|[\\/])')


def _now_ms(started):
    return int((time.monotonic() - started) * 1000)


def reanchor_my_drive_path(path, current_my_drive_root=None):
    """Re-anchor a stored path to the current machine's My Drive root.

    Args:
        path: absolute path string that may contain a "My Drive" segment.
        current_my_drive_root: optional override for the current machine's
            My Drive root. Defaults to "<user home>/My Drive".

    Returns a structured response per ecosystem Rule 7:
        status: 'success' | 'skipped' | 'error'
        data:
            success → {'path': re-anchored path, 'original': original path}
            skipped → {'path': original path, 'reason': str}
            error   → None
        error_type / error_message: populated only on error
        duration_ms: int
    """
    started = time.monotonic()
    try:
        if not isinstance(path, str) or not path:
            return {
                'status': 'error',
                'data': None,
                'error_type': 'TypeError',
                'error_message': 'path must be a non-empty string',
                'duration_ms': _now_ms(started),
            }

        parts = _MY_DRIVE_RE.split(path, maxsplit=1)
        if len(parts) != 2:
            return {
                'status': 'skipped',
                'data': {'path': path, 'reason': 'no_my_drive_anchor'},
                'error_type': None,
                'error_message': None,
                'duration_ms': _now_ms(started),
            }

        if current_my_drive_root is None:
            current_my_drive_root = os.path.join(os.path.expanduser('~'), 'My Drive')

        tail = parts[1].lstrip('\\/')
        new_path = (
            os.path.normpath(os.path.join(current_my_drive_root, tail))
            if tail
            else os.path.normpath(current_my_drive_root)
        )

        return {
            'status': 'success',
            'data': {'path': new_path, 'original': path},
            'error_type': None,
            'error_message': None,
            'duration_ms': _now_ms(started),
        }
    except Exception as exc:
        return {
            'status': 'error',
            'data': None,
            'error_type': type(exc).__name__,
            'error_message': str(exc),
            'duration_ms': _now_ms(started),
        }
