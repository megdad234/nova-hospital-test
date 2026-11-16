"""NOVA lab read-only queue: all-history dates, patient/test search and safety."""
import sqlite3
import unittest
from datetime import date

from hospital.nova_lab_queue_search import search_queue

TODAY = date(2026, 11, 16)


class TestNOVAQueueSearch(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.executescript("""
        CREATE TABLE hospital_patients(
            id INTEGER PRIMARY KEY, patient_no TEXT, full_name TEXT);
        CREATE TABLE hospital_orders(
            id INTEGER PRIMARY KEY, patient_id INTEGER, order_no TEXT,
            created_at TEXT, status TEXT, total INTEGER);
        CREATE TABLE hospital_order_items(
            id INTEGER PRIMARY KEY, order_id INTEGER,
            test_name TEXT, result_status TEXT);
        INSERT INTO hospital_patients VALUES(1,'2041','أحمد محمد');
        INSERT INTO hospital_patients VALUES(2,'2042','عائشة الطيب');
        """)
        for i in range(1, 248):
            status = "paid" if i < 246 else ("pending" if i==246 else "cancelled")
            if i==1:status="completed"
            dt="2026-11-15" if i<=230 else "2026-11-16"
            patient=2 if i in (245,246) else 1
            name="Vitamin D" if i==245 else ("VDRL" if i==230 else "CBC")
            self.db.execute("""INSERT INTO hospital_orders VALUES
                (?,?,?,?,?,?)""",(i,patient,"LAB-%06d"%i,
                                 dt+"T12:00:00",status,i*100))
            result = "approved" if i==1 or i==245 else (
                "draft" if i==3 else "pending")
            self.db.execute("""INSERT INTO hospital_order_items VALUES
                (?,?,?,?)""",(i*10,i,name,result))
            if i==2:
                self.db.execute("""INSERT INTO hospital_order_items VALUES
                    (?,?,?,?)""",(i*10+1,i,"Urine General Analysis","approved"))
        self.db.commit()
        self.original_changes=self.db.total_changes

    def tearDown(self):
        self.db.close()

    def query(self,**kwargs):
        return search_queue(self.db,role="lab",current_day=TODAY,**kwargs)

    def test_default_today_and_paid_only(self):
        x=self.query()
        self.assertEqual(x["total"],15)
        self.assertEqual(x["period"],"today")
        self.assertEqual(x["summary"]["total"],15)
        self.assertEqual(x["older_unfinished"],229)
        self.assertTrue(all(v["status"] in ("paid","completed") for v in x["items"]))
        self.assertTrue(all(v["created_at"].startswith("2026-11-16")
                            for v in x["items"]))
        self.assertEqual(self.db.total_changes,self.original_changes)

    def test_whole_history_not_silently_cut_at_200(self):
        x=self.query(period="all")
        self.assertEqual(x["total"],245)
        self.assertEqual(x["pages"],10)
        self.assertEqual(len(x["items"]),25)
        self.assertEqual(x["items"][0]["id"],245)
        self.assertEqual(x["items"][0]["tests_preview"],"Vitamin D")
        second=self.query(period="all",page=2)
        self.assertEqual(len(second["items"]),25)
        self.assertTrue(set(v["id"] for v in x["items"]).isdisjoint(
            v["id"] for v in second["items"]))
        last=self.query(period="all",page=999)
        self.assertEqual(last["page"],10)
        self.assertEqual(len(last["items"]),20)
        oldest=self.query(period="all",sort="oldest")
        self.assertEqual(oldest["items"][0]["id"],1)

    def test_search_all_history_by_patient_file_order_and_test(self):
        for q,expected in [
            ("Vitamin D",245),("2042",245),("عائشة",245),
            ("LAB-000245",245),("VDRL",230),("lab-000230",230),
            ("Urine General",2),
        ]:
            with self.subTest(q=q):
                x=self.query(q=q,period="all")
                self.assertEqual(x["total"],1)
                self.assertEqual(x["items"][0]["id"],expected)
        # This search must not see unpaid patient 246.
        self.assertEqual(self.query(period="all",q="LAB-000246")["total"],0)
        self.assertEqual(self.db.total_changes,self.original_changes)

    def test_date_ranges_states_and_backlog_count_are_independent(self):
        self.assertEqual(self.query(period="yesterday")["total"],230)
        self.assertEqual(self.query(period="week")["total"],245)
        self.assertEqual(self.query(period="custom",
                  date_from="2026-11-15",date_to="2026-11-15")["total"],230)
        self.assertEqual(self.query(period="all",status="completed")["total"],2)
        self.assertEqual(self.query(period="all",status="partial")["total"],1)
        self.assertEqual(self.query(period="all",status="draft")["total"],1)
        self.assertEqual(self.query(period="all",status="waiting")["total"],241)
        self.assertEqual(self.query(period="all",status="unfinished")["total"],243)
        x=self.query(status="completed",q="Vitamin D")
        self.assertEqual(x["total"],1)
        self.assertEqual(x["older_unfinished"],229)
        self.assertEqual(x["summary"]["completed"],1)

    def test_literal_like_wildcards_do_not_expand_search(self):
        self.assertEqual(self.query(period="all",q="%")["total"],0)
        self.assertEqual(self.query(period="all",q="_")["total"],0)
        self.assertEqual(self.query(period="all",q="\\")["total"],0)

    def test_role_and_input_guards_before_query(self):
        for role in ("cashier","reception","frontdesk",None):
            with self.subTest(role=role),self.assertRaises(PermissionError):
                search_queue(self.db,role=role,period="all",current_day=TODAY)
        bad=[
            {"period":"month"},
            {"status":"paid"},
            {"sort":"random"},
            {"page":"-2"},
            {"page":"1 OR 1=1"},
            {"page_size":"0"},
            {"page_size":"999"},
            {"period":"custom","date_from":"2026-02-30","date_to":"2026-11-16"},
            {"period":"custom","date_from":"2026-12-01","date_to":"2026-11-16"},
            {"q":"X"*121},
        ]
        for item in bad:
            with self.subTest(item=item),self.assertRaises(ValueError):
                self.query(**item)
        self.assertEqual(self.db.total_changes,self.original_changes)

    def test_page_is_bounded_and_continuation_has_real_global_counts(self):
        x=self.query(period="all",page_size=50,page=5)
        self.assertEqual(x["total"],245)
        self.assertEqual(x["pages"],5)
        self.assertEqual(len(x["items"]),45)
        self.assertEqual(x["summary"]["total"],245)
        self.assertEqual(x["summary"]["completed"],2)
        self.assertEqual(x["summary"]["partial"],1)
        self.assertEqual(x["summary"]["drafts"],1)
        self.assertEqual(x["summary"]["unfinished"],243)
        self.assertEqual(self.db.total_changes,self.original_changes)


if __name__=="__main__":
    unittest.main()
