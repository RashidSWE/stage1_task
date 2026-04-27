from sqlmodel import Session
from app.db.session import get_session
import re
import pycountry

def get_country_code(q: str) -> str:
    for country in pycountry.countries:
        if country.name.lower() in q:
            return country.alpha_2
    return None

def parse_query(q: str) -> str:
    text = q.lower().strip()
    filters = {}

    # gender
    if any(w in text for w in ["female", "females", "women", "woman", "girl", "girls"]):
        filters["gender"] = "female"
    elif any(w in text for w in ["male", "males", "men", "man", "boy", "boys"]):
        filters["gender"] = "male"
    # "male and female" or "both" = no gender filter

    # "young" → ages 16–24 (not an age_group, just min/max age)
    if "young" in text:
        filters["min_age"] = 16
        filters["max_age"] = 24

    # age group — only if "young" not already matched
    if "young" not in text:
        if any(w in text for w in ["senior", "elderly", "old people", "old men", "old women"]):
            filters["age_group"] = "senior"
        elif "adult" in text:
            filters["age_group"] = "adult"
        elif any(w in text for w in ["teenager", "teenagers", "teen", "teens", "adolescent"]):
            filters["age_group"] = "teenager"
        elif any(w in text for w in ["child", "children", "kid", "kids"]):
            filters["age_group"] = "child"
    
    # min/max age — matches "over 30", "above 25", "under 18", "below 40", "older than 50"
    over = re.search(r"(?:over|above|older than|greater than)\s*(\d+)", q)
    under = re.search(r"(?:under|below|younger than|less than)\s*(\d+)", q)
    between = re.search(r"between\s*(\d+)\s*and\s*(\d+)", q)

    if between:
        filters["min_age"] = int(between.group(1))
        filters["max_age"] = int(under.group(2))
    else:
        if over:
            filters["min_age"] = int(over.group(1))
        if under:
            filters["max"] = int(under.group(1))
    
    country_code = get_country_code(q)
    if country_code:
        filters["country_id"] = country_code
    else:
        iso = re.search(r'\b([a-z]{2})\b', text)
        if iso:
            candidate = iso.group(1).upper()
            if pycountry.countries.get(alpha_2=candidate):
                filters["country_id"] = candidate

    if any(w in text for w in ["sort by age", "order by age", "ranked by age"]):
        filters["sort_by"] = "age"
    elif any(w in text for w in ["recent", "latest", "newest"]):
        filters["sort_by"] = "created_at"
        filters["order"] = "desc"

    # order
    if any(w in text for w in ["descending", "desc", "highest", "oldest"]):
        filters["order"] = "desc"
    elif any(w in text for w in ["ascending", "asc", "lowest", "youngest"]):
        filters["order"] = "asc"

    limit_match = re.search(r"\b(?:top|first|limit)\s*(\d+)\b", q)
    if limit_match:
        filters["limit"] = min(int(limit_match.group(1)), 50)

    if not filters:
        return None
    return filters
