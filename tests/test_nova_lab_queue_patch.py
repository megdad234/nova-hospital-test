"""NOVA lab queue patch safety and original order/detail/print preservation."""
import pathlib
import subprocess
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/".github"/"ci"))
from nova_lab_queue_patch import (
    patch_app,patch_gateway,patch_style,LAB_WIRE_PATTERN,
    GATEWAY_IMPORT,GATEWAY_ANCHOR,
)


def lab_original_wiring():
    return ("if(section==='lab'){const render=()=>{$('lab-queue').innerHTML="
        "orderRows(state.orders.filter(x=>['paid','completed'].includes(x.status))"
        ".filter(x=>String(x.patient_name + ' ' + x.patient_no + ' ' + x.order_no)"
        ".toLowerCase().includes(val('lab-search').toLowerCase())));"
        "document.querySelectorAll('[data-order]').forEach(b=>"
        "b.addEventListener('click',()=>openDetails(Number(b.dataset.order))))};"
        "$('lab-search')?.addEventListener('input',render);"
        "$('lab-refresh')?.addEventListener('click',()=>navigate('lab'))}")


class TestQueueUIPatches(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper=(ROOT/"hospital/static/nova_lab_queue_ui.js").read_text(
            encoding="utf-8")

    def test_surgical_original_lab_event_wiring(self):
        self.assertEqual(len(LAB_WIRE_PATTERN.findall(lab_original_wiring())),1)
        old = ("function viewLab(){return 'legacy queue';}\n"
               "function openDetails(id){return id;}\n"
               "function printReport(id){return 'UNMODIFIED_PRINT';}\n"
               "function wireSection(section){"+lab_original_wiring()+"}\n")
        revised=patch_app(old,self.helper)
        self.assertIn("function viewLab(){return novaLabQueueView();}",revised)
        self.assertIn("if(section==='lab'){novaLabQueueWire();}",revised)
        self.assertNotIn("lab-search",revised)
        self.assertIn("function printReport(id){return 'UNMODIFIED_PRINT';}",revised)
        self.assertIn("function openDetails(id){return id;}",revised)
        with self.assertRaises(ValueError):
            patch_app(revised,self.helper)
        with self.assertRaises(ValueError):
            patch_app(old.replace("function printReport","function other"),self.helper)
        with self.assertRaises(ValueError):
            patch_app(old.replace("lab-search","changed-lab-search"),self.helper)

    def test_original_orders_and_role_guard_left_untouched(self):
        original=GATEWAY_IMPORT+", royallab_nova_live_order_overlay\n"+(
            "def get(self,path,c,role):\n"+GATEWAY_ANCHOR+"\n")
        revised=patch_gateway(original)
        self.assertEqual(revised.count(GATEWAY_ANCHOR),1)
        self.assertIn("core.orders(c,role)",revised)
        self.assertIn("core.require_role(role,'admin','lab')",revised)
        self.assertIn("if path=='/api/hospital/lab/queue':",revised)
        self.assertIn("nova_lab_queue_search.search_queue(",revised)
        self.assertIn("date_from=arg('from')",revised)
        with self.assertRaises(ValueError):
            patch_gateway(revised)
        with self.assertRaises(ValueError):
            patch_gateway(original.replace("core.orders(c,role)","other(c,role)"))

    def test_styles_only_touch_lab_queue_selectors(self):
        updated=patch_style("body{margin:0}\n")
        self.assertIn(".nova-lab-toolbar",updated)
        self.assertIn("body{margin:0}",updated)
        self.assertNotIn("@media print",updated)
        self.assertNotIn(".pharmacy",updated)
        with self.assertRaises(ValueError):
            patch_style(updated)

    def test_ui_is_valid_javascript_without_legacy_200_record_filter(self):
        result=subprocess.run(["node","--check",
             str(ROOT/"hospital/static/nova_lab_queue_ui.js")],
             capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("lab/queue?",self.helper)
        self.assertIn("function novaLabQueueWire()",self.helper)
        self.assertIn("function novaLabQueueLoad()",self.helper)
        self.assertIn("function novaLabQueueRows(rows)",self.helper)
        self.assertIn("data-order=",self.helper)
        self.assertIn("openDetails(Number(button.dataset.order))",self.helper)
        self.assertIn("older_unfinished",self.helper)
        self.assertIn("tests_preview",self.helper)
        self.assertIn("aria-live",self.helper)
        self.assertNotIn("state.orders.filter(",self.helper)
        self.assertNotIn("printReport(",self.helper)
        self.assertNotIn("save_values(",self.helper)
        self.assertNotIn("lab/values",self.helper)

    def test_builder_keeps_source_files_until_post_ui_patch(self):
        build=(ROOT/".github/workflows/nova_build.yml").read_text(
            encoding="utf-8")
        self.assertIn("nova_lab_hide_internal_codes.py",build)
        if "python .github/ci/nova_lab_queue_patch.py" in build:
            self.assertGreater(build.index("python .github/ci/nova_lab_queue_patch.py"),
                               build.index("python .github/ci/nova_lab_hide_internal_codes.py"))


if __name__=="__main__":
    unittest.main()
