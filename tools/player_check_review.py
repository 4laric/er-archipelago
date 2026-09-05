"""Plain-language check projection. Presentation only; never adjudicates claims."""
from __future__ import annotations
import re


def player_check(check: dict, confidence: dict | None = None, grace: str = "") -> dict:
    name = check["name"].split(" :: ", 1)[-1]
    name = name.split(", may be sweep-granted", 1)[0]
    name = re.sub(r"\s*\[f\d+\]\s*$", "", name).strip()
    item, sep, place = name.partition(" - ")
    item = re.sub(r"^\[(?:Incantation|Sorcery)\]\s*", "", item)
    tags = set(check["tags"])
    kind = ("Shops" if "Shop" in tags else "Boss rewards" if "Boss" in tags
            else "Quest items" if "KeyItem" in tags else
            "Flask and blessing upgrades" if tags & {"Church", "Seedtree", "Fragment", "Revered"}
            else "Other pickups")
    region_claim = next(c for c in check["claims"] if c["claim_kind"] == "region")
    value = region_claim["value"]
    region = value.get("region", "") if isinstance(value, dict) else str(value)
    conflict = any(c["status"] == "conflicted" for c in check["claims"])
    count = confidence["external_family_count"] if confidence else None
    need = ("conflict" if conflict else "confirmed" if confidence
            and confidence["confidence"] == "trusted_identity_region"
            else "second_source" if count == 1 else "first_source")
    if not place or re.fullmatch(r"m\d\d(?:_\d\d){1,3}(?:.*)?", place):
        place = "Exact spot still needs a description"
    return {"item": item, "place": place, "region": region, "kind": kind,
            "nearby_grace": grace, "need": need, "family_count": count,
            "access_reviewed": bool(check["access_dispositions"]) and all(
                d["disposition"] in {"encoded", "region_sufficient"}
                for d in check["access_dispositions"])}
