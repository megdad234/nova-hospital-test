"""Remove the original NOVA 200-test response cap after Royal Lab migration.

The existing hospital/lab.py catalog() fetches ALL active tests and applies
the requested filter, then discards everything beyond row 200. Admin lab
pricing and patient test pickers receive that truncated JSON and their LOCAL
search cannot find later tests such as Vitamin D / VDRL (TestIDs 316/59).

Patch ONLY the five-line catalog() function, preserving sorting, active-only
filter, popular-only search, term matching, IDs/prices, and all other routes.
No database mutation, pharmacy, print or billing logic change.
"""
from pathlib import Path

OLD = """def catalog(c, search='', only_popular=False):
    rows=pharmacy.query(c,'SELECT * FROM hospital_lab_tests WHERE active=1 ORDER BY popular DESC,name')
    if only_popular:rows=[x for x in rows if x['popular']]
    term=search.strip().casefold()[:80]
    if term:rows=[x for x in rows if term in (x['code']+' '+x['name']+' '+x['aliases']).casefold()]
    return rows[:200]
"""
NEW = """def catalog(c, search='', only_popular=False):
    # NOVA_ROYALLAB_CATALOG_ALL_ACTIVE: 367 Royal Lab source tests plus
    # independently approved local tests; filtering is performed BEFORE any
    # UI display-page cap. Never discard tests at the API boundary.
    rows=pharmacy.query(c,'SELECT * FROM hospital_lab_tests WHERE active=1 ORDER BY popular DESC,name')
    if only_popular:rows=[x for x in rows if x['popular']]
    term=search.strip().casefold()[:80]
    if term:rows=[x for x in rows if term in (x['code']+' '+x['name']+' '+x['aliases']).casefold()]
    return rows
"""


def patch(source):
    if not isinstance(source, str):
        raise TypeError("NOVA laboratory module source must be text")
    if "NOVA_ROYALLAB_CATALOG_ALL_ACTIVE" in source:
        raise ValueError("Full-catalog visibility already patched")
    if source.count(OLD) != 1:
        raise ValueError("Original NOVA laboratory catalog search changed; no unsafe patch")
    return source.replace(OLD, NEW, 1)


def apply(root):
    path = Path(root) / "hospital" / "lab.py"
    path.write_text(patch(path.read_text(encoding="utf-8-sig")),
                    encoding="utf-8")
    return path


if __name__ == "__main__":
    apply(Path(__file__).resolve().parents[2])
