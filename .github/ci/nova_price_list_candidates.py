"""Review-only candidate suggestions for mismatched supplier spellings.

No database writes, no automatic fuzzy approvals. Suggestions must be
confirmed by a human, and strength/pack/form conflicts are never hidden.
"""
from difflib import SequenceMatcher
from nova_price_list_preview import normalized_name

def candidates(upload_row, catalog, aliases=(), limit=5):
    """Return possible matches and explicit conflict flags.

    aliases: iterable of {alias, package_id}; aliases are NOT approval.
    """
    name = normalized_name(upload_row.get("name"))
    if not name:
        return []
    alias_ids = {int(a["package_id"]) for a in aliases
                 if normalized_name(a.get("alias")) == name}
    out = []
    for item in catalog:
        target = normalized_name(item.get("name"))
        if not target:
            continue
        similarity = SequenceMatcher(None, name, target).ratio()
        alias_hit = int(item["package_id"]) in alias_ids
        if similarity < 0.55 and not alias_hit:
            continue
        conflicts = []
        for field in ("strength", "pack", "form", "manufacturer"):
            left = normalized_name(upload_row.get(field))
            right = normalized_name(item.get(field))
            if left and right and left != right:
                conflicts.append(field)
        out.append({"package_id": int(item["package_id"]),
                    "catalog_name": item.get("name"),
                    "supplier_name": upload_row.get("name"),
                    "score": round(similarity, 3),
                    "known_alias": alias_hit,
                    "conflicts": conflicts,
                    "requires_confirmation": True})
    return sorted(out, key=lambda r: (bool(r["conflicts"]), not r["known_alias"],
                                     -r["score"], r["package_id"]))[:limit]
