import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from hospital.royallab_native_result_form import native_catalog,native_test_form,validate_result_values
class NativeForms(unittest.TestCase):
 def setUp(self):
  self.library={'tests':[{'TestID':i,'Name':'Test '+str(i)} for i in range(367)],'analytes':[{'analyte_id':i,'test_id':0,'name':'Field '+str(i),'active':True,'result_formats':[{'id':i+1,'title':'Field '+str(i),'types':['ColoseEndedResultFormat'] if i==0 else ['DoubleResultFormat'],'options':[{'id':1,'label':'Positive','active':True,'order':1}] if i==0 else [],'unit':''}]} for i in range(1245)]}
 def test_native_catalog_does_not_need_old_nova(self):
  cat=native_catalog(self.library)
  self.assertEqual(cat['test_count'],367)
  self.assertFalse(cat['uses_old_nova_test_matching'])
  form=native_test_form(cat,0)
  self.assertEqual(len(form['fields']),1245)
  self.assertEqual(form['fields'][0]['kind'],'select')
  self.assertEqual(form['fields'][1]['kind'],'number')
 def test_select_is_closed_and_numeric_is_numeric(self):
  form=native_test_form(native_catalog(self.library),0)
  self.assertEqual(validate_result_values(form,{'1':1,'2':'2.5'}),{'1':'1','2':'2.5'})
  with self.assertRaisesRegex(ValueError,'listed source option'):validate_result_values(form,{'1':999})
  with self.assertRaisesRegex(ValueError,'numeric'):validate_result_values(form,{'2':'abc'})
  with self.assertRaisesRegex(ValueError,'Unknown Royal'):validate_result_values(form,{'99999':'x'})
 def test_inactive_and_malformed_fields_rejected(self):
  form={"fields":[{"source_format_id":"A","kind":"text","active":False}]}
  with self.assertRaisesRegex(ValueError,"Inactive"):validate_result_values(form,{"A":"result"})
  with self.assertRaisesRegex(ValueError,"Invalid source field"):validate_result_values({"fields":[None]},{"A":"result"})
 def test_nonfinite_text_float_rejected(self):
  form={"fields":[{"source_format_id":"A","kind":"text","active":True}]}
  with self.assertRaisesRegex(ValueError,"Non-finite"):validate_result_values(form,{"A":float("nan")})
  with self.assertRaisesRegex(ValueError,"Non-finite"):validate_result_values(form,{"A":float("inf")})
 def test_unknown_test_is_rejected(self):
  with self.assertRaisesRegex(ValueError,'Unknown'):native_test_form(native_catalog(self.library),'not-exists')
if __name__=='__main__':unittest.main()
