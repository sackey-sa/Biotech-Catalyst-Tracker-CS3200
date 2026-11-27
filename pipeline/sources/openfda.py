"""openFDA drugsfda: FDA applications per sponsor, reduced to the original (ORIG) submission.

Notes:
- sponsor_name is an exact-match field, so we search by prefix ("VERTEX*").
- Vaccines and other CBER biologics (e.g. Moderna's) are not in drugsfda.
- openFDA does not publish complete response letters (rejections); those come from press releases.
"""
from pipeline import config
from pipeline.http import ApiClient
from pipeline.normalize import parse_yyyymmdd

_client = ApiClient("https://api.fda.gov", config.DEFAULT_USER_AGENT, min_interval=0.3)
_PAGE = 1000


def _original_submission(app: dict) -> dict | None:
    """Pick the ORIG submission: the earliest approval if there is one, else the latest ORIG."""
    origs = [s for s in app.get("submissions", [])
             if s.get("submission_type") == "ORIG" and parse_yyyymmdd(s.get("submission_status_date"))]
    if not origs:
        return None
    approved = [s for s in origs if s.get("submission_status") == "AP"]
    if approved:
        return min(approved, key=lambda s: s["submission_status_date"])
    return max(origs, key=lambda s: s["submission_status_date"])


def _drug(app: dict) -> dict:
    """Brand name and active ingredient(s) of the application's first product."""
    products = app.get("products") or [{}]
    first = products[0]
    ingredients = sorted({i["name"].strip() for i in first.get("active_ingredients", []) if i.get("name")})
    brand = first.get("brand_name") or (app.get("openfda", {}).get("brand_name") or [None])[0]
    return {"brand_name": brand, "active_ingredient": "; ".join(ingredients) or brand or "UNKNOWN"}


def applications_by_sponsor_prefix(prefix: str) -> list[dict]:
    """Original applications whose sponsor name starts with `prefix` (case-insensitive)."""
    search = f"sponsor_name:{prefix.upper().replace(' ', '?')}*"
    out, skip = [], 0
    while True:
        data = _client.get("drug/drugsfda.json", {"search": search, "limit": _PAGE, "skip": skip},
                           allow_404=True)  # openFDA returns 404 for "no matches"
        if not data:
            return out
        for app in data["results"]:
            sub = _original_submission(app)
            if sub is None:
                continue
            out.append({
                "application_number": app["application_number"],
                "sponsor_name": app.get("sponsor_name"),
                "submission_type": sub["submission_type"],
                "status": sub.get("submission_status") or "UNKNOWN",
                "action_date": parse_yyyymmdd(sub["submission_status_date"]),
                **_drug(app),
            })
        skip += _PAGE
        if skip >= data["meta"]["results"]["total"]:
            return out
