"""Execute ORIGINAL NOVA lab.save_values on an isolated in-memory SQLite DB."""
import ast,json,pathlib,sqlite3,sys,types,unittest,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hospital"))
from royallab_nova_save_bridge import prepare_nova_save_payload

def load_original_save():
 with zipfile.ZipFile(ROOT/"NOVA_Hospital_GitHub_Ready_Source.zip") as z:
  src=z.read("hospital/lab.py").decode("utf-8-sig")
 tree=ast.parse(src)
 fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="save_values")
 module=ast.Module(body=[fn],type_ignores=[])
 def one(c,q,args=()):
  row=c.execute(q,args).fetchone()
  return dict(row) if row else None
 def query(c,q,args=()):
  return [dict(x) for x in c.execute(q,args)]
 def to_int(v,label,minimum=1):
  x=int(v)
  if x<minimum:raise ValueError(label)
  return x
 def txt(data,key,limit,required=False):
  value=str(data.get(key) or "")
  if len(value)>limit or (required and not value):raise ValueError(key)
  return value
 def lines(c,item_id):return query(c,"SELECT * FROM hospital_lab_lines WHERE item_id=? ORDER BY id",(item_id,))
 def ensure_order_lines(c,order_id):return None
 def audit(c,*args):return None
 scope={"pharmacy":types.SimpleNamespace(one=one,query=query),"to_int":to_int,"txt":txt,
        "ensure_order_lines":ensure_order_lines,"lines":lines,"audit":audit,"now":lambda:"2026-11-11T12:00:00",
        "json":json}
 exec(compile(module,"original_nova_lab.py","exec"),scope)
 return scope["save_values"]

def fixture(status="paid"):
 c=sqlite3.connect(":memory:")
 c.row_factory=sqlite3.Row
 c.executescript("""
 CREATE TABLE hospital_orders(id INTEGER PRIMARY KEY,status TEXT);
 CREATE TABLE hospital_order_items(id INTEGER PRIMARY KEY,order_id INTEGER,result_version INTEGER,result_status TEXT,result_entered_by INTEGER,approved_at TEXT);
 CREATE TABLE hospital_lab_lines(id INTEGER PRIMARY KEY,item_id INTEGER,value TEXT,modified_at TEXT,source TEXT,code TEXT,name TEXT,unit TEXT);
 CREATE TABLE hospital_lab_revisions(id INTEGER PRIMARY KEY,item_id INTEGER,user_id INTEGER,recorded_at TEXT,before_json TEXT,after_json TEXT,reason TEXT,source TEXT,version INTEGER);
 INSERT INTO hospital_order_items VALUES(22,1,0,'draft',NULL,NULL);
 INSERT INTO hospital_lab_lines(id,item_id,value,modified_at,source,code,name,unit) VALUES(11,22,'',NULL,'manual','R1','Royal result','');
 """)
 c.execute("INSERT INTO hospital_orders VALUES(1,?)",(status,))
 c.commit()
 return c

FORM={"mode":"review_only","can_save_patient_results":False,"fields":[{"source_format_id":"r1","kind":"select","options":[{"label":"Positive"},{"label":"Negative"}]}]}
class ActualSaveTests(unittest.TestCase):
 def test_original_nova_save_draft_and_revision(self):
  c=fixture()
  try:
   payload=prepare_nova_save_payload(FORM,{"r1":"Negative"},{"r1":11},22,0)
   load_original_save()(c,{"id":7},payload)
   self.assertEqual(c.execute("SELECT value FROM hospital_lab_lines WHERE id=11").fetchone()[0],"Negative")
   self.assertEqual(c.execute("SELECT result_status,result_version FROM hospital_order_items WHERE id=22").fetchone()[:],("draft",1))
   self.assertEqual(c.execute("SELECT COUNT(*) FROM hospital_lab_revisions").fetchone()[0],1)
  finally:c.close()
 def test_original_nova_rejects_unpaid_and_stale_version(self):
  save=load_original_save()
  for status,version,exc in [("unpaid",0,PermissionError),("paid",99,ValueError)]:
   c=fixture(status)
   try:
    payload=prepare_nova_save_payload(FORM,{"r1":"Negative"},{"r1":11},22,version)
    with self.assertRaises(exc):save(c,{"id":7},payload)
    self.assertEqual(c.execute("SELECT value FROM hospital_lab_lines WHERE id=11").fetchone()[0],"")
    self.assertEqual(c.execute("SELECT COUNT(*) FROM hospital_lab_revisions").fetchone()[0],0)
   finally:c.close()
if __name__=="__main__":unittest.main()
