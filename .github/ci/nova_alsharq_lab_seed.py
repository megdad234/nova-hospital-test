"""Al Sharq laboratory catalogue seed for NEW installations only.

Does not change prices in an existing database, invoice snapshots, or clinical ranges.
Ambiguous panels are distinct entries, never aliases of individual tests.
"""
from pathlib import Path
import ast

P=Path("hospital/lab.py")
C=Path("hospital/lab_catalog.py")
source=P.read_text(encoding="utf-8")
catalog=C.read_text(encoding="utf-8")
if "AL_SHARQ_LAB_SEED_V1" in source:
    print("Al Sharq seed already applied")
    raise SystemExit(0)

# PDF prices in SDG. Only exact clinically reviewed catalogue mappings are reused.
# Format: source PDF code, existing NOVA code, price, English display, category.
ROWS=[
("CBC","CBC",15000,"Complete Blood Count","Hematology"),
("ESR","ESR",10000,"ESR","Hematology"),
("BFFM","MALARIA",8000,"Blood Film for Malaria","Parasitology"),
("SG","SG",8000,"Sickling Test","Hematology"),
("URINE","URINE",8000,"Urine General","Urinalysis"),
("US&A","USA",5000,"U S&A","Urinalysis"),
("STOOL","STOOL",8000,"Stool General","Parasitology"),
("WIDAL","WIDAL",10000,"Widal Test","Serology"),
("MAT","MAT",10000,"MAT","Serology"),
("BRUCELLA","BRUCELLA",15000,"Brucella","Serology"),
("ICT_TYPHOID","ICT_TYPHOID",15000,"ICT Typhoid","Serology"),
("DENGUE","DENGUE",25000,"Dengue fever AG/AB","Serology"),
("HP_STOOL","HP_STOOL",15000,"Stool H.Pylori","Serology"),
("HP_SERUM","HP_SERUM",15000,"Serum H.Pylori","Serology"),

("HBS_ELISA","HBS_ELISA",83000,"ELISA for HBsAg","Serology"),
("RBG","RBS",8000,"Random Blood Glucose","Chemistry"),
("RFT","RFT",20000,"Renal Function Tests","Chemistry"),
("NA_K","NA_K",20000,"Sodium & Potassium","Chemistry"),
("CA","CALCIUM",15000,"Calcium","Chemistry"),
("PH","PHOS",20000,"Phosphorus","Chemistry"),
("MG","MG",20000,"Magnesium","Chemistry"),
("LFT_E","LFT_E",75000,"LFT + Electrolytes","Chemistry"),
("LIPID","LIPID",60000,"Lipid Profile","Chemistry"),
("URIC","URIC",15000,"Uric Acid","Chemistry"),
("AMYLASE","AMYLASE",50000,"Amylase","Chemistry"),
("HBA1C","HBA1C",30000,"HbA1c","Chemistry"),
("IRON_FULL","IRON_FULL",80000,"Iron - Full test","Chemistry"),
("TFT","TFT",85000,"Thyroid Function Tests","Hormones"),
("AMH","AMH",50000,"AMH","Hormones"),
("INSULIN","INSULIN",50000,"Insulin","Hormones"),
("C_PEPTIDE","C_PEPTIDE",50000,"C-Peptide","Hormones"),
("FERTILITY","FERTILITY",120000,"Fertility Profile","Hormones"),
("BHCG","BHCG",50000,"Beta-hCG Quantitative","Hormones"),
("HCG","HCG",10000,"Pregnancy Test","Serology"),
("VIT_D","VITD",70000,"Vitamin D","Chemistry"),
("VIT_B12","B12",70000,"Vitamin B12","Chemistry"),
("PTH","PTH",80000,"PTH","Hormones"),
("PSA","PSA",70000,"PSA","Tumor markers"),
("CRP_Q","CRP",30000,"CRP Quantitative","Immunology"),
("ASO_Q","ASO",50000,"ASO Quantitative","Immunology"),
("RF","RF",15000,"Rheumatoid Factor","Immunology"),
("ACCP","ACCP",80000,"Anti-CCP","Immunology"),
("PT_PTT","PT_PTT",30000,"PT & PTT (15,000 per unit)","Coagulation"),
("TROPONIN_Q","TROPONIN_Q",60000,"Troponin Q","Cardiac"),
("D_DIMER","D_DIMER",60000,"D-Dimer","Coagulation"),
("AFP","AFP",80000,"AFP","Tumor markers"),
("SEMEN","SEMEN",30000,"Semen Analysis","Andrology"),
]
assert len(ROWS)==47 and len({x[0] for x in ROWS})==47
# These are conservative exact mappings; the uncertain names stay distinct.
# HIV/B/C/VDRL group excluded from auto-seed: 15,000 SDG is per unit, not package.
# Other ambiguous tests have independent codes, with no fabricated medical reference ranges.
tree=ast.parse(catalog)
existing={item.elts[0].value for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="TESTS" for t in node.targets) for item in node.value.elts}
# Structured entry for new installations; no clinical reference ranges or inferred diagnoses.
# Existing catalogue definitions and already installed databases remain untouched.
LAB_STRUCTURED_NEW = {
    "MALARIA": [
        ("DENSITY", "Malaria Density", "", "", "", ""),
        ("TYPE", "Malaria Type", "", "", "", ""),
        ("STAGE", "Malaria Stage", "", "", "", ""),
        ("PARASITE", "B.F. for Malaria", "", "", "", ""),
        ("COMMENTS", "Microscopy comments", "", "", "", ""),
    ],
    "GTT": [
        ("FASTING", "Fasting glucose (0 min)", "mg/dL", "", "", ""),
        ("TIME_30", "Glucose at 30 min (if ordered)", "mg/dL", "", "", ""),
        ("TIME_60", "Glucose at 60 min (if ordered)", "mg/dL", "", "", ""),
        ("TIME_120", "Glucose at 120 min (if ordered)", "mg/dL", "", "", ""),
        ("TIME_180", "Glucose at 180 min (if ordered)", "mg/dL", "", "", ""),
        ("COMMENTS", "Comments / protocol", "", "", "", ""),
    ],
}
extra=[]
for src,code,price,name,category in ROWS:
    if code not in existing:
        extra.append((code,name,category,src.lower().replace("_"," "),LAB_STRUCTURED_NEW.get(code,[("RESULT","Result","","","","")])))
        existing.add(code)
# Expand the existing malaria test definition as well: the original catalogue
# contains MALARIA with only MP, so a missing-code-only seed never upgraded it.
# Keep MP as the first field for backwards compatibility with existing results.
# Do not invent reference ranges, units or positive patient findings.
catalog=catalog.replace(
    "\\nPOPULAR = ",
    "\\n# NOVA_MALARIA_TEMPLATE_V2: full microscopy entry on fresh installations.\\n"
    "for _idx,_test in enumerate(TESTS):\\n"
    "    if _test[0] == 'MALARIA':\\n"
    "        _existing_codes = {p[0] for p in _test[4]}\\n"
    "        _additional = [p for p in " + repr(LAB_STRUCTURED_NEW["MALARIA"]) + " if p[0] not in _existing_codes]\\n"
    "        TESTS[_idx] = (*_test[:4], list(_test[4]) + _additional, *_test[5:])\\n"
    "        break\\n"
    "\\nPOPULAR = ",
    1
)
# GTT is a structured catalogue option on new installs, without a default price.
if "GTT" not in existing:
    extra.append(("GTT", "Glucose Tolerance Test", "Chemistry", "glucose tolerance test", LAB_STRUCTURED_NEW["GTT"]))
    existing.add("GTT")
anchor="\nPOPULAR = "
assert anchor in catalog
catalog=catalog.replace(anchor,"\n# AL_SHARQ_LAB_SEED_V1 — new test definitions; no invented clinical intervals.\nTESTS.extend("+repr(extra)+")\n"+anchor,1)
C.write_text(catalog,encoding="utf-8")
# Insertion happens only when the test code is not present. Never touch a locally edited price.
prices={code:price for _,code,price,_,_ in ROWS}
needle="                  (code,name,0,category,aliases,int(code in lab_catalog.POPULAR))).lastrowid"
assert source.count(needle)==1, "Unexpected lab insert shape"
source=source.replace(needle,"                  (code,name,AL_SHARQ_LAB_SEED_V1.get(code,0),category,aliases,int(code in lab_catalog.POPULAR))).lastrowid")
pos="DEFAULT_BRAND = "
assert pos in source
source=source.replace(pos,"# AL_SHARQ_LAB_SEED_V1: applies to first-time catalogue rows only.\nAL_SHARQ_LAB_SEED_V1 = "+repr(prices)+"\n\n"+pos,1)
P.write_text(source,encoding="utf-8")
# Original regression test assumed all brand-new lab prices are zero.
# After intentional Al Sharq preload, CBC must be priced at 15,000 SDG.
T=Path("tests/test_lab_complete.py")
if T.exists():
    test=T.read_text(encoding="utf-8")
    old="self.assertEqual(cbc['price'],0)"
    assert test.count(old)==1, "Unexpected CBC price assertion; review before changing tests"
    T.write_text(test.replace(old,"self.assertEqual(cbc['price'],15000)"),encoding="utf-8")
print("Al Sharq seed prepared:",len(ROWS),"prices;",len(extra),"new definitions")
