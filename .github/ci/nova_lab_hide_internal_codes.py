"""Presentation-only NOVA laboratory test-picker fix.

The original app.js renders internal test code (ROYAL-275, etc.) on quick
buttons and checkbox cards. Keep the code in the database/search/selection
model; remove only its DOM interpolation in the lab ordering UI.

Called by Windows builder after all other hospital UI/print patches.
"""
from pathlib import Path

QUICK_BEFORE = '<strong>${esc(t.code)}</strong><small>${esc(t.name)}</small>'
QUICK_AFTER = '<strong>${esc(t.name)}</strong>'
CHECK_BEFORE = '<span><b>${esc(t.code)}</b> ${esc(t.name)} <small>${money(t.price)}</small></span>'
CHECK_AFTER = '<span><b>${esc(t.name)}</b> <small>${money(t.price)}</small></span>'


def hide_codes_in_lab_picker(js: str) -> str:
    original = js
    for before, after, label in (
        (QUICK_BEFORE, QUICK_AFTER, 'popular quick-test buttons'),
        (CHECK_BEFORE, CHECK_AFTER, 'search / checkbox test cards'),
    ):
        if js.count(before) == 1:
            js = js.replace(before, after, 1)
        elif js.count(before) == 0 and js.count(after) == 1:
            pass  # idempotent for an already patched source
        else:
            raise RuntimeError(f'Unexpected {label} markup; refuse unsafe changes')

    for name, token in (
        ('quick-test picker', 'data-pick="${t.id}"'),
        ('checkbox picker', 'data-pickcheck="${t.id}"'),
        ('model code for search', '${t.name} ${t.code} ${t.aliases}'),
    ):
        if token not in js:
            raise RuntimeError(f'{name} lost while hiding visible codes')
    # The ONLY code interpolation in the original lab card renderers is removed.
    for token in (QUICK_BEFORE, CHECK_BEFORE):
        if token in js:
            raise RuntimeError('A lab test card still renders its internal code')
    if js == original and (QUICK_AFTER not in js or CHECK_AFTER not in js):
        raise RuntimeError('Unrecognized laboratory renderer')
    return js


def main():
    path = Path('hospital/static/app.js')
    source = path.read_text(encoding='utf-8')
    revised = hide_codes_in_lab_picker(source)
    path.write_text(revised, encoding='utf-8')
    print('NOVA_LAB_INTERNAL_CODES_HIDDEN_FROM_BOTH_PICKERS')
    print('NOVA_LAB_IDS_CODES_PRICES_AND_SEARCH_PRESERVED')


if __name__ == '__main__':
    main()
