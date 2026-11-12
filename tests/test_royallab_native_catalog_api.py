import pathlib,sqlite3,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from hospital.royallab_native_catalog_store import install
from hospital.royallab_native_catalog_api import current_catalog_id,catalog_response,form_response,validate_response,_public_form
class NativeAPI(unittest.TestCase):
 def setUp(self):
  self.conn=sqlite3.connect(':memory:')
  self.lib={'tests':[{'TestID':i,'Name':'CBC' if i==1 else 'Test '+str(i)} for i in range(367)],'analytes':[{'analyte_id':i,'test_id':1,'name':'Field','numeric_ranges':[{'low':2,'high':9}],'result_formats':[{'id':i+1,'title':'Field','types':['ColoseEndedResultFormat'] if i==0 else ['DoubleResultFormat'],'options':[{'id':10,'label':'Negative','active':True}] if i==0 else [],'unit':'g/dL','numeric_ranges':[{'low':2,'high':9}]}]} for i in range(1245)]}
 def tearDown(self):self.conn.close()
 def test_public_labels_hide_source_codes_without_mutating_source(self):
  original={'source_test_id':'ROYAL-001','name':'ROYAL-001 CBC','fields':[
   {'source_format_id':'F1','label':'ROYAL-002 WBC','kind':'select',
    'options':[{'id':'3','label':'ROYAL-003 Positive','active':True}]}]}
  public=_public_form(original)
  self.assertEqual(public['name'],'CBC')
  self.assertEqual(public['fields'][0]['label'],'WBC')
  self.assertEqual(public['fields'][0]['options'][0]['label'],'Positive')
  self.assertEqual(public['source_test_id'],'ROYAL-001')
  self.assertEqual(public['fields'][0]['source_format_id'],'F1')
  self.assertEqual(original['name'],'ROYAL-001 CBC')

 def test_no_catalog(self):
  with self.assertRaises(LookupError):catalog_response(self.conn)
 def test_search_forms_and_options(self):
  cid=install(self.conn,self.lib,'c'*64)
  self.assertEqual(current_catalog_id(self.conn),cid)
  self.assertEqual(catalog_response(self.conn)['total'],367)
  self.assertEqual(catalog_response(self.conn)['ready_for_result_entry'],1)
  self.assertFalse(catalog_response(self.conn)['tests'][0]['result_entry_ready'])
  self.assertTrue(catalog_response(self.conn,'cbc')['tests'][0]['result_entry_ready'])
  self.assertEqual(catalog_response(self.conn,'cbc')['tests'][0]['source_test_id'],'1')
  self.assertEqual(catalog_response(self.conn,'ROYAL-999')['total'],0)
  f=form_response(self.conn,1)['test']
  self.assertEqual(f['fields'][0]['options'][0]['label'],'Negative')
  self.assertEqual(f['fields'][0]['numeric_ranges'],[{'low':2,'high':9}])
  self.assertEqual(validate_response(self.conn,1,{'1':'10'})['validated_values']['1'],'10')
  with self.assertRaises(ValueError):validate_response(self.conn,1,{'1':'unknown'})
if __name__=='__main__':unittest.main()
