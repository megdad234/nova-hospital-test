# -*- coding: utf-8 -*-
"""Synthetic HTTP regression for NOVA beneficiary insurance (zero live data)."""
import unittest
from tests.test_hospital_gateway import HospitalServerFixture

class BeneficiaryInsuranceAcceptance(HospitalServerFixture,unittest.TestCase):
    def test_relationship_rates_and_old_invoice_immutability(self):
        admin=self.admin
        rec=self.make_user("reception","batch06Rec")
        insurer=admin.post("/api/hospital/insurer",{"name":"Synthetic Family Coverage","default_coverage":70})
        iid=insurer["id"]
        pat=rec.post("/api/hospital/patients",{"full_name":"Synthetic Child Patient"})
        pid=pat["id"]
        svc=next(x for x in admin.get("/api/hospital/services") if x["code"]=="CONS-GP")
        admin.post("/api/hospital/service",{"id":svc["id"],"code":svc["code"],
            "category_code":svc["category_code"],"name":svc["name"],"price":10000})
        key=svc["key"]
        # Parent linked beneficiary, default insurer coverage without custom rates.
        rec.post("/api/hospital/patient-insurance",{"patient_id":pid,"insurer_id":iid,
            "member_no":"SYN-CHILD-01","beneficiary_type":"child"})
        profile=rec.get("/api/hospital/patient-insurance/"+str(pid))
        self.assertEqual(profile["beneficiary_type"],"child")
        q=rec.post("/api/hospital/invoice-quote",{"patient_id":pid,"services":[key],"insurer_id":iid})
        self.assertEqual(q["insurer_due"],7000)
        admin.post("/api/hospital/nova-beneficiary-rate",
            {"insurer_id":iid,"beneficiary_type":"child","coverage":80})
        self.assertTrue(any(r["coverage"]==80 for r in admin.get("/api/hospital/nova-beneficiary-rates")))
        q=rec.post("/api/hospital/invoice-quote",{"patient_id":pid,"services":[key],"insurer_id":iid})
        self.assertEqual(q["patient_due"],2000)
        self.assertEqual(q["beneficiary_type"],"child")
        inv=rec.post("/api/hospital/invoices",{"patient_id":pid,"services":[key],"insurer_id":iid})
        snapshot=admin.get("/api/hospital/invoice/"+str(inv["id"]))
        self.assertEqual(snapshot["beneficiary_type"],"child")
        self.assertEqual(snapshot["lines"][0]["coverage"],80)
        self.assertEqual(snapshot["insurer_due"],8000)
        # Admin changes future rate; existing invoice must retain original snapshot.
        admin.post("/api/hospital/nova-beneficiary-rate",
            {"insurer_id":iid,"beneficiary_type":"child","coverage":85})
        self.assertEqual(admin.get("/api/hospital/invoice/"+str(inv["id"]))["insurer_due"],8000)
        self.assertEqual(rec.post("/api/hospital/invoice-quote",
            {"patient_id":pid,"services":[key],"insurer_id":iid})["insurer_due"],8500)
        # Service-specific coverage overrides child relationship.
        admin.post("/api/hospital/insurance-rate",
            {"insurer_id":iid,"service_key":key,"category_code":"","coverage":50})
        self.assertEqual(rec.post("/api/hospital/invoice-quote",
            {"patient_id":pid,"services":[key],"insurer_id":iid})["insurer_due"],5000)
        # Clearing the override reverts to the relationship rate.
        admin.post("/api/hospital/nova-beneficiary-rate",
            {"insurer_id":iid,"beneficiary_type":"child","inherit":True})
        self.assertEqual(rec.post("/api/hospital/invoice-quote",
            {"patient_id":pid,"services":[key],"insurer_id":iid})["insurer_due"],5000)
        # A different service with no overrides would use the 70% default.

    def test_admin_only_configuration_and_invalid_beneficiary(self):
        admin=self.admin
        rec=self.make_user("reception","batch06NoAdmin")
        insurer=admin.post("/api/hospital/insurer",{"name":"Synthetic Strict Insurer","default_coverage":60})
        iid=insurer["id"]
        # Standard request client raises on permission denial.
        with self.assertRaises(Exception) as forbidden:
            rec.post("/api/hospital/nova-beneficiary-rate",
                {"insurer_id":iid,"beneficiary_type":"child","coverage":99})
        self.assertIn("403",str(forbidden.exception))
        with self.assertRaises(Exception) as forbidden:
            rec.get("/api/hospital/nova-beneficiary-rates")
        self.assertIn("403",str(forbidden.exception))
        pat=rec.post("/api/hospital/patients",{"full_name":"Synthetic Relationship Invalid"})
        with self.assertRaises(Exception) as rejected:
            rec.post("/api/hospital/patient-insurance",
                {"patient_id":pat["id"],"insurer_id":iid,"beneficiary_type":"unknown"})
        self.assertIn("400",str(rejected.exception))
        admin.post("/api/hospital/nova-beneficiary-rate",
            {"insurer_id":iid,"beneficiary_type":"father","coverage":0})
        rates=admin.get("/api/hospital/nova-beneficiary-rates")
        self.assertTrue(any(x["insurer_id"]==iid and x["beneficiary_type"]=="father" and x["coverage"]==0 for x in rates))

if __name__=="__main__":
    unittest.main(verbosity=2)
