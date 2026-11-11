import pathlib,sys,unittest,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.github/ci'))
from royallab_typed_input_patch import patch
class TypedPatchTests(unittest.TestCase):
 def test_batch04_grouped_renderer_uses_typed_input_not_literal(self):
  batch=(ROOT/'.github/ci/nova_batch04_lab_reception.py').read_text(encoding='utf-8')
  start=batch.index('function novaLabGroupedRows(lines,editable)')
  end=batch.index('""")',start)
  fragment=batch[start:end]
  result=patch(fragment)
  self.assertIn("editable?royalLabInput(x):",result)
  self.assertNotIn("editable?'royalLabInput(x)'",result)
  self.assertIn("function novaLabGroupedRows(lines,editable)",result)
  with self.assertRaises(ValueError):patch(result)
 def test_original_save_logic_preserved_and_typed_widget_added(self):
  with zipfile.ZipFile(ROOT/'NOVA_Hospital_GitHub_Ready_Source.zip') as z:
   original=z.read('hospital/static/app.js').decode('utf-8-sig')
  result=patch(original)
  self.assertIn('function royalLabInput(x)',result)
  self.assertIn('royalLabInput(x)',result)
  self.assertIn("await api('lab/values',{item_id:",result)
  self.assertEqual(result.count("await api('lab/values',{item_id:"),original.count("await api('lab/values',{item_id:"))
  self.assertIn("if(!m||",result)
  self.assertIn("data-line=",result)
  with self.assertRaises(ValueError):patch(result)
if __name__=='__main__':unittest.main()
