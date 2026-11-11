import hashlib,json,pathlib,sqlite3,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from hospital.royallab_native_catalog_store import install,install_file,list_tests,test_form
class NativeCatalogStoreTests(unittest.TestCase):
 def setUp(self):
  self.conn=sqlite3.connect(':memory:')
  self.library={'tests':[{'TestID':i,'Name':'Test '+str(i)} for i in range(367)],'analytes':[{'analyte_id':i,'test_id':i%367,'name':'Result '+str(i),'active':True,'numeric_ranges':[{'min':1,'max':10}],'result_formats':[{'id':i+1,'title':'Result '+str(i),'types':['DoubleResultFormat'],'unit':'mg/dL'}]} for i in range(1245)]}
 def tearDown(self):self.conn.close()
 def test_import_all_and_keep_ranges(self):
  cid=install(self.conn,self.library,'a'*64)
  self.assertEqual(len(list_tests(self.conn,cid)),367)
  form=test_form(self.conn,cid,'0')
  self.assertEqual(form['fields'][0]['numeric_ranges'],[{'min':1,'max':10}])
  self.assertEqual(form['fields'][0]['unit'],'mg/dL')
  self.assertEqual(install(self.conn,self.library,'a'*64),cid)
  self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM royal_lab_native_catalogs').fetchone()[0],1)
 def test_import_file(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'library.json'
   p.write_text(json.dumps(self.library),encoding='utf-8')
   cid=install_file(self.conn,p)
   self.assertEqual(len(list_tests(self.conn,cid)),367)
 def test_duplicate_id_rejected(self):
  self.library['tests'][1]['TestID']=0
  with self.assertRaisesRegex(ValueError,'duplicate'):install(self.conn,self.library,'b'*64)
if __name__=='__main__':unittest.main()
