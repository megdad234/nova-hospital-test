# مراجعة الـ27 فحص غير الجاهزة في NOVA — الأدلة والخطوات المطلوبة

**تاريخ المراجعة:** 13 نوفمبر 2026. **المصدر:** فرع `feature/royallab-full-migration-20261111` من `megdad234/nova-hospital-test`، ونتيجة فحص Source Audit Run `43319015885`، وكتالوج Royal Lab الأصلي في `megdad234/Royallab-Recovery` بفرع `recovered-results`.

**الإحصاء الأخير:** 303 من أصل 330 اختباراً سريرياً قابل لإدخال النتائج قبل أي اعتماد جديد، و27 تحتاج مراجعة: 20 لا تحتوي source analytes مرتبطة، و7 تحتوي مشاكل أخرى. **العمل المكتمل هنا بحث وتصنيف وأدلة مراجعة، وليس تفعيل فحوص أو ترخيصاً طبياً.** يجب التحقق من الجهاز والكيت والمرجع الخاص بالمعمل واعتماد نموذج النتائج بواسطة مراجع مستقل. لا تُستخرج بيانات المرضى من صور التقارير.

## الحالات الـ7 التي لها أثر أصلي لكن تمنع الإدخال

| Source TestID | اسم الفحص الأصلي | الموجود فعلاً | العمل المطلوب من المصدر أو المعمل |
|---|---|---|---|
| 14 | `Ict fof malaria` | مكوّن أصلي غير نشط وصيغة مختلطة | معرفة كيت ICT الفعلي وخطوط HRP2/pLDH وتمييزه عن B.F microscopy (الذي يعرض Density وType وStage) |
| 60 | `HbA1C` | مكوّنان أصليان غير نشطين | مطابقة تعريف الجهاز/الوحدة NGSP% أو IFCC mmol/mol بالمصدر القديم؛ لا إعادة تفعيل آلي |
| 239 | `G.G.T` | مكوّن غير نشط | يمكن أن يكون نتيجة رقمية للإنزيم؛ تأكيد الأصل/الجهاز/الوحدة والمدى |
| 237 | `ALT` | مكوّن غير نشط | مثل GGT، تأكيد تعريف النتيجة العددية والوحدة |
| 263 | `CSF for C/S` | 18 مكوّناً أصلياً تاريخياً؛ اسم أحد الحقول ناقص | محاولة استرجاع الاسم من نموذج `CSF` الأصلي أو مزارع أخرى؛ تأكيد Gram stain/culture/organism/susceptibility وفق ما يجري فعلياً |
| 290 | `O 1` | صيغة قديمة غير مكتملة وحقل غير نشط | حسم ما إذا كان مكوّن O1 داخل Vibrio Cholerae Ag بدلاً من فحص مستقل |
| 310 | `Sample collection services` | حقل غير نشط | خدمة سحب عينة؛ تصنيفها خارج النتائج السريرية إن ثبت أنها غير تقريرية، من دون إنشاء نتيجة مخبرية وهمية |

## الحالات الـ20 بلا مكوّنات أصلية

| TestID | الاسم الأصلي | ما أثبته البحث أو مصدر Royal Lab | المطلوب قبل اعتماد نتيجة |
|---|---|---|---|
| 287 | Vibrio Cholerae Ag | نظير أصلّي 292، وقد يعرض O1/O139 | صورة الكيت/النموذج: هل هو RDT stool أم culture/PCR |
| 288 | O1 | غالباً جزء من اختبار كوليرا، لا إثبات أنه قابل للطلب وحده | صورة شاشة الطلب/النتيجة |
| 289 | O 139 | اسم مشابه لـ291 ويحتمل أنه مكوّن | تحديد وظيفة TestID بدقة |
| 291 | O 139 | مكرر بالاسم مع 289 | التحقق من الفرق وعدم ازدواج الفوترة |
| 320 | CBC(5 Parts) | نظير **CBC Five Differential** TestID 101 (26 مكوّناً)، غير CBC الثلاثي 21 | موديل CBC الفعلي أو صورة تقرير 5-part لتحديد WBC/RBC/HGB/PLT والمجموعات NEUT/LYM/MONO/EOS/BASO والوحدات |
| 336 | HCV | نظير أصلي 337، لكن تحته طرق مختلفة | تحديد Anti-HCV Ab vs RNA vs Genotyping؛ لا تبديل النتائج بينها |
| 339 | Hemocytine | تسمية غير موثقة، في قسم أمراض الدم الأصلي | أهم صورة مطلوبة: اسم التحليل الكامل أو التقرير أو شاشة حقوله |
| 340 | Herpes | فحص قد يكون HSV-1/2 DNA أو type-specific antibodies | تحديد العينة والطريقة؛ عدم افتراض IgM |
| 341 | ADA | مرجع موثوق لفحص ADA الكمي في pleural fluid | تأكيد نوع العينة والوحدة/الجهاز المحلي |
| 343 | Food Panel Profile | الكتالوجات العامة تقدم تشكيلات مختلفة | صورة التقرير/اسم منصة allergens/قائمة المكونات الحقيقية |
| 344 | Food Panel 2 | اختلاف كبير في تكوين Food Panel 2 بين المعامل | صورة الكيت/المكونات وعدم استيراد قائمة Mayo عشوائياً |
| 347 | ICT for typhoid | نظير Royal Lab TestID 309، **ليس Widal titre** | تحديد IgM/IgG/antigen حسب الكيت |
| 352 | Blood Sugar Curve | لا توجد توقيتات أصلية مرتبطة؛ نموذج GTT مع سكر البول أضيف **محلياً** وبشكل منفصل | توثيق توقيتات المنحنى الفعلي وجرعة التحميل؛ لا خلط الفحصين |
| 353 | Blood Fluid Analysis | توجد نماذج Body Fluid أصلية برقمَي 29 و30، لكنها غير مطابقة بالضرورة | تحديد CSF/pleural/ascitic/غيره ومكونات طلب الاختبار |
| 368 | vitamin d | نظير أصلي 316؛ مرجع Mayo يفرق 25-OH عن 1,25-D | نوع التحليل والجهاز والوحدة؛ مدى مرجعي معتمد محلياً |
| 369 | ict for dange fever | قد يحتوي NS1 أو IgM أو IgG بحسب الكيت | صورة الكاسيت أو التقرير لتحديد كل خانة |
| 378 | RPL | الاختصار غير محسوم؛ المصدر وضعه في قسم الهرمونات | أهم صورة مطلوبة: الاسم الكامل أو نموذج نتيجة، **لا تحوّله إلى RPR افتراضياً** |
| 391 | b12 | نظيران أصليان 89 و315 | نتيجة كمية Serum B12 مرشحة؛ تحقق من الجهاز والوحدة |
| 346 | Fructose Test(Qualitative) | Mayo يوثق فحص Fructose Qualitative على semen | تأكيد أنها عينة مني فعلاً وأن الحقل نوعي؛ لا تختلق خيارات كيت |
| 351 | Blood Ammonia | فحص بلازما كمي؛ النقل/التأخير قد يؤثر على النتيجة | نوع الأنبوب وطريقة النقل والجهاز والوحدة والمدى المحلي |

## نتائج البحث التي تقلل الحاجة للصور

1. **CDC (HCV):** Anti-HCV يتطلب تفسيراً مختلفاً عن HCV RNA، ومجرد إيجابية الأجسام المضادة لا تثبت العدوى الحالية. لذا لا يمكن استخدام نموذج موحد للفحصين. https://www.cdc.gov/hepatitis-c/hcp/diagnosis-testing/
2. **WHO (Malaria ICT):** أنواع RDT تختلف باختلاف HRP2 وpLDH وPf/Pan، فلا تُنسخ كثافة أو أطوار فحص الدم المجهري إلى الاختبار السريع. https://www.who.int/teams/global-malaria-programme/case-management/diagnosis/rapid-diagnostic-tests
3. **CDC (Dengue):** فحوص NS1 وIgM وRNA تختلف في دواعيها والتوقيت وقراءة النتيجة؛ على نموذج ICT أن يعكس خطوط الكاسيت المحددة. https://www.cdc.gov/dengue/hcp/diagnosis-testing/
4. **CDC (Cholera):** O1 وO139 قد يكونان نتيجتين ضمن فحص Vibrio cholerae في البراز، والتأكيد بالمزرعة أو PCR مختلف عن RDT. https://www.cdc.gov/cholera/php/laboratories/cholera-clinical-detection.html
5. **UW Medicine (CSF Culture):** تظهر العينة، Gram stain وCulture وReport Status كعناصر معملية؛ لا تصلح لاستنتاج اسم حقل Royal Lab المفقود من تلقاء نفسها. https://labmed.uw.edu/test-guide/view/CSFC
6. **Mayo (Fructose, Semen):** يوجد فعلاً فحص نوعي. النموذج المرشح مكوّن نوعي بعد إثبات العينة. https://www.mayocliniclabs.com/test-catalog/overview/92187
7. **Mayo (ADA, Pleural Fluid):** اختبار كمي؛ الوحدة والأرقام المرجعية في مختبر آخر لا تُنقل كمدى محلي. https://www.mayocliniclabs.com/test-catalog/overview/75664
8. **Mayo (Vitamin D):** 25-hydroxy يختلف عن 1,25-dihydroxy. https://www.mayocliniclabs.com/test-catalog/overview/8822
9. **Mayo (Vitamin B12):** Serum B12 assay كمي. https://www.mayocliniclabs.com/test-catalog/Overview/9154
10. **Mayo (Ammonia):** النتيجة غالباً رقمية على plasma، مع احتياج أخذ العينة ونقلها بسرعة؛ لا تُنشأ مديات من مصدر آخر. https://www.mayocliniclabs.com/test-catalog/Overview/35130
11. **Mayo / UW (Food Panels):** أسماء Food Panel 2 وFood Panel Profile غير محددة بما يكفي: بعض المختبرات تستخدم allergens مختلفة أو pooled reagent مقابل individual IgE؛ تحتاج قائمة معملنا. https://www.mayocliniclabs.com/test-catalog/overview/86207 وhttps://labmed.uw.edu/test-guide/view/LFODP
12. **CDC (Herpes):** طرق HSV NAAT وtype-specific serology مختلفة، وIgM غير موصى به لقراءة herpes genital routine. https://www.cdc.gov/std/treatment-guidelines/herpes.htm
13. **MedlinePlus (CBC Differential):** 5-part white differential: neutrophils, lymphocytes, monocytes, eosinophils, basophils، ولكن أرقام الوحدات والحقول الأخرى مصدرها جهاز المعمل. https://medlineplus.gov/lab-tests/blood-differential/
14. **NGSP (HbA1c):** % و mmol/mol تمثلان معيارين مختلفين، ويجب توثيق القياس من الجهاز. https://ngsp.org/ifcc.asp
15. **OpenELIS Global (LIS):** يفرّق بين test وresult components وselect options وnumeric limits؛ NOVA يحتوي نفس الفكرة بالفعل ولا يحتاج إعادة بناء نظام قوائم من الصفر. https://uwdigi.atlassian.net/wiki/spaces/oeg/pages/1660518401/Test%2Bcatalog%2Bimport%2Bv2%2Bfull%2Battributes%2Badmin%2Bupload%2Band%2Bthe%2Bdecision%2Bqueue

## أولويات الصور — أقل مجهود من المستخدم

**الأولوية القصوى للهوية غير المحددة:** `339 Hemocytine` و`378 RPL`. مجرد صورة لاسم الفحص الكامل أو صفحة إدخال نتيجته قد تحسم ماهيته.

**الأولوية التالية للكيت أو اللوحة الفعلية:** `343/344 Food Panels`، `336 HCV`، `340 Herpes`، `347 ICT Typhoid`، `369 Dengue ICT`، `14 Malaria ICT`، `287-291 Cholera`.

**الأولوية لعرض مخطط/جهاز:** `320 CBC 5-parts`، `352 Blood Sugar Curve`، `353 Blood Fluid Analysis`. تحتاج صور/تفاصيل لتحديد الحقول الأصلية.

**الأقل احتياجاً لصور:** `237 ALT`, `239 GGT`, `60 HbA1c`, `368 Vitamin D`, `391 B12`, `341 ADA`, `346 Fructose`, `351 Ammonia`. توجد نماذج منشورة تدعم شكل المقترح، لكن يلزم تأكيد الأجهزة ووحدات المعمل والمراجع المعتمدة.

**لا ترفع أسماء أو أرقام المرضى:** يكفي اسم الفحص، أسماء الحقول، الوحدات، خيارات الـdropdown، اسم الكيت/الجهاز، وحدود المدى المرجعي إذا كانت مدونة في النظام المعتمد.

## حماية الإنتاج

- لا أي تفعيل آلي للفحوص الـ27 أو تعديل في بيانات النتائج/الأسعار.
- المصادر الخارجية تعرّف **النوع الشائع للفحص** لا ما تم تطبيقه في Royal Lab بالفعل.
- تعديلات البحث أضافت أسئلة وروابط إلى مساعد المراجعة الموجود `hospital/royallab_missing_test_review_templates.py`. تبقى جميع النماذج اقتراحات غير قابلة للاستخدام السريري حتى المراجعة المستقلة.
- لا تغيير في NOVA Pharmacy أو الإيصالات أو مسودات المرضى القديمة.
