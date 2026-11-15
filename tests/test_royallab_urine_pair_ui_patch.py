"""Verify original NOVA renderer retains independent urine source result IDs."""
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github/ci"))
from royallab_typed_input_patch import patch as typed_patch
from royallab_urine_pair_ui_patch import patch as urine_patch


class UrinePairRenderTests(unittest.TestCase):
    def _patched_renderer(self):
        batch = (ROOT / ".github/ci/nova_batch04_lab_reception.py").read_text(
            encoding="utf-8")
        start = batch.index("function novaLabGroupedRows(lines,editable)")
        end = batch.index('""")', start)
        original = batch[start:end]
        return original, urine_patch(typed_patch(original))

    def test_verified_source_inputs_remain_separate_and_no_other_test_changes(self):
        original, after = self._patched_renderer()
        self.assertIn("function novaUrinePairedRows(rows,editable)", after)
        self.assertEqual(after.count("novaUrinePairedRows(rows,editable)"), 2)
        self.assertEqual(after.count("function novaLabGroupedRows(lines,editable)"), 1)
        self.assertIn("royalLabInput(x)", after)
        self.assertIn("data-line=", after)
        with self.assertRaises(ValueError):
            urine_patch(after)
        self.assertNotEqual(original, after)

    def test_node_executes_both_inputs_once_per_pair_and_preserves_fallback(self):
        _, source = self._patched_renderer()
        # Execute source independently: no browser, database or patient information.
        script = """function esc(v){return String(v??'');}\n""" + source + r"""
const lines = [
 {id:1,code:'ROYAL_FMT_297',name:'Crystals (Type)',value:'Oxalate',unit:'',reference_range:''},
 {id:2,code:'ROYAL_FMT_727',name:'Crystals (Grade)',value:'(++)',unit:'',reference_range:''},
 {id:3,code:'ROYAL_FMT_745',name:'Cast (Type)',value:'Nil',unit:'',reference_range:''},
 {id:4,code:'ROYAL_FMT_746',name:'Cast (Grade)',value:'(+)',unit:'',reference_range:''},
 {id:5,code:'ROYAL_FMT_555',name:'Others (Grade)',value:'Few',unit:'',reference_range:''},
 {id:6,code:'ROYAL_FMT_409',name:'Others (Additional Notes)',value:'Test',unit:'',reference_range:''}
];
const result=novaUrinePairedRows(lines,true);
if((result.match(/<tr>/g)||[]).length!==3)throw Error('urine should display three paired rows');
for(const l of lines){
 const re=new RegExp('data-line="'+l.id+'"','g');
 if((result.match(re)||[]).length!==1)throw Error('missing or repeated result input '+l.id);
}
if(!result.includes('Crystals')||!result.includes('Cast')||!result.includes('Others'))
 throw Error('group labels missing');
const separate=novaUrinePairedRows([
 {id:7,code:'OTHER',name:'Other test',value:'abc',unit:'',reference_range:''}
],true);
if(!separate.includes('data-line="7"')||separate.includes('nova-urine-pair'))
 throw Error('non-urine test renderer changed');
const partial=novaUrinePairedRows(lines.slice(0,2),true);
if((partial.match(/<tr>/g)||[]).length!==2)
 throw Error('partial/unsupported panel must retain separate source fields');
const readonly=novaUrinePairedRows(lines,false);
if(readonly.includes('data-line=')||readonly.includes('<input'))
 throw Error('read-only result must not expose input controls');
"""
        with tempfile.TemporaryDirectory() as td:
            source_path = pathlib.Path(td) / "urine-render.js"
            source_path.write_text(script, encoding="utf-8")
            for args in (["node", "--check", str(source_path)],
                         ["node", str(source_path)]):
                result = subprocess.run(args, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
