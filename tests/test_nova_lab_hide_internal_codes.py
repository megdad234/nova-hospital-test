"""Prevent ROYAL-<source ID> from appearing in the staff lab picker."""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.github/ci/nova_lab_hide_internal_codes.py'
SPEC = importlib.util.spec_from_file_location('nova_lab_hide_internal_codes', SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LabPickerPresentationTests(unittest.TestCase):
    def setUp(self):
        self.original = '''function orderedTestsList(){return `<div class="quick-tests">${state.tests.filter(t=>t.popular).map(t=>`<button type="button" class="quick-test ${state.selected.has(t.id)?'selected':''}" data-pick="${t.id}"><strong>${esc(t.code)}</strong><small>${esc(t.name)}</small></button>`).join('')}</div><label>Search</label><div id="test-options">${testChoices()}</div>`}
function searchTest(t,search){const s=search.trim().toLowerCase();return !s||`${t.name} ${t.code} ${t.aliases}`.toLowerCase().includes(s)}
function testChoices(){const list=state.tests.filter(t=>searchTest(t,state.filter)&&(!state.labCategory||t.category===state.labCategory));return `<div class="checks">${list.slice(0,60).map(t=>`<label class="test-choice"><input type="checkbox" data-pickcheck="${t.id}" ${state.selected.has(t.id)?'checked':''}><span><b>${esc(t.code)}</b> ${esc(t.name)} <small>${money(t.price)}</small></span></label>`).join('')}</div>`}'''

    def test_both_quick_and_checkbox_cards_show_name_only(self):
        js = MODULE.hide_codes_in_lab_picker(self.original)
        self.assertNotIn('${esc(t.code)}', js)
        self.assertIn(MODULE.QUICK_AFTER, js)
        self.assertIn(MODULE.CHECK_AFTER, js)
        self.assertIn('data-pick="${t.id}"', js)
        self.assertIn('data-pickcheck="${t.id}"', js)
        self.assertIn('${money(t.price)}', js)
        self.assertIn('${t.name} ${t.code} ${t.aliases}', js)
        self.assertIn('state.selected.has(t.id)', js)
        self.assertEqual(MODULE.hide_codes_in_lab_picker(js), js)

    def test_unknown_html_is_rejected_instead_of_failing_silently(self):
        corrupted=self.original.replace(MODULE.CHECK_BEFORE,'unknown html')
        with self.assertRaisesRegex(RuntimeError,'checkbox test cards'):
            MODULE.hide_codes_in_lab_picker(corrupted)

    def test_search_and_internal_code_must_not_be_removed(self):
        bad=self.original.replace('${t.name} ${t.code} ${t.aliases}',
                                  '${t.name} ${t.aliases}')
        with self.assertRaisesRegex(RuntimeError,'model code for search'):
            MODULE.hide_codes_in_lab_picker(bad)

    def test_other_clinical_workflows_unchanged(self):
        original=self.original+'\\nconst clinicalForm = getPatientResults();\\nconst pharmacyReceipt = printPharmacy();'
        js=MODULE.hide_codes_in_lab_picker(original)
        self.assertIn('const clinicalForm = getPatientResults();',js)
        self.assertIn('const pharmacyReceipt = printPharmacy();',js)


if __name__ == '__main__':
    unittest.main()
