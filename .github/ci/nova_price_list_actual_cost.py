"""NOVA: read actual last purchase cost across suppliers, converted to target pack.

No price-list upload may create a purchase, move stock or overwrite historical cost.
"""
from decimal import Decimal, ROUND_HALF_UP

def actual_last_cost(c, package_id):
    target=c.execute("SELECT product_id,factor FROM packages WHERE id=?",(package_id,)).fetchone()
    if target is None: raise ValueError("Unknown target package")
    product_id,factor=int(target[0]),int(target[1])
    if factor<=0:raise ValueError("Invalid target pack factor")
    # Sort by recorded purchase line (not by supplier or price-list upload).
    # qty+bonus is received sellable packages; total amount is the recorded purchase cost.
    records=c.execute("""
        SELECT pl.id,pl.qty,pl.bonus,pl.amount,pk.factor
        FROM purchase_lines pl
        JOIN packages pk ON pk.id=pl.package_id
        WHERE pk.product_id=?
        ORDER BY pl.id DESC
    """,(product_id,)).fetchall()
    for record in records:
        line_id,qty,bonus,amount,source_factor=map(int,record)
        units=(qty+bonus)*source_factor
        if units<=0 or amount<0:continue
        converted=(Decimal(amount)*Decimal(factor)/Decimal(units)).quantize(Decimal("1"),rounding=ROUND_HALF_UP)
        return {"purchase_line_id":line_id,"unit_purchase_cost":int(converted),"source_factor":source_factor,"target_factor":factor}
    return None
