"""Conservative, side-effect-free price-list matching for NOVA.

Never guesses a product from a similar name. All ambiguous or missing matches
are returned for human review; package factor and purchase history are supplied
by the caller from the *current* database.
"""
from decimal import Decimal
from nova_price_list_preview import normalized_name, proposed_sale, money

def _key(row):
    return (normalized_name(row.get("name")), normalized_name(row.get("strength")),
            normalized_name(row.get("pack")))

def preview(uploaded, catalog, last_purchases, markup_override=None):
    """Return reviewable records without changing prices or inventory.

    catalog: dict rows {package_id, name, strength, pack, sale_price, factor}
    last_purchases: {package_id: {price, factor}} using latest actual purchase
    across *all* suppliers, fetched by caller. Prices refer to whole packs.
    """
    lookup = {}
    for item in catalog:
        lookup.setdefault(_key(item), []).append(item)
    results = []
    seen = set()
    for row in uploaded:
        matches = lookup.get(_key(row), [])
        record = {"source": row, "status": "review", "reason": "", "selected": False}
        if len(matches) != 1:
            record["reason"] = "unmatched" if not matches else "ambiguous"
            results.append(record)
            continue
        item = matches[0]
        package_id = int(item["package_id"])
        if package_id in seen:
            record["reason"] = "duplicate_in_upload"
            results.append(record)
            continue
        seen.add(package_id)
        last = last_purchases.get(package_id)
        if not last:
            record["reason"] = "no_actual_purchase"
            results.append(record)
            continue
        old = money(last["price"])
        new = money(row["purchase_price"])
        old_factor = Decimal(str(last.get("factor", item["factor"])))
        target_factor = Decimal(str(item["factor"]))
        if old_factor <= 0 or target_factor <= 0:
            record["reason"] = "invalid_unit_factor"
            results.append(record)
            continue
        normalized_old = Decimal(old) * target_factor / old_factor
        if normalized_old <= 0 or normalized_old != normalized_old.to_integral_value():
            record["reason"] = "nonintegral_or_zero_reference_cost"
            results.append(record)
            continue
        old_equivalent = int(normalized_old)
        record.update(package_id=package_id, old_purchase=old_equivalent,
                      new_purchase=new, old_sale=money(item["sale_price"]))
        if new == old_equivalent:
            record.update(status="unchanged", reason="same_purchase_price")
        else:
            proposed = proposed_sale(old_equivalent, item["sale_price"], new, markup_override)
            if proposed is None:
                record["reason"] = "no_reference_markup"
            else:
                record.update(status="ready", selected=True, proposed_sale=proposed,
                              delta=new-old_equivalent,
                              change_percent=str((Decimal(new-old_equivalent) * 100 /
                                                  Decimal(old_equivalent)).quantize(Decimal("0.01"))))
        results.append(record)
    return results
