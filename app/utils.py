arr = self._store.get(key, [])
        # keep only within window
        arr = [t for t in arr if now - t <= self.window_sec]
        if len(arr) >= self.max_hits:
            self._store[key] = arr
            return False
        arr.append(now)
        self._store[key] = arr
        return True


# ---------------------------
# LIMIT HELPERS
# ---------------------------

def is_blocked(blocked_until: Optional[dt.datetime]) -> bool:
    if not blocked_until:
        return False
    return utcnow() < blocked_until


def ensure_non_negative(x: int) -> int:
    return max(0, int(x))


def apply_decrement(value: int, dec: int = 1) -> int:
    """Decrement but never below 0."""
    return max(0, int(value) - int(dec))


# ---------------------------
# FILE / MEDIA HELPERS
# ---------------------------

def safe_filename(name: str, ext: str = "") -> str:
    """
    Make safe filename (latin, digits, underscore).
    """
    base = re.sub(r"[^a-zA-Z0-9_\-]+", "_", (name or "file")).strip("_")
    base = base[:60] if base else "file"
    if ext:
        ext = ext.lstrip(".")
        return f"{base}.{ext}"
    return base


def bytes_to_mb(n: int) -> float:
    return round(n / (1024 * 1024), 2)


# ---------------------------
# PRICE HELPERS
# ---------------------------

def money_usd(amount: float) -> str:
    """Format $12.00"""
    try:
        return f"${float(amount):.2f}"
    except Exception:
        return "$0.00"


# ---------------------------
# DEBUG SAFE
# ---------------------------

def safe_err(e: Exception) -> str:
    """
    Short safe error string for logs / admin messages.
    """
    name = e.class.name
    msg = str(e)
    msg = msg[:400]
    return f"{name}: {msg}"
