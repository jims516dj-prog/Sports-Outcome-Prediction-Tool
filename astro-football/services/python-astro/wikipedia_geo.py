"""Stadium coordinates (spec 3.2): Wikipedia first, OpenStreetMap fallback; plus timezone lookup."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx
from timezonefinder import TimezoneFinder

UA = {"User-Agent": "astro-football/1.0 (stadium coordinate lookup; research use)"}
WIKI = "https://en.wikipedia.org/w/api.php"
_tf = TimezoneFinder()


def wikipedia_coords(title: str, timeout=3.0):
    """Returns {lat, long, pageId, canonicalName} or None."""
    with httpx.Client(timeout=timeout, headers=UA) as cl:
        r = cl.get(WIKI, params={"action": "query", "format": "json", "prop": "coordinates|pageprops",
                                 "titles": title, "redirects": 1, "coprimary": "all"})
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", {})
        for pid, pg in pages.items():
            if int(pid) < 0:
                continue
            if "disambiguation" in pg.get("pageprops", {}):
                break                       # fall through to search
            coords = pg.get("coordinates") or []
            if coords:
                best = next((c for c in coords if c.get("primary") is not None), coords[0])
                return {"lat": best["lat"], "long": best["lon"], "pageId": int(pid), "canonicalName": pg["title"]}
        # disambiguation / no coordinates: search for a stadium article
        s = cl.get(WIKI, params={"action": "query", "format": "json", "list": "search",
                                 "srsearch": f"{title} stadium", "srlimit": 3})
        s.raise_for_status()
        for hit in s.json().get("query", {}).get("search", []):
            if hit["title"] != title:
                res = wikipedia_coords_direct(cl, hit["title"])
                if res:
                    return res
    return None


def wikipedia_coords_direct(cl, title):
    r = cl.get(WIKI, params={"action": "query", "format": "json", "prop": "coordinates", "titles": title,
                             "redirects": 1})
    for pid, pg in r.json().get("query", {}).get("pages", {}).items():
        if int(pid) > 0 and pg.get("coordinates"):
            c = pg["coordinates"][0]
            return {"lat": c["lat"], "long": c["lon"], "pageId": int(pid), "canonicalName": pg["title"]}
    return None


def osm_coords(name: str, timeout=3.0):
    with httpx.Client(timeout=timeout, headers=UA) as cl:
        r = cl.get("https://nominatim.openstreetmap.org/search", params={"q": name, "format": "json", "limit": 1})
        r.raise_for_status()
        js = r.json()
        if js:
            return {"lat": float(js[0]["lat"]), "long": float(js[0]["lon"]), "canonicalName": js[0].get("display_name")}
    return None


def lookup(name: str, wiki_title: str | None = None):
    errors = []
    try:
        res = wikipedia_coords(wiki_title or name)
        if res:
            return res | {"source": "wikipedia", "timezone": tz_at(res["lat"], res["long"])}
    except Exception as e:
        errors.append(f"Wikipedia: {type(e).__name__}")
    try:
        res = osm_coords(name)
        if res:
            return res | {"source": "openstreetmap", "timezone": tz_at(res["lat"], res["long"])}
    except Exception as e:
        errors.append(f"OpenStreetMap: {type(e).__name__}")
    return {"source": None, "errors": errors,
            "message": "Lookup unavailable - please enter coordinates manually"}


def tz_at(lat, lon):
    return _tf.timezone_at(lat=lat, lng=lon) or "UTC"


def gmt_to_local(dt_utc: datetime, lat, lon):
    tz = tz_at(lat, lon)
    loc = dt_utc.astimezone(ZoneInfo(tz))
    return {"timezone": tz, "local": loc.strftime("%Y-%m-%dT%H:%M"), "utc_offset": loc.strftime("%z"),
            "dst": bool(loc.dst())}


def local_to_gmt(local_naive: datetime, lat, lon):
    tz = tz_at(lat, lon)
    loc = local_naive.replace(tzinfo=ZoneInfo(tz))
    utc = loc.astimezone(timezone.utc)
    return {"timezone": tz, "gmt": utc.strftime("%Y-%m-%dT%H:%M"), "utc_offset": loc.strftime("%z")}
