from cachetools import TTLCache
from threading import Lock

_CACHE_TTL = 60
_CACHE_MAX = 512

_cache: TTLCache = TTLCache(maxsize=_CACHE_MAX, ttl=_CACHE_TTL)
_lock: Lock = Lock()

def cache_get(key: str):
    """Return cached value or None if missing / expired."""
    with _lock:
        return _cache.get(key)


def cache_set(key: str, value) -> None:
    """Store value under key. Evicts LRU entry if at capacity."""
    with _lock:
        _cache[key] = value


def cache_invalidate_all() -> None:
    """
    Wipe the entire cache.
    Called after CSV ingestion completes so the next query hits the database
    and picks up the newly inserted rows.
    """
    with _lock:
        _cache.clear()


def cache_stats() -> dict:
    """Return basic stats — useful for a /health or /debug endpoint."""
    with _lock:
        return {
            "size": len(_cache),
            "maxsize": _CACHE_MAX,
            "ttl_seconds": _CACHE_TTL,
            "currsize": _cache.currsize,
        }