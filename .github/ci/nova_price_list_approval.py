"""NOVA bulk price approval guard.

Pure validation and conditional updates. The caller owns permissions,
database transaction, audit logging and durable batch persistence.
"""
from nova_price_list_preview import money

def validate_approval(preview_rows, decisions, current_prices):
    """Return conditional sale-price changes; fail closed on stale data.

    decisions: {package_id: {action:'approve'|'skip', sale_price:int}}
    current_prices: {package_id: current sale price read immediately before commit}
    """
    approved = []
    seen = set()
    for row in preview_rows:
        if row.get("status") != "ready":
            continue
        package_id = int(row["package_id"])
        if package_id in seen:
            raise ValueError("Duplicate package in preview")
        seen.add(package_id)
        choice = decisions.get(package_id, {"action": "skip"})
        if choice.get("action") == "skip":
            continue
        if choice.get("action") != "approve":
            raise ValueError("Unknown approval action")
        if not row.get("selected", False):
            raise ValueError("Row was not selected")
        old_sale = money(row["old_sale"])
        if package_id not in current_prices or money(current_prices[package_id]) != old_sale:
            raise ValueError("Stale sale price: refresh preview")
        new_sale = money(choice.get("sale_price", row.get("proposed_sale")))
        if new_sale <= 0:
            raise ValueError("Sale price must be positive")
        if new_sale != old_sale:
            approved.append({"package_id": package_id, "expected_sale": old_sale,
                             "new_sale": new_sale, "source_purchase_price": money(row["new_purchase"])})
    for key, choice in decisions.items():
        if choice.get("action") == "approve" and int(key) not in seen:
            raise ValueError("Unreviewed or unmatched item cannot be approved")
    return approved

def apply_approved(cursor, changes, audit_callback):
    """Call inside caller's existing BEGIN/COMMIT transaction; rollback on error.

    Optimistic UPDATE prevents overwriting concurrent price edits.
    """
    for change in changes:
        res = cursor.execute(
            "UPDATE packages SET sale_price=? WHERE id=? AND sale_price=?",
            (change["new_sale"], change["package_id"], change["expected_sale"]))
        if res.rowcount != 1:
            raise ValueError("Concurrent price change: rollback batch")
        audit_callback("bulk_price_list_sale_price", change)
    return len(changes)

def rollback_approved(cursor, changes, audit_callback):
    """Reverse only if no subsequent sale-price edits occurred."""
    for change in reversed(changes):
        res = cursor.execute(
            "UPDATE packages SET sale_price=? WHERE id=? AND sale_price=?",
            (change["expected_sale"], change["package_id"], change["new_sale"]))
        if res.rowcount != 1:
            raise ValueError("Price changed after approval: rollback refused")
        audit_callback("bulk_price_list_rollback", change)
    return len(changes)
