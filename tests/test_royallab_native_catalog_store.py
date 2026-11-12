import hashlib,json,pathlib,sqlite3,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from hospital.royallab_native_catalog_store import install,install_file,list_tests,test_form,clinical_test_form
from hospital.royallab_native_result_drafts import save_draft
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
 def test_active_fields_can_be_saved_without_deleted_source_fields(self):
  cid=install(self.conn,self.library,'d'*64)
  form=test_form(self.conn,cid,"0")
  form["review_flags"]=["inactive_source_field"]
  form["fields"][1]["active"]=False
  self.conn.execute("UPDATE royal_lab_native_tests SET form_json=? WHERE catalog_id=? AND source_test_id='0'",
                    (json.dumps(form),cid))
  active=clinical_test_form(self.conn,cid,"0")
  self.assertEqual(len(active["fields"]),len(form["fields"])-1)
  self.assertEqual(active["review_flags"],[])
  self.assertEqual(len(test_form(self.conn,cid,"0")["fields"]),len(form["fields"]))
  field=active["fields"][0]["source_format_id"]
  self.assertEqual(save_draft(self.conn,"PATIENT-LAB-1","0",{field:"7"})["values"],{field:"7"})

 def test_all_inactive_fields_stay_blocked(self):
  cid=install(self.conn,self.library,'e'*64)
  form=test_form(self.conn,cid,"0")
  form["review_flags"]=["inactive_source_field"]
  for field in form["fields"]:field["active"]=False
  self.conn.execute("UPDATE royal_lab_native_tests SET form_json=? WHERE catalog_id=? AND source_test_id='0'",
                    (json.dumps(form),cid))
  self.assertEqual(clinical_test_form(self.conn,cid,"0")["review_flags"],["inactive_source_field"])
  with self.assertRaises(ValueError):
   save_draft(self.conn,"PATIENT-LAB-1","0",{"1":"7"})
 def test_blank_order_zero_option_is_only_a_source_placeholder(self):
  cid=install(self.conn,self.library,'f'*64)
  form=test_form(self.conn,cid,"0")
  field=form["fields"][0]
  field.update({"kind":"select","types":["ColoseEndedResultFormat"],
    "options":[{"id":"EMPTY","label":" ","order":0,"active":True},
               {"id":"P","label":"Positive","order":1,"active":True}]})
  form["review_flags"]=["missing_source_option_label"]
  self.conn.execute("UPDATE royal_lab_native_tests SET form_json=? WHERE catalog_id=? AND source_test_id='0'",
                    (json.dumps(form),cid))
  effective=clinical_test_form(self.conn,cid,"0")
  self.assertEqual(effective["review_flags"],[])
  self.assertEqual(effective["excluded_blank_placeholder_options"],1)
  self.assertEqual([o["id"] for o in effective["fields"][0]["options"]],["P"])
  self.assertEqual(len(test_form(self.conn,cid,"0")["fields"][0]["options"]),2)
  self.assertEqual(save_draft(self.conn,"LAB-ORDER-1","0",{field["source_format_id"]:"P"})["status"],"draft")

 def test_unlabeled_nonzero_source_choice_is_not_a_result(self):
  cid=install(self.conn,self.library,'1'*64)
  form=test_form(self.conn,cid,"0")
  field=form["fields"][0]
  field.update({"kind":"select","types":["ColoseEndedResultFormat"],
    "options":[{"id":"UNKNOWN","label":" ","order":2,"active":True},
               {"id":"P","label":"Positive","order":1,"active":True}]})
  form["review_flags"]=["missing_source_option_label"]
  self.conn.execute("UPDATE royal_lab_native_tests SET form_json=? WHERE catalog_id=? AND source_test_id='0'",
                    (json.dumps(form),cid))
  effective=clinical_test_form(self.conn,cid,"0")
  self.assertEqual([o["id"] for o in effective["fields"][0]["options"]], ["P"])
  self.assertEqual(effective["review_flags"], [])
  self.assertEqual(save_draft(self.conn,"LAB-ORDER-1","0",
                              {field["source_format_id"]:"P"})["status"],"draft")
  with self.assertRaises(ValueError):
   save_draft(self.conn,"LAB-ORDER-1","0",{field["source_format_id"]:"UNKNOWN"})

 def test_empty_only_source_dropdown_uses_labeled_manual_draft_only(self):
  cid=install(self.conn,self.library,'2'*64)
  form=test_form(self.conn,cid,"0")
  field=form["fields"][0]
  field.update({"kind":"select","types":["ColoseEndedResultFormat"],
                "options":[{"id":"BLANK","label":" ","order":100,"active":True}]})
  form["review_flags"]=["missing_source_option_label"]
  self.conn.execute("UPDATE royal_lab_native_tests SET form_json=? WHERE catalog_id=? AND source_test_id='0'",
                    (json.dumps(form),cid))
  effective=clinical_test_form(self.conn,cid,"0")
  self.assertEqual(effective["fields"][0]["options"],[])
  self.assertEqual(effective["fields"][0]["kind"],"text")
  self.assertTrue(effective["fields"][0]["manual_missing_closed_options_draft_only"])
  self.assertEqual(save_draft(self.conn,"LAB-ORDER-1","0",
                   {field["source_format_id"]:"Clinically reviewed observation"})["status"],"draft")
  self.assertEqual(test_form(self.conn,cid,"0")["fields"][0]["kind"],"select")

 def test_blank_only_source_dropdown_without_analyte_name_stays_blocked(self):
  cid=install(self.conn,self.library,'9'*64)
  form=test_form(self.conn,cid,"0")
  field=form["fields"][0]
  field.update({"kind":"select","types":["ColoseEndedResultFormat"],"label":"",
                "options":[{"id":"BLANK","label":" ","order":100,"active":True}]})
  form["review_flags"]=["missing_source_option_label","missing_source_field_label"]
  self.conn.execute("UPDATE royal_lab_native_tests SET form_json=? WHERE catalog_id=? AND source_test_id='0'",
                    (json.dumps(form),cid))
  with self.assertRaises(ValueError):
   save_draft(self.conn,"LAB-ORDER-1","0",{field["source_format_id"]:"Not a verified name"})

 def test_original_department_only_marks_empty_service_as_non_lab(self):
  from hospital.royallab_native_catalog_store import is_non_lab_service
  self.assertTrue(is_non_lab_service({"source_department_id":"15","fields":[]}))
  self.assertFalse(is_non_lab_service({"source_department_id":"3","fields":[]}))
  self.assertFalse(is_non_lab_service({"source_department_id":"15","fields":[{"kind":"text"}]}))
  self.assertFalse(is_non_lab_service({"source_department_id":"15","fields":None}))

 def test_existing_catalog_form_upgrade_archives_old_forms_and_preserves_drafts(self):
  from hospital.royallab_native_result_drafts import SCHEMA as DRAFT_SCHEMA
  cid=install(self.conn,self.library,'8'*64)
  old_form=test_form(self.conn,cid,'0')
  old_form["fields"][0]["kind"]="text"
  self.conn.execute("UPDATE royal_lab_native_tests SET form_json=? WHERE catalog_id=? AND source_test_id='0'",
                    (json.dumps(old_form),cid))
  # Simulate a previously installed version with already-entered historical draft.
  self.conn.execute("DELETE FROM royal_lab_native_catalog_generators WHERE catalog_id=?",(cid,))
  self.conn.execute(DRAFT_SCHEMA)
  self.conn.execute("""INSERT INTO royal_lab_native_result_drafts
      (order_key,source_test_id,catalog_id,values_json) VALUES(?,?,?,?)""",
      ("ORDER-EXISTING","0",cid,json.dumps({"1":"original stored draft"})))
  self.assertEqual(install(self.conn,self.library,'8'*64),cid)
  self.assertEqual(test_form(self.conn,cid,'0')["fields"][0]["kind"],"number")
  archived=self.conn.execute("""SELECT form_json FROM royal_lab_native_catalog_form_backups
       WHERE catalog_id=? AND source_test_id='0' AND generator_version=1""",(cid,)).fetchone()
  self.assertEqual(json.loads(archived[0])["fields"][0]["kind"],"text")
  self.assertEqual(self.conn.execute(
    "SELECT values_json FROM royal_lab_native_result_drafts WHERE order_key='ORDER-EXISTING'"
  ).fetchone()[0],json.dumps({"1":"original stored draft"}))
  self.assertEqual(self.conn.execute(
    "SELECT COUNT(*) FROM royal_lab_native_catalog_form_backups WHERE catalog_id=?",(cid,)
  ).fetchone()[0],367)
  install(self.conn,self.library,'8'*64)
  self.assertEqual(self.conn.execute(
    "SELECT COUNT(*) FROM royal_lab_native_catalog_form_backups WHERE catalog_id=?",(cid,)
  ).fetchone()[0],367)

 def test_newer_installed_catalog_version_is_not_downgraded(self):
  cid=install(self.conn,self.library,'7'*64)
  self.conn.execute("UPDATE royal_lab_native_catalog_generators SET generator_version=99 WHERE catalog_id=?",(cid,))
  with self.assertRaisesRegex(ValueError,"downgrade blocked"):
   install(self.conn,self.library,'7'*64)
  self.assertEqual(self.conn.execute(
    "SELECT COUNT(*) FROM royal_lab_native_catalog_form_backups").fetchone()[0],0)

 def test_named_missing_format_can_be_manually_entered_as_draft_only(self):
  cid=install(self.conn,self.library,'3'*64)
  form=test_form(self.conn,cid,"0")
  field=form["fields"][0]
  field.update({"source_format_id":"ANALYTE-0","source_analyte_id":"0",
                "kind":"text","types":[],"label":"Microscopy note","options":[]})
  form["review_flags"]=["source_format_missing_or_incomplete_free_text_fallback"]
  self.conn.execute("UPDATE royal_lab_native_tests SET form_json=? WHERE catalog_id=? AND source_test_id='0'",
                    (json.dumps(form),cid))
  effective=clinical_test_form(self.conn,cid,"0")
  self.assertEqual(effective["review_flags"],[])
  self.assertTrue(effective["fields"][0]["manual_untyped_draft_only"])
  self.assertEqual(save_draft(self.conn,"LAB-ORDER-1","0",{"ANALYTE-0":"No organisms seen"})["status"],"draft")
  self.assertEqual(test_form(self.conn,cid,"0")["review_flags"],
                   ["source_format_missing_or_incomplete_free_text_fallback"])

 def test_unnamed_and_untyped_source_placeholder_is_not_a_result(self):
  cid=install(self.conn,self.library,'4'*64)
  form=test_form(self.conn,cid,"0")
  field=form["fields"][0]
  field.update({"source_format_id":"ANALYTE-0","source_analyte_id":"0",
                "kind":"text","types":[],"label":"","options":[]})
  form["review_flags"]=["source_format_missing_or_incomplete_free_text_fallback","missing_source_field_label"]
  self.conn.execute("UPDATE royal_lab_native_tests SET form_json=? WHERE catalog_id=? AND source_test_id='0'",
                    (json.dumps(form),cid))
  edited=clinical_test_form(self.conn,cid,"0")
  self.assertEqual(edited["review_flags"],[])
  self.assertEqual(edited["excluded_unnamed_untyped_placeholders"],1)
  self.assertNotIn("ANALYTE-0",{f["source_format_id"] for f in edited["fields"]})
  self.assertEqual(test_form(self.conn,cid,"0")["fields"][0]["source_format_id"],"ANALYTE-0")
  with self.assertRaisesRegex(ValueError,"Unknown Royal Lab result format"):
   save_draft(self.conn,"LAB-ORDER-1","0",{"ANALYTE-0":"guess"})

 def test_same_analyte_populated_dropdown_replaces_only_empty_legacy_format(self):
  cid=install(self.conn,self.library,'5'*64)
  form=test_form(self.conn,cid,"0")
  field=form["fields"][0]
  field.update({"kind":"select","types":["ColoseEndedResultFormat"],
                "options":[{"id":"P","label":"Positive","active":True}]})
  source_analyte=field["source_analyte_id"]
  form["fields"].append({"source_analyte_id":source_analyte,
      "source_format_id":"INCOMPLETE-2","kind":"text",
      "types":["ColoseEndedResultFormat"],"label":"Result",
      "active":True,"options":[]})
  form["review_flags"]=["source_format_missing_or_incomplete_free_text_fallback"]
  self.conn.execute("UPDATE royal_lab_native_tests SET form_json=? WHERE catalog_id=? AND source_test_id='0'",
                    (json.dumps(form),cid))
  resolved=clinical_test_form(self.conn,cid,"0")
  self.assertEqual(resolved["review_flags"],[])
  self.assertEqual(resolved["excluded_redundant_empty_closed_formats"],1)
  self.assertEqual(len(resolved["fields"]),len(form["fields"])-1)
  self.assertEqual(len(test_form(self.conn,cid,"0")["fields"]),len(form["fields"]))
  self.assertEqual(save_draft(self.conn,"LAB-ORDER-1","0",
                   {field["source_format_id"]:"P"})["status"],"draft")

 def test_different_analyte_cannot_supply_missing_dropdown_choices(self):
  cid=install(self.conn,self.library,'6'*64)
  form=test_form(self.conn,cid,"0")
  form["fields"][0].update({"kind":"select","types":["ColoseEndedResultFormat"],
       "options":[{"id":"P","label":"Positive","active":True}]})
  form["fields"].append({"source_analyte_id":"DIFFERENT",
      "source_format_id":"INCOMPLETE-3","kind":"text",
      "types":["ColoseEndedResultFormat"],"label":"Result",
      "active":True,"options":[]})
  form["review_flags"]=["source_format_missing_or_incomplete_free_text_fallback"]
  self.conn.execute("UPDATE royal_lab_native_tests SET form_json=? WHERE catalog_id=? AND source_test_id='0'",
                    (json.dumps(form),cid))
  resolved=clinical_test_form(self.conn,cid,"0")
  self.assertEqual(resolved["excluded_redundant_empty_closed_formats"],0)
  unresolved=next(f for f in resolved["fields"] if f["source_analyte_id"]=="DIFFERENT")
  self.assertEqual(unresolved["kind"],"text")
  self.assertEqual(unresolved["options"],[])
  self.assertTrue(unresolved["manual_missing_closed_options_draft_only"])
  self.assertEqual(save_draft(self.conn,"LAB-ORDER-1","0",
                 {"INCOMPLETE-3":"manual observation"})["status"],"draft")

 def test_optionless_named_closed_source_can_only_be_manually_drafted(self):
  cid=install(self.conn,self.library,'9'*64)
  form=test_form(self.conn,cid,"0")
  field=form["fields"][0]
  field.update({"kind":"text","types":["ColoseEndedResultFormat"],
    "label":"Pleural fluid observation","options":[]})
  form["review_flags"]=["source_format_missing_or_incomplete_free_text_fallback"]
  self.conn.execute("UPDATE royal_lab_native_tests SET form_json=? WHERE catalog_id=? AND source_test_id='0'",
                    (json.dumps(form),cid))
  reviewed=clinical_test_form(self.conn,cid,"0")
  self.assertEqual(reviewed["review_flags"],[])
  self.assertEqual(reviewed["manual_missing_closed_options_draft_fields"],1)
  self.assertTrue(reviewed["fields"][0]["manual_missing_closed_options_draft_only"])
  self.assertEqual(save_draft(self.conn,"LAB-ORDER-1","0",
      {field["source_format_id"]:"manual observation"})["status"],"draft")
  self.assertEqual(test_form(self.conn,cid,"0")["review_flags"],
                   ["source_format_missing_or_incomplete_free_text_fallback"])

 def test_empty_closed_source_label_cannot_be_auto_reconstructed(self):
  cid=install(self.conn,self.library,'a'*64)
  form=test_form(self.conn,cid,"0")
  field=form["fields"][0]
  field.update({"kind":"text","types":["ColoseEndedResultFormat"],
    "label":"-","options":[]})
  form["review_flags"]=["source_format_missing_or_incomplete_free_text_fallback"]
  self.conn.execute("UPDATE royal_lab_native_tests SET form_json=? WHERE catalog_id=? AND source_test_id='0'",
                    (json.dumps(form),cid))
  self.assertIn("source_format_missing_or_incomplete_free_text_fallback",
                clinical_test_form(self.conn,cid,"0")["review_flags"])
  with self.assertRaises(ValueError):
   save_draft(self.conn,"LAB-ORDER-1","0",{field["source_format_id"]:"invented"})

 def test_duplicate_id_rejected(self):
  self.library['tests'][1]['TestID']=0
  with self.assertRaisesRegex(ValueError,'duplicate'):install(self.conn,self.library,'b'*64)
if __name__=='__main__':unittest.main()
