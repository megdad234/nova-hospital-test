# NOVA / Royal Lab — original-source 20 no-analyte tests: verified review decisions

Date: 2026-11-13. Audit source: NOVA feature branch read-only source audit, run 43319015885, audited source tests 367, analytes 1,245.

**Scope:** 20 clinical tests with no linked source analytes and 7 other blocked tests. These numbers are **runtime** figures (303 ready, 27 blocked, 37 non-laboratory services), not the older source staging flags. This file documents review questions and open guidance; **it does not declare clinical activation**.

## Why not fill automatically from open-source screenshots

OpenELIS/Bahmni supports coded, numeric and text results, as NOVA now does. It does not establish which precise local analyzer, kit, reagent, sample protocol or reporting units the specific Royal Lab site used. Internet screenshots can guide layouts but cannot safely reconstruct a missing clinical source identity, unit, sex/age interval or exact RDT cassette result meanings. Never import external defaults as if they were Royal Lab original source definitions.

## Exact 20 names/IDs and next evidence

| Royal source TestID | Original name | Method-specific action before approval |
|---|---|---|
| 287 | Vibrio Cholerae Ag | Determine stool RDT vs culture/PCR, kit brand and specific O1/O139 reporting targets |
| 288 | O1 | Determine whether this was a sub-component of source 287; do not create independent chargeable test without proof |
| 289 | O 139 | Check source structure, O139 target and duplication against ID 291 |
| 291 | O 139 | Separate same-named source row; identify purpose and original method |
| 320 | CBC(5 Parts) | Use the local 5-differential analyzer parameter list; candidate WBC/RBC/Hb/HCT/PLT and five-cell differential only pending verified machine output |
| 336 | HCV | Identify antibody vs viral RNA; do not equate screening with current infection |
| 339 | Hemocytine | Unclear original spelling; keep blocked until original laboratory naming/method is identified |
| 340 | Herpes | Identify HSV I/II antigen, serology or PCR, plus specimen/method |
| 341 | ADA | Identify pleural/body fluid vs other, quantitative method and units |
| 343 | Food Panel Profile | Determine actual allergen-reagent panel contents; do not make up food choices |
| 344 | Food Panel 2 | Determine actual different panel composition vs ID 343 |
| 347 | ICT for typhoid | Identify kit target (IgM, IgG, both or other), document poor performance limitations |
| 352 | Blood Sugar Curve | Document locally ordered time points; avoid generic automatic 0/1/2/3-hour fields |
| 353 | Blood Fluid Analysis | Specify fluid type and its distinct analysis panel |
| 368 | vitamin d | Establish 25-OH vs 1,25-dihydroxyvitamin D; unit and normal range are assay-specific |
| 369 | ict for dange fever | Establish NS1 vs IgM/IgG cassette design and result interpretation |
| 378 | RPL | Ambiguous abbreviation; cannot define patient result fields until exact lab test identity known |
| 391 | b12 | Quantitative serum B12 is a candidate; analyzer and unit to be documented locally |
| 346 | Fructose Test(Qualitative) | Potential qualitative semen fructose; must confirm specimen and procedure |
| 351 | Blood Ammonia | Quantitative ammonia is a candidate; confirm specimen handling, unit, method |

**Do not assume 20 will become active from literature alone.** The code exposes advisory method-specific questions in the existing Arabic in-NOVA review screen, while leaving choices, normal limits and clinical approvals unfilled until verified.

## The other seven (not source-empty)

- `14` ICT for malaria: inactive source field and mixed format, check actual kit/archived format.
- `60` HbA1C: source fields deactivated despite historical result-column evidence; no automatic reactivation.
- `239` G.G.T and `237` ALT: source fields inactive, require documented active assay review.
- `263` CSF for C/S: source field label missing among 23 fields; use exact source format identity or authorized lab review, not guessed label.
- `290` O 1: original incomplete result format and inactive field; check O1 relationship to cholera parent.
- `310` Sample collection services: operational sample service rather than typical reportable assay; check source departmental classification and do not force clinical result fields merely to reduce the blocked count.

## Evidence references used for method-identification suggestions

1. OpenELIS/Bahmni test concept and coded/numeric/text setup: https://bahmni.atlassian.net/wiki/spaces/BAH/pages/109314082/Configure+Laboratory+Management+System
2. CDC HCV screening versus NAT: https://www.cdc.gov/hepatitis-c/hcp/diagnosis-testing/
3. WHO dengue laboratory testing (2025): https://www.who.int/publications/i/item/B09394
4. CDC cholera clinical detection and serogroup O1/O139: https://www.cdc.gov/cholera/php/laboratories/cholera-clinical-detection.html
5. CDC typhoid diagnostic testing limitations: https://www.cdc.gov/yellow-book/hcp/travel-associated-infections-diseases/typhoid-and-paratyphoid-fever.html
6. MedlinePlus CBC and differential overview: https://medlineplus.gov/lab-tests/blood-differential/
7. Mayo ADA, pleural-fluid method: https://www.mayocliniclabs.com/test-catalog/overview/75664
8. Mayo differential vitamin D assays: https://www.mayocliniclabs.com/test-catalog/overview/8822
9. Mayo Vitamin B12 assay: https://www.mayocliniclabs.com/test-catalog/Overview/800083
10. Mayo qualitative semen fructose: https://www.mayocliniclabs.com/test-catalog/overview/92187
11. CLSI EP28 reference interval verification: https://clsi.org/shop/standards/ep28/

## Engineering outcome

New local-test form management is implemented in `hospital/nova_lab_local_tests.py`, uses existing NOVA lab test/parameter IDs, and requires independent laboratory form approval before activation. Source-derived repair remains in `hospital/royallab_clinical_template_review.py`. No Royal Lab source IDs are overwritten; no patient results or old Royal Lab prices are imported. For laboratory orders already recorded, local form edits are frozen to prevent changing historical results. The existing pharmacy and printing contracts remain untouched.
