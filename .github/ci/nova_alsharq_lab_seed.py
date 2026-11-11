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
    "\nPOPULAR = ",
    "\n# NOVA_MALARIA_TEMPLATE_V2: full microscopy entry on fresh installations.\n"
    "for _idx,_test in enumerate(TESTS):\n"
    "    if _test[0] == 'MALARIA':\n"
    "        _existing_codes = {p[0] for p in _test[4]}\n"
    "        _additional = [p for p in " + repr(LAB_STRUCTURED_NEW["MALARIA"]) + " if p[0] not in _existing_codes]\n"
    "        TESTS[_idx] = (*_test[:4], list(_test[4]) + _additional, *_test[5:])\n"
    "        break\n"
    "\nPOPULAR = ",
    1
)
# GTT is a structured catalogue option on new installs, without a default price.
if "GTT" not in existing:
    extra.append(("GTT", "Glucose Tolerance Test", "Chemistry", "glucose tolerance test", LAB_STRUCTURED_NEW["GTT"]))
    existing.add("GTT")
# Additional commonly requested tests absent from the initial price list.
# Only add missing codes; leave price at zero pending local pricing approval.
# Do not invent clinical reference intervals or patient results.
COMMON_EXTRA_TESTS = [
 ("HIV_RAPID","HIV Rapid Screening","Serology",[("RESULT","Screening result","","","","")]),
 ("HCV_RAPID","HCV Antibody Rapid Screening","Serology",[("RESULT","Screening result","","","","")]),
 ("HBSAG_RAPID","HBsAg Rapid Screening","Serology",[("RESULT","Screening result","","","","")]),
 ("VDRL","VDRL Screening","Serology",[("RESULT","Screening result","","","","")]),
 ("RPR","RPR Screening","Serology",[("RESULT","Screening result","","","","")]),
 ("MALARIA_RDT","Malaria Rapid Diagnostic Test","Parasitology",[("RESULT","Rapid test result","","","","")]),
 ("STOOL_OCCULT","Stool Occult Blood","Parasitology",[("RESULT","Occult blood result","","","","")]),
 ("ESR","Erythrocyte Sedimentation Rate","Hematology",[("ESR","ESR","mm/hr","","","")]),
 ("RETIC","Reticulocyte Count","Hematology",[("RETIC","Reticulocyte count","%","","","")]),
 ("BLOOD_GROUP","ABO and Rh Blood Group","Blood Bank",[("ABO","ABO group","","","",""),("RH","Rh(D)","","","","")]),
 ("CROSSMATCH","Blood Crossmatch","Blood Bank",[("RESULT","Compatibility result","","","",""),("COMMENTS","Comments","","","","")]),
 ("URINE_CULTURE","Urine Culture","Microbiology",[("GROWTH","Culture growth","","","",""),("ORGANISM","Organism","","","",""),("SENSITIVITY","Susceptibility / comments","","","","")]),
 ("STOOL_CULTURE","Stool Culture","Microbiology",[("GROWTH","Culture growth","","","",""),("ORGANISM","Organism","","","",""),("SENSITIVITY","Susceptibility / comments","","","","")]),
 ("BLOOD_CULTURE","Blood Culture","Microbiology",[("GROWTH","Culture growth","","","",""),("ORGANISM","Organism","","","",""),("SENSITIVITY","Susceptibility / comments","","","","")]),
 ("URINE_PREG","Urine Pregnancy Test","Serology",[("RESULT","Pregnancy test result","","","","")]),
]
for code,name,category,params in COMMON_EXTRA_TESTS:
    if code not in existing:
        extra.append((code,name,category,name.lower(),params))
        existing.add(code)
anchor="\nPOPULAR = "
assert anchor in catalog
catalog=catalog.replace(anchor,"\n# AL_SHARQ_LAB_SEED_V1 — new test definitions; no invented clinical intervals.\nTESTS.extend("+repr(extra)+")\n"+anchor,1)
# NOVA_LAB_STRUCTURED_CATALOG_V1: named analytes for existing composite assays.
# Use field identities, not fabricated patient results or clinical reference intervals.
# The source catalogue remains the authority for test codes and pricing.
STRUCTURED_FIELDS = {
    # OpenELIS-style multi-component microbiology results: growth, organism,
    # susceptibility and narrative remain separate; no automatic interpretation.
    **{_culture: [("GROWTH", "Culture growth"),
                   ("ORGANISM", "Isolated organism"),
                   ("SENS", "Antimicrobial susceptibility / antibiogram"),
                   ("COMMENTS", "Culture comments")]
       for _culture in ("CULTURE","URINE_CULT","STOOL_CULT","BLOOD_CULT")},
    **{_culture: [("GROWTH", "Culture growth"),
                   ("ORGANISM", "Isolated organism"),
                   ("SENSITIVITY", "Antimicrobial susceptibility / antibiogram"),
                   ("COMMENTS", "Culture comments")]
       for _culture in ("URINE_CULTURE","STOOL_CULTURE","BLOOD_CULTURE")},
    "WIDAL": [("O", "Salmonella Typhi O"), ("H", "Salmonella Typhi H")],
    "MAL_RDT": [("RDT", "Malaria Rapid Test")],
    "BGROUP": [("ABO", "ABO group"), ("RH", "Rh(D)")],
    "PTINR": [("PT", "Prothrombin Time"), ("INR", "INR")],
    "BTCT": [("BT", "Bleeding Time"), ("CT", "Clotting Time")],
    "NA_K": [("NA", "Sodium"), ("K", "Potassium")],
    "LFT_E": [("ALT", "ALT (SGPT)"), ("AST", "AST (SGOT)"),
              ("ALP", "Alkaline Phosphatase"), ("TBIL", "Total Bilirubin"),
              ("DBIL", "Direct Bilirubin"), ("ALBUMIN", "Albumin"),
              ("TOTAL_PROTEIN", "Total Protein"), ("NA", "Sodium"),
              ("K", "Potassium"), ("CL", "Chloride")],
    "IRON_FULL": [("IRON", "Serum Iron"), ("TIBC", "Total Iron Binding Capacity"),
                  ("TRANSFERRIN_SAT", "Transferrin Saturation"), ("FERRITIN", "Ferritin")],
    "PT_PTT": [("PT", "Prothrombin Time"), ("INR", "INR"),
               ("APTT", "Activated Partial Thromboplastin Time")],
    "SEMEN": [("VOLUME", "Volume"), ("APPEARANCE", "Appearance"),
              ("LIQUEFACTION", "Liquefaction"), ("VISCOSITY", "Viscosity"),
              ("PH", "pH"), ("CONCENTRATION", "Sperm Concentration"),
              ("TOTAL_COUNT", "Total Sperm Count"), ("PROGRESSIVE", "Progressive Motility"),
              ("NONPROGRESSIVE", "Non-progressive Motility"), ("IMMOTILE", "Immotile"),
              ("MORPHOLOGY", "Normal Morphology"), ("VITALITY", "Vitality"),
              ("WBC", "Round Cells / WBC"), ("COMMENTS", "Comments")],
    "DENGUE": [("NS1", "Dengue NS1 Antigen"), ("IGM", "Dengue IgM"),
               ("IGG", "Dengue IgG")],
    "FERTILITY": [("FSH", "FSH"), ("LH", "LH"), ("PROLACTIN", "Prolactin"),
                  ("ESTRADIOL", "Estradiol"), ("PROGESTERONE", "Progesterone"),
                  ("TESTOSTERONE", "Testosterone")],
    "BRUCELLA": [("RESULT", "Brucella screening result"), ("TITER", "Titer (if performed)")],
    "HBS_ELISA": [("RESULT", "HBsAg ELISA result"), ("INDEX", "Index / S-CO (if reported)")],
    "AMYLASE": [("AMYLASE", "Amylase")],
    "AMH": [("AMH", "Anti-Mullerian Hormone")],
    "INSULIN": [("INSULIN", "Insulin")],
    "C_PEPTIDE": [("C_PEPTIDE", "C-Peptide")],
    "PTH": [("PTH", "Parathyroid Hormone")],
    "ACCP": [("ACCP", "Anti-CCP Antibody")],
    "TROPONIN_Q": [("TROPONIN", "Troponin (quantitative)")],
    "AFP": [("AFP", "Alpha-Fetoprotein")],
    "SG": [("RESULT", "Sickling test result")],
    "ICT_TYPHOID": [("RESULT", "Typhoid ICT result")],
    "HP_STOOL": [("RESULT", "H. pylori stool antigen result")],
    "HP_SERUM": [("RESULT", "H. pylori serum antibody result")],
    "HCG": [("RESULT", "Pregnancy test result")],
    "STOOL_OCCULT": [("RESULT", "Occult blood result")],
    "URINE_PREG": [("RESULT", "Pregnancy test result")],
    "MALARIA_RDT": [("RESULT", "Malaria RDT result")],
}
# Single-analyte and qualitative panels are intentionally kept simple.
# Some names (MAT, U S&A, Troponin Q) do not establish a method;
# never infer assay-specific thresholds or reference values from the name.
# Build an explicit replacement after all new catalogue tests are appended.
catalog = catalog.replace(
    "\nPOPULAR = ",
    "\n# NOVA_LAB_STRUCTURED_CATALOG_V1\n"
    "for _idx, _test in enumerate(TESTS):\n"
    "    _map = " + repr(STRUCTURED_FIELDS) + ".get(_test[0])\n"
    "    if _map is not None:\n"
    "        _old = {str(p[0]): p for p in _test[4]}\n"
    "        _params = []\n"
    "        for code, label in _map:\n"
    "            _prior = _old.get(code)\n"
    "            _params.append((code, label, *_prior[2:]) if _prior is not None else (code, label, '', '', '', ''))\n"
    "        TESTS[_idx] = (*_test[:4], _params, *_test[5:])\n"
    "\nPOPULAR = ", 1
)
C.write_text(catalog,encoding="utf-8")
# NOVA_LAB_FULL_CATALOGUE_GATE_V1: validate the ACTUAL generated catalogue
# after all 47 price-list entries, extras and structured fields are applied.
# This gate runs in the seed phase, never against the original 58-test ZIP.
import importlib.util
import csv
_spec=importlib.util.spec_from_file_location("nova_lab_catalog_seed_validation",C)
_mod=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
_all_tests=list(_mod.TESTS)
_codes=[str(t[0]) for t in _all_tests]
assert len(_codes)==97, f"Expected 97 complete tests after seed, got {len(_codes)}"
assert len(set(_codes))==97, "Duplicate test codes after seed"
assert all(t[4] for t in _all_tests), "Test without any result parameters"
assert all(len({str(p[0]) for p in t[4]})==len(t[4]) for t in _all_tests), "Duplicate analytes"
for _code in ("NA_K","LFT_E","IRON_FULL","PT_PTT","SEMEN","DENGUE","FERTILITY"):
    _panel=next(t for t in _all_tests if t[0]==_code)
    assert not (len(_panel[4])==1 and _panel[4][0][0]=="RESULT"), _code
# A single consolidated review queue: avoid pretending every field is clinically
# finalized just because its renderer is editable. This is a data audit, not
# a patient-result test, and does not alter the installed database.
_review_rows=[]
for _test in _all_tests:
    _code,_name=_test[0],_test[1]
    _fields=_test[4]
    if len(_fields)==1 and str(_fields[0][0])=="RESULT":
        _review_rows.append((_code,_name,"generic_result","Define assay-specific choices or measurements from validated method"))
    for _field in _fields:
        if len(_field)<6:
            _review_rows.append((_code,_name,"incomplete_field_metadata",str(_field[0])))
with Path("lab_catalogue_clinical_review_queue.csv").open("w",encoding="utf-8-sig",newline="") as _review_file:
    _review_writer=csv.writer(_review_file)
    _review_writer.writerow(("test_code","test_name","issue","required_action"))
    _review_writer.writerows(_review_rows)
print("NOVA_LAB_CLINICAL_REVIEW_QUEUE",len(_review_rows),"items")
with Path("lab_all_97_field_mapping.csv").open("w",encoding="utf-8-sig",newline="") as _fh:
    _writer=csv.writer(_fh)
    _writer.writerow(("test_code","test_name","category","field_code","field_name","unit","reference_range"))
    for _test in _all_tests:
        for _field in _test[4]:
            _writer.writerow((_test[0],_test[1],_test[2],_field[0],_field[1],_field[2],_field[3]))
print("NOVA_LAB_FULL_CATALOGUE_GATE_OK",len(_all_tests),
      "tests",sum(len(t[4]) for t in _all_tests),"analytes")

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
# Run the complete 97-assay UI field regression AFTER the catalogue is seeded.
# Previously this test ran only before seeding and silently skipped the full audit.
import subprocess
import sys
print("NOVA_POST_SEED_FULL_FIELD_REGRESSION_START",flush=True)
subprocess.run([sys.executable, ".github/ci/test_nova_lab_print_isolation.py"], check=True)
print("NOVA_POST_SEED_FULL_FIELD_REGRESSION_PASS",flush=True)

