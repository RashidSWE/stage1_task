import json

# Gender synonym map — all known aliases → canonical form
_GENDER_MAP: dict[str, str] = {
    "male":    "male",
    "males":   "male",
    "man":     "male",
    "men":     "male",
    "boy":     "male",
    "boys":    "male",
    "m":       "male",
    "female":  "female",
    "females": "female",
    "woman":   "female",
    "women":   "female",
    "girl":    "female",
    "girls":   "female",
    "f":       "female",
}

_VALID_AGE_GROUPS = {"child", "teenager", "young adult", "adult", "senior"}
_VALID_SORT_BY    = {"age", "created_at", "name", "country_id"}
_VALID_ORDER      = {"asc", "desc"}


def normalize_filters(filters: dict) -> dict:
    """
    Accept the raw filter dict produced by the existing query parser
    and return a canonical version with:
      - all string values lowercased / uppercased as appropriate
      - gender synonyms collapsed
      - age range sorted [min, max]
      - keys in alphabetical order
      - None / missing values omitted entirely

    The returned dict is what gets serialized into the cache key and
    passed to the database query builder.
    """
    out = {}

    # --- gender ---
    raw_gender = filters.get("gender")
    if raw_gender is not None:
        canonical = _GENDER_MAP.get(str(raw_gender).strip().lower())
        if canonical:
            out["gender"] = canonical

    # --- country_id ---
    raw_country = filters.get("country_id")
    if raw_country is not None:
        out["country_id"] = str(raw_country).strip().upper()

    # --- age range ---
    raw_min = filters.get("min_age")
    raw_max = filters.get("max_age")

    if raw_min is not None:
        try:
            out["min_age"] = max(0, int(raw_min))
        except (ValueError, TypeError):
            pass

    if raw_max is not None:
        try:
            out["max_age"] = min(150, int(raw_max))
        except (ValueError, TypeError):
            pass

    # Swap if caller provided them reversed
    if "min_age" in out and "max_age" in out:
        if out["min_age"] > out["max_age"]:
            out["min_age"], out["max_age"] = out["max_age"], out["min_age"]

    # --- age_group ---
    raw_group = filters.get("age_group")
    if raw_group is not None:
        normalized_group = str(raw_group).strip().lower()
        if normalized_group in _VALID_AGE_GROUPS:
            out["age_group"] = normalized_group

    # --- sort_by ---
    raw_sort = filters.get("sort_by")
    if raw_sort is not None:
        normalized_sort = str(raw_sort).strip().lower()
        if normalized_sort in _VALID_SORT_BY:
            out["sort_by"] = normalized_sort

    # --- order ---
    raw_order = filters.get("order")
    if raw_order is not None:
        normalized_order = str(raw_order).strip().lower()
        if normalized_order in _VALID_ORDER:
            out["order"] = normalized_order

    # --- limit ---
    raw_limit = filters.get("limit")
    if raw_limit is not None:
        try:
            out["limit"] = max(1, min(50, int(raw_limit)))
        except (ValueError, TypeError):
            pass

    # --- page ---
    raw_page = filters.get("page")
    if raw_page is not None:
        try:
            out["page"] = max(1, int(raw_page))
        except (ValueError, TypeError):
            pass

    return dict(sorted(out.items()))


def make_cache_key(filters: dict) -> str:
    """
    Serialize a normalized filter dict into a stable string cache key.
    Uses json.dumps with sort_keys=True as a second safety net.

    Example:
        {"country_id": "NG", "gender": "female", "min_age": 20, "max_age": 45}
        → '{"country_id": "NG", "gender": "female", "max_age": 45, "min_age": 20}'
    """
    normalized = normalize_filters(filters)
    return json.dumps(normalized, sort_keys=True)
