/* Royal Lab replacement catalogue UI, independent of legacy NOVA test names.
   Mount on an authenticated lab container; the existing gateway enforces roles.
   No printing, pharmacy or cashier code is modified. */
(function (global) {
  'use strict';
  function safeText(value) { return String(value == null ? '' : value); }
  // Source identifiers remain internal for binding only; never display them to staff.
  function displayText(value) { return safeText(value).replace(/\bROYAL[\s_-]*\d+\b/gi, '').replace(/\s{2,}/g, ' ').trim(); }
  function createRoyalLabPicker(root, apiBase) {
    if (!root || typeof root.appendChild !== 'function') throw new Error('Lab container required');
    const base = apiBase || '/api/hospital/royallab-native';
    root.replaceChildren();
    const search = document.createElement('input');
    search.type = 'search';
    search.placeholder = 'ابحث عن فحص بالاسم';
    search.setAttribute('aria-label', 'بحث فحوصات المعمل');
    const picker = document.createElement('select');
    picker.setAttribute('aria-label', 'فحوصات المعمل');
    const detail = document.createElement('section');
    detail.dir = 'rtl';
    const status = document.createElement('p');
    status.setAttribute('role', 'status');
    root.dir = 'rtl';
    root.append(search, picker, status, detail);
    const orderItem = document.createElement('input');
    orderItem.type = 'number';
    orderItem.min = '1';
    orderItem.placeholder = 'رقم بند طلب المعمل';
    orderItem.setAttribute('aria-label', 'رقم بند طلب المعمل');
    const saveButton = document.createElement('button');
    saveButton.type = 'button';
    saveButton.textContent = 'حفظ مسودة النتيجة';
    saveButton.disabled = true;
    let formReady = false;
    let saving = false;
    root.append(orderItem, saveButton);
    async function send(path, payload) {
      const response = await fetch(base + path, {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!response.ok) throw new Error('تعذر حفظ مسودة المعمل؛ تحقق من الصلاحية وحالة الدفع');
      return response.json();
    }
    async function saveSelectedDraft() {
      if (!formReady || saving) throw new Error('الفحص غير جاهز لحفظ النتائج');
      const selectedTest = picker.value;
      const selectedSerial = requestSerial;
      const itemId = Number(orderItem.value);
      if (!Number.isSafeInteger(itemId) || itemId <= 0 || !picker.value)
        throw new Error('اختر الفحص وأدخل رقم بند طلب صحيح');
      const values = {};
      for (const control of detail.querySelectorAll('[data-source-format-id]')) {
        const id = control.dataset.sourceFormatId;
        if (!id || id === 'null') continue;
        const alternative = Array.from(detail.querySelectorAll('[data-alternative-for]'))
          .find(function (x) { return x.dataset.alternativeFor === id; });
        values[id] = alternative && alternative.value.trim() !== '' ?
          alternative.value.trim() : control.value;
      }
      await send('/order/attach', { nova_item_id: itemId, source_test_id: selectedTest });
      if (selectedSerial !== requestSerial || picker.value !== selectedTest)
        throw new Error('تغير الفحص أثناء الحفظ؛ أعد فتح الفحص وتحقق من النتائج');
      await send('/order/draft', { nova_item_id: itemId, values: values });
      if (selectedSerial === requestSerial) status.textContent = 'تم حفظ مسودة النتائج، ولم يتم اعتمادها أو نشرها';
    }
    saveButton.addEventListener('click', function () {
      if (!formReady || saving) return;
      saving = true;
      saveButton.disabled = true;
      saveSelectedDraft().catch(function (error) {
        status.textContent = safeText(error.message);
      }).finally(function () {
        saving = false;
        saveButton.disabled = !formReady;
      });
    });
    let tests = [];
    let requestSerial = 0;
    let loadSerial = 0;
    function filter() {
      ++requestSerial; // Discard a previously requested form when search changes.
      const q = search.value.trim().toLocaleLowerCase();
      picker.replaceChildren();
      const empty = document.createElement('option');
      empty.value = '';
      empty.textContent = '— اختر الفحص —';
      picker.appendChild(empty);
      for (const test of tests) {
        if (!displayText(test.name).toLocaleLowerCase().includes(q)) continue;
        const option = document.createElement('option');
        option.value = safeText(test.source_test_id);
        option.disabled = test.result_entry_ready === false;
        const suffix = test.entry_status === 'non_lab_service' ? ' — خدمة غير معملية' : ' — يحتاج مراجعة';
        option.textContent = displayText(test.name) + (option.disabled ? suffix : '');
        picker.appendChild(option);
      }
      detail.replaceChildren();
      formReady = false;
      saveButton.disabled = true;
    }
    // In-app repair of source-incomplete forms. This panel is separate from
    // ordinary result entry, and never stores a patient result or approves one.
    // The gateway authenticates lab staff and requires a different admin for
    // second-person activation. Every clinical choice starts empty.
    const reviewPanel = document.createElement('details');
    reviewPanel.className = 'royal-lab-clinical-review';
    reviewPanel.dir = 'rtl';
    const reviewHeading = document.createElement('summary');
    reviewHeading.textContent = 'إصلاح نماذج الفحوصات الناقصة (يتطلب مراجعة مستقلة)';
    const reviewBody = document.createElement('section');
    const reviewStatus = document.createElement('p');
    reviewStatus.setAttribute('role', 'status');
    const reviewSelect = document.createElement('select');
    reviewSelect.setAttribute('aria-label', 'الفحص الذي يحتاج نموذج نتائج');
    const proposalFields = document.createElement('div');
    const addFieldButton = document.createElement('button');
    addFieldButton.type = 'button';
    addFieldButton.textContent = 'إضافة حقل نتيجة';
    const suggestButton = document.createElement('button');
    suggestButton.type = 'button';
    suggestButton.textContent = 'تعبئة الحقول من المصدر أو مقترح المراجعة';
    const methodInput = document.createElement('textarea');
    methodInput.placeholder = 'طريقة التحليل الفعلية بالمختبر (مطلوب)';
    methodInput.setAttribute('aria-label', 'طريقة التحليل المعتمدة بالمختبر');
    const evidenceInput = document.createElement('textarea');
    evidenceInput.placeholder = 'مرجع الشركة المصنعة أو بروتوكول المختبر ورقمه (مطلوب)';
    evidenceInput.setAttribute('aria-label', 'مرجع نموذج الفحص');
    const rationaleInput = document.createElement('textarea');
    rationaleInput.placeholder = 'سبب اختيار هذا النموذج والحقول (مطلوب)';
    rationaleInput.setAttribute('aria-label', 'مبررات الحقول');
    const proposeButton = document.createElement('button');
    proposeButton.type = 'button';
    proposeButton.textContent = 'إرسال النموذج للمراجعة';
    const reviewHistoryContainer = document.createElement('section');
    const help = document.createElement('p');
    help.textContent = 'لا تُفعّل النماذج أو القوائم إلا بعد مراجعة مختلفة واعتماد إداري. أدخل فقط ما تؤكده طريقة التحليل، بدون افتراض المدى المرجعي.';
    reviewBody.append(help, reviewSelect, suggestButton, proposalFields, addFieldButton,
      methodInput, evidenceInput, rationaleInput, proposeButton,
      reviewHistoryContainer, reviewStatus);
    reviewPanel.append(reviewHeading, reviewBody);
    root.appendChild(reviewPanel);
    // Independent NOVA local test management. Preserves immutable Royal Lab source.
    // Newly approved tests enter existing NOVA hospital_lab_tests, so reception,
    // cashier and original NOVA laboratory results continue using their own flows.
    function mountNOVALocalTestDesigner() {
      const panel = document.createElement('details');
      panel.className = 'nova-lab-local-designer';
      panel.dir = 'rtl';
      const summary = document.createElement('summary');
      summary.textContent = 'إضافة فحص جديد أو تعديل فحص محلي';
      const area = document.createElement('section');
      const note = document.createElement('p');
      note.textContent = 'تقدر تنشئ فحص جديد وتحدد حقوله ووحداته وقوائمه. النشر يحتاج اعتماد شخص آخر من الإدارة. الفحص الذي لديه طلبات سابقة لا تتغير حقوله؛ أنشئ نسخة جديدة.';
      const selector = document.createElement('select');
      selector.setAttribute('aria-label', 'اختر فحصاً محلياً للتعديل');
      const name = document.createElement('input');
      name.placeholder = 'اسم الفحص الجديد';
      name.setAttribute('aria-label','اسم الفحص');
      const section = document.createElement('input');
      section.placeholder = 'قسم المعمل مثل الكيمياء الحيوية';
      section.setAttribute('aria-label', 'قسم الفحص');
      const price = document.createElement('input');
      price.type = 'number';
      price.min = '0.01';
      price.step = '0.01';
      price.placeholder = 'سعر الفحص بالجنيه';
      price.setAttribute('aria-label','سعر الفحص');
      const fieldsArea = document.createElement('section');
      const add = document.createElement('button');
      add.type = 'button';
      add.textContent = 'إضافة حقل نتيجة جديد';
      const method = document.createElement('textarea');
      method.placeholder = 'طريقة التحليل أو الجهاز المستخدم';
      const evidence = document.createElement('textarea');
      evidence.placeholder = 'مرجع الشركة المصنعة أو بروتوكول المعمل';
      const rationale = document.createElement('textarea');
      rationale.placeholder = 'مبررات إنشاء أو تعديل الفحص';
      const propose = document.createElement('button');
      propose.type = 'button';
      propose.textContent = 'إرسال الفحص للمراجعة والاعتماد';
      const refresh = document.createElement('button');
      refresh.type = 'button';
      refresh.textContent = 'تحديث طلبات المراجعة';
      const status = document.createElement('p');
      status.setAttribute('role','status');
      const approvals = document.createElement('section');
      area.append(note,selector,name,section,price,fieldsArea,add,
        method,evidence,rationale,propose,refresh,status,approvals);
      panel.append(summary,area);
      root.appendChild(panel);
      let localTests = [];
      let seq = 0;
      let loadToken = 0;
      async function fetchJson(url) {
        const response = await fetch(base + url, {credentials:'same-origin'});
        if (!response.ok) throw new Error('تعذر تحميل بيانات إدارة الفحوص؛ تحقق من الصلاحيات');
        return response.json();
      }
      function newOption(value,text) {
        const el = document.createElement('option');
        el.value = safeText(value);
        el.textContent = safeText(text);
        return el;
      }
      function makeField(data) {
        const f = data || {};
        const box = document.createElement('fieldset');
        const legend = document.createElement('legend');
        legend.textContent = 'حقل النتيجة';
        const label = document.createElement('input');
        label.dataset.localLabel = '1';
        label.placeholder = 'اسم الحقل مثل WBC';
        label.value = safeText(f.label);
        const kind = document.createElement('select');
        kind.dataset.localKind = '1';
        kind.append(newOption('text','نص'),newOption('number','رقم'),
                    newOption('select','قائمة منسدلة'));
        kind.value = f.kind || 'text';
        const unit = document.createElement('input');
        unit.dataset.localUnit = '1';
        unit.placeholder = 'الوحدة (اختياري)';
        unit.value = safeText(f.unit);
        const options = document.createElement('textarea');
        options.dataset.localOptions = '1';
        options.placeholder = 'خيارات القائمة: كل خيار في سطر';
        options.value = Array.isArray(f.options) ? f.options.join('\n') : '';
        const reference = document.createElement('input');
        reference.dataset.localReference = '1';
        reference.placeholder = 'المدى المرجعي حسب طريقة المعمل (اختياري)';
        reference.value = safeText(f.reference);
        const source = document.createElement('input');
        source.dataset.localReferenceSource = '1';
        source.placeholder = 'مرجع المدى الطبيعي عند كتابته';
        source.value = safeText(f.reference_source);
        const required = document.createElement('input');
        required.type = 'checkbox';
        required.dataset.localRequired = '1';
        required.checked = f.required === true;
        const requiredLabel = document.createElement('label');
        requiredLabel.textContent = 'نتيجة مطلوبة';
        requiredLabel.appendChild(required);
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.textContent = 'حذف الحقل من المقترح';
        remove.addEventListener('click', function () { box.remove(); });
        function toggle() { options.hidden = kind.value !== 'select'; }
        kind.addEventListener('change', toggle);
        box.dataset.localKey = safeText(f.key || ('field' + (++seq)));
        box.append(legend,label,kind,unit,options,reference,source,requiredLabel,remove);
        toggle();
        fieldsArea.appendChild(box);
        return box;
      }
      add.addEventListener('click', function () { makeField(); });
      function clearForm() {
        fieldsArea.replaceChildren();
        seq = 0;
        name.value = '';
        section.value = '';
        price.value = '';
        method.value = '';
        evidence.value = '';
        rationale.value = '';
        status.textContent = '';
        makeField();
      }
      async function loadLocalTests() {
        const id = ++loadToken;
        const response = await fetchJson('/local/tests');
        if (id !== loadToken) return;
        if (!Array.isArray(response)) throw new Error('قائمة الفحوص المحلية غير صحيحة');
        localTests = response;
        const previous = selector.value;
        selector.replaceChildren(newOption('','— فحص جديد —'));
        for (const t of response) selector.appendChild(
            newOption(t.local_id,t.name + (t.has_orders ? ' — مستخدم، لا يُعدل' : '')));
        if (Array.from(selector.options).some(o => o.value === previous))
          selector.value = previous;
      }
      selector.addEventListener('change', async function () {
        const id = selector.value;
        clearForm();
        if (!id) return;
        const token = ++loadToken;
        try {
          const form = await fetchJson('/local/form/' + encodeURIComponent(id));
          if (token !== loadToken || id !== selector.value) return;
          name.value = safeText(form.name);
          price.value = safeText(form.price);
          fieldsArea.replaceChildren();
          for (const f of form.fields || []) makeField(f);
          const record = localTests.find(x => safeText(x.local_id) === id);
          if (form.has_orders || (record && record.has_orders)) {
            propose.disabled = true;
            status.textContent = 'الفحص مستخدم في طلبات سابقة؛ لا يمكن تغيير نموذج نتائجه. أضف فحصاً جديداً بدلاً منه.';
          } else propose.disabled = false;
        } catch (e) { status.textContent = safeText(e.message); }
      });
      function readFields() {
        return Array.from(fieldsArea.querySelectorAll('fieldset')).map(function (box) {
          const kind = box.querySelector('[data-local-kind]').value;
          const choices = box.querySelector('[data-local-options]').value;
          return {key:box.dataset.localKey,
            label:box.querySelector('[data-local-label]').value.trim(),
            kind:kind,unit:box.querySelector('[data-local-unit]').value.trim(),
            options:kind === 'select' ? choices.split(/\r?\n/).map(s=>s.trim()).filter(Boolean) : [],
            reference:box.querySelector('[data-local-reference]').value.trim(),
            reference_source:box.querySelector('[data-local-reference-source]').value.trim(),
            required:box.querySelector('[data-local-required]').checked};
        });
      }
      propose.addEventListener('click',async function () {
        propose.disabled = true;
        try {
          const localId = selector.value ? Number(selector.value) : null;
          const record = localTests.find(x => x.local_id === localId);
          if (record && record.has_orders) throw new Error('الفحص مرتبط بطلبات قديمة؛ أنشئ نسخة جديدة');
          const response = await send('/local/propose',{
            local_id:localId,name:name.value.trim(),section:section.value.trim(),
            price:price.value,fields:readFields(),method:method.value.trim(),
            evidence:evidence.value.trim(),rationale:rationale.value.trim()
          });
          if (!response.proposal_id || response.state !== 'pending')
            throw new Error('لم يتم حفظ طلب المراجعة');
          status.textContent = 'تم حفظ المقترح رقم ' + response.proposal_id +
            '، وسيظهر الفحص بعد موافقة مراجع إداري آخر.';
          await loadProposals();
        } catch (e) { status.textContent = safeText(e.message); }
        finally { propose.disabled = false; }
      });
      async function loadProposals() {
        const pending = await fetchJson('/local/proposals');
        if (!Array.isArray(pending)) throw new Error('سجل المراجعة غير صحيح');
        approvals.replaceChildren();
        const title = document.createElement('h4');
        title.textContent = 'مقترحات الفحوص بانتظار الاعتماد';
        approvals.appendChild(title);
        for (const item of pending.filter(x => x.state === 'pending')) {
          const group = document.createElement('section');
          const caption = document.createElement('strong');
          caption.textContent = item.name + ' — ' + item.section + ' — ' + item.price;
          group.appendChild(caption);
          for (const f of item.fields || []) {
            const paragraph = document.createElement('p');
            paragraph.textContent = safeText(f.label) + ' — ' + safeText(f.kind) +
              (f.unit ? ' — ' + safeText(f.unit) : '') +
              ((f.options||[]).length ? ' — ' + f.options.join('، ') : '') +
              (f.reference ? ' — المدى: ' + safeText(f.reference) : '');
            group.appendChild(paragraph);
          }
          for (const line of ['الطريقة: ' + item.method, 'المرجع: ' + item.evidence,
                    'التبرير: ' + item.rationale]) {
            const paragraph = document.createElement('p');
            paragraph.textContent = safeText(line);
            group.appendChild(paragraph);
          }
          const attestation = document.createElement('textarea');
          attestation.placeholder = 'إقرار المراجع المستقل بمطابقة النموذج لطريقة المعمل';
          const approveButton = document.createElement('button');
          approveButton.type = 'button';
          approveButton.textContent = 'اعتماد الفحص بعد المراجعة';
          approveButton.addEventListener('click',async function () {
            approveButton.disabled = true;
            try {
              const done = await send('/local/approve',{
                proposal_id:item.proposal_id,form_hash:item.form_hash,
                attestation:attestation.value.trim()
              });
              if (done.state !== 'approved') throw new Error('لم يعتمد النموذج');
              status.textContent = 'تم اعتماد الفحص داخل كتالوج NOVA المحلي، ولم تُعتمد نتائج مرضى.';
              await loadLocalTests();
              await loadProposals();
            } catch(e) { status.textContent = safeText(e.message); }
            finally { approveButton.disabled = false; }
          });
          group.append(attestation,approveButton);
          approvals.appendChild(group);
        }
      }
      refresh.addEventListener('click',function () {
        loadLocalTests().then(loadProposals).catch(e => {status.textContent=safeText(e.message);});
      });
      clearForm();
      panel.addEventListener('toggle',function () {
        if (!panel.open) return;
        loadLocalTests().then(loadProposals).catch(e => {status.textContent=safeText(e.message);});
      });
    }
    mountNOVALocalTestDesigner();
    let fieldSequence = 0;
    function makeReviewField() {
      const line = document.createElement('fieldset');
      line.className = 'royal-lab-review-field';
      const legend = document.createElement('legend');
      legend.textContent = 'حقل نتيجة ' + (++fieldSequence);
      const label = document.createElement('input');
      label.placeholder = 'اسم الحقل';
      label.dataset.reviewLabel = '1';
      const kind = document.createElement('select');
      kind.dataset.reviewKind = '1';
      for (const choice of [['text','نص'], ['number','رقم'], ['select','قائمة منسدلة']]) {
        const option = document.createElement('option');
        option.value = choice[0];
        option.textContent = choice[1];
        kind.appendChild(option);
      }
      const unit = document.createElement('input');
      unit.placeholder = 'الوحدة من مرجع الفحص، إن وجدت';
      unit.dataset.reviewUnit = '1';
      const choices = document.createElement('textarea');
      choices.placeholder = 'خيارات القائمة: خيار واحد في كل سطر';
      choices.dataset.reviewChoices = '1';
      choices.hidden = true;
      kind.addEventListener('change', function () {
        choices.hidden = kind.value !== 'select';
        if (kind.value !== 'select') choices.value = '';
      });
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.textContent = 'حذف الحقل';
      remove.addEventListener('click', function () { line.remove(); });
      line.append(legend,label,kind,unit,choices,remove);
      proposalFields.appendChild(line);
      return line;
    }
    addFieldButton.addEventListener('click', makeReviewField);
    suggestButton.addEventListener('click', async function () {
      const selected = reviewSelect.value;
      if (!selected) {
        reviewStatus.textContent = 'اختر فحصاً يحتاج إصلاحاً';
        return;
      }
      if (proposalFields.querySelector('fieldset')) {
        reviewStatus.textContent = 'حافظ على الحقول المكتوبة: امسحها يدوياً قبل استيراد المقترح';
        return;
      }
      suggestButton.disabled = true;
      try {
        const response = await fetch(base + '/review/suggestion/' + encodeURIComponent(selected),
          { credentials: 'same-origin' });
        if (!response.ok) throw new Error('تعذر قراءة مقترحات المصدر؛ تحقق من الصلاحيات');
        const result = await response.json();
        if (selected !== reviewSelect.value) return;
        if (!result || result.source_test_id !== selected || !Array.isArray(result.fields) ||
            result.ready_for_patient_results !== false || result.requires_independent_approval !== true)
          throw new Error('مقترح المراجعة غير صالح');
        for (const candidate of result.fields) {
          if (!candidate || !candidate.label || !['text','number','select'].includes(candidate.kind))
            continue;
          const row = makeReviewField();
          row.querySelector('[data-review-label]').value = safeText(candidate.label);
          row.querySelector('[data-review-kind]').value = candidate.kind;
          row.querySelector('[data-review-unit]').value = safeText(candidate.unit);
          const choices = row.querySelector('[data-review-choices]');
          choices.value = Array.isArray(candidate.option_labels) ?
            candidate.option_labels.map(safeText).join('\n') : '';
          choices.hidden = candidate.kind !== 'select';
        }
        const warnings = Array.isArray(result.warnings) ? result.warnings : [];
        reviewStatus.textContent = result.fields.length +
          ' حقل مقترح للمراجعة؛ تحقق من طريقة التحليل والقوائم، ولا تعتمدها دون مستند.' +
          (warnings.length ? ' تنبيهات: ' + warnings.map(safeText).join('؛ ') : '');
      } catch (error) {
        reviewStatus.textContent = safeText(error.message);
      } finally {
        suggestButton.disabled = false;
      }
    });

    function refreshReviewOptions() {
      const previously = reviewSelect.value;
      reviewSelect.replaceChildren();
      const initial = document.createElement('option');
      initial.value = '';
      initial.textContent = '— اختر فحصاً يحتاج إصلاحاً —';
      reviewSelect.appendChild(initial);
      for (const t of tests.filter(function (x) {
        return x.entry_status === 'requires_review';
      })) {
        const o = document.createElement('option');
        o.value = safeText(t.source_test_id);
        o.textContent = displayText(t.name);
        reviewSelect.appendChild(o);
      }
      if (Array.from(reviewSelect.options).some(function (o) { return o.value === previously; }))
        reviewSelect.value = previously;
    }
    async function fetchReviewHistory() {
      const sourceId = reviewSelect.value;
      reviewHistoryContainer.replaceChildren();
      if (!sourceId) return;
      const response = await fetch(base + '/review/history/' + encodeURIComponent(sourceId),
        { credentials: 'same-origin' });
      if (!response.ok) throw new Error('عرض المراجعة يتطلب صلاحية موظف معمل');
      const entries = await response.json();
      if (sourceId !== reviewSelect.value) return;
      if (!Array.isArray(entries)) throw new Error('بيانات مراجعة النموذج غير صحيحة');
      if (!entries.length) {
        reviewStatus.textContent = 'لا توجد نسخة مراجعة مرسلة لهذا الفحص';
        return;
      }
      const latest = entries[entries.length - 1];
      if (!latest || latest.state !== 'pending') {
        reviewStatus.textContent = 'آخر نسخة من النموذج معتمدة؛ حدّث قائمة الفحوصات';
        return;
      }
      const detailResponse = await fetch(base + '/review/details/' +
        encodeURIComponent(sourceId) + '/' + encodeURIComponent(latest.revision),
        { credentials: 'same-origin' });
      if (!detailResponse.ok) throw new Error('تعذر تحميل حقول النموذج للمراجعة');
      const data = await detailResponse.json();
      if (sourceId !== reviewSelect.value) return;
      if (data.form_hash !== latest.form_hash || !data.form || !Array.isArray(data.form.fields))
        throw new Error('تغيّرت نسخة المراجعة؛ لا يمكن اعتمادها');
      const header = document.createElement('h4');
      header.textContent = 'مراجعة مستقلة للنسخة ' + safeText(data.revision);
      reviewHistoryContainer.appendChild(header);
      for (const f of data.form.fields) {
        const row = document.createElement('p');
        row.textContent = safeText(f.label) + ' — ' + safeText(f.kind) +
          (f.unit ? ' (' + safeText(f.unit) + ')' : '') +
          (f.options && f.options.length ? ' — ' +
            f.options.map(function (o) { return safeText(o.label); }).join('، ') : '');
        reviewHistoryContainer.appendChild(row);
      }
      for (const line of ['طريقة الفحص: ' + data.method, 'المرجع: ' + data.evidence,
                         'مبررات التعديل: ' + data.rationale]) {
        const paragraph = document.createElement('p');
        paragraph.textContent = safeText(line);
        reviewHistoryContainer.appendChild(paragraph);
      }
      const attestation = document.createElement('textarea');
      attestation.placeholder = 'إقرار مستقل بمراجعة طريقة التحليل والحقول والقوائم';
      attestation.setAttribute('aria-label', 'إقرار مراجعة واعتماد نموذج الفحص');
      const approval = document.createElement('button');
      approval.type = 'button';
      approval.textContent = 'اعتماد النموذج بعد المراجعة (إدارة المعمل)';
      approval.addEventListener('click', async function () {
        approval.disabled = true;
        try {
          if (sourceId !== reviewSelect.value) throw new Error('تغير الفحص المحدد');
          await send('/review/approve', {
            source_test_id: sourceId, revision: data.revision,
            form_hash: data.form_hash, attestation: attestation.value.trim()
          });
          reviewStatus.textContent = 'تم اعتماد النموذج بواسطة مراجع مستقل. حدّث قائمة الفحوصات.';
          await load();
          await fetchReviewHistory();
        } catch (error) {
          reviewStatus.textContent = safeText(error.message);
        } finally {
          approval.disabled = false;
        }
      });
      reviewHistoryContainer.append(attestation, approval);
      reviewStatus.textContent = 'النموذج بانتظار اعتماد شخص مخوّل مختلف عن مُعدّه';
    }
    reviewSelect.addEventListener('change', function () {
      proposalFields.replaceChildren();
      fieldSequence = 0;
      reviewStatus.textContent = '';
      fetchReviewHistory().catch(function (error) {
        reviewStatus.textContent = safeText(error.message);
      });
    });
    proposeButton.addEventListener('click', async function () {
      if (!reviewSelect.value) {
        reviewStatus.textContent = 'اختر الفحص الناقص أولاً';
        return;
      }
      proposeButton.disabled = true;
      try {
        const rows = Array.from(proposalFields.querySelectorAll('fieldset'));
        const fields = rows.map(function (row, index) {
          const kind = row.querySelector('[data-review-kind]').value;
          const choicesText = row.querySelector('[data-review-choices]').value;
          const options = kind === 'select' ? choicesText.split(/\r?\n/)
            .map(function (x) { return x.trim(); }).filter(Boolean)
            .map(function (label, i) { return { key: 'o' + (i + 1), label: label }; }) : [];
          return { key: 'f' + (index + 1), label: row.querySelector('[data-review-label]').value.trim(),
            kind: kind, unit: row.querySelector('[data-review-unit]').value.trim(),
            options: options };
        });
        if (!fields.length) throw new Error('أضف حقلاً واحداً على الأقل');
        await send('/review/propose', {
          source_test_id: reviewSelect.value, fields: fields,
          method: methodInput.value.trim(), evidence: evidenceInput.value.trim(),
          rationale: rationaleInput.value.trim()
        });
        reviewStatus.textContent = 'تم إرسال النموذج للمراجعة المستقلة؛ لم يُفعّل بعد';
        await fetchReviewHistory();
      } catch (error) {
        reviewStatus.textContent = safeText(error.message);
      } finally {
        proposeButton.disabled = false;
      }
    });
    async function load() {
      status.textContent = 'جاري تحميل فحوصات المعمل...';
      const serial = ++loadSerial;
      const response = await fetch(base + '/tests', { credentials: 'same-origin' });
      if (!response.ok) throw new Error('تعذر تحميل فحوصات المعمل');
      const data = await response.json();
      if (serial !== loadSerial) return;
      if (!Array.isArray(data.tests) || !Number.isSafeInteger(data.total) || data.total <= 0 || data.tests.length !== data.total ||
          data.tests.some(function (test) { return !test || !test.source_test_id || !displayText(test.name); }) ||
          new Set(data.tests.map(function (test) { return safeText(test.source_test_id); })).size !== data.tests.length)
        throw new Error('كتالوج الفحوصات غير مكتمل أو يحتوي على تكرار');
      tests = data.tests;
      filter();
      refreshReviewOptions();
      const readyCount = Number.isSafeInteger(data.ready_for_result_entry) ? data.ready_for_result_entry : null;
      const serviceCount = Number.isSafeInteger(data.non_lab_services) ? data.non_lab_services : 0;
      const clinicalBlocked = Number.isSafeInteger(data.clinical_needing_review) ?
        data.clinical_needing_review : data.total - (readyCount || 0) - serviceCount;
      status.textContent = readyCount === null ? 'تم تحميل ' + data.total + ' فحص' :
        'جاهز لإدخال النتائج: ' + readyCount + '؛ يحتاج مراجعة: ' + clinicalBlocked +
        '؛ خدمات غير معملية: ' + serviceCount;
    }
    async function showSelected() {
      const id = picker.value;
      const serial = ++requestSerial;
      detail.replaceChildren();
      formReady = false;
      saveButton.disabled = true;
      if (!id) return;
      status.textContent = 'جاري تحميل حقول الفحص...';
      try {
        const response = await fetch(base + '/form/' + encodeURIComponent(id), { credentials: 'same-origin' });
        if (!response.ok) throw new Error('تعذر تحميل حقول الفحص');
        const data = await response.json();
        if (serial !== requestSerial) return;
        if (!data.test || safeText(data.test.source_test_id) !== id) throw new Error('هوية الفحص غير متطابقة');
        const reviewFlags = Array.isArray(data.test.review_flags) ? data.test.review_flags : [];
        if (reviewFlags.length) {
          status.textContent = 'الفحص يحتاج مراجعة الحقول قبل حفظ النتائج';
          saveButton.disabled = true;
          return;
        }
        const fields = Array.isArray(data.test.fields) ? data.test.fields : [];
        const fieldIds = fields.map(function (f) { return safeText(f && f.source_format_id); });
        if (!fields.length || fieldIds.some(function (v) { return !v || v === 'null'; }) ||
            new Set(fieldIds).size !== fieldIds.length ||
            fields.some(function (f) { return [false, 0, 'False', 'false', '0'].includes(f.active); })) {
          status.textContent = 'بيانات حقول الفحص غير مكتملة وتحتاج مراجعة';
          saveButton.disabled = true;
          return;
        }
        const title = document.createElement('h3');
        title.textContent = displayText(data.test.name);
        detail.appendChild(title);
        for (const field of data.test.fields || []) {
          const line = document.createElement('label');
          line.className = 'royal-lab-field';
          const label = document.createElement('span');
          label.textContent = displayText(field.label) + (field.unit ? ' (' + displayText(field.unit) + ')' : '');
          line.appendChild(label);
          const ranges = [];
          for (const range of field.numeric_ranges || []) ranges.push(range);
          for (const range of field.text_ranges || []) ranges.push(range);
          if (ranges.length) {
            const reference = document.createElement('small');
            reference.className = 'royal-lab-reference';
            reference.textContent = 'المدى المرجعي: ' + ranges.map(function (r) {
              if (typeof r === 'string' || typeof r === 'number') return String(r);
              if (r && typeof r === 'object') return Object.entries(r).filter(function (pair) {
                return pair[1] !== null && pair[1] !== '';
              }).map(function (pair) { return pair[0] + ': ' + String(pair[1]); }).join('، ');
              return '';
            }).filter(Boolean).join(' | ');
            reference.textContent = displayText(reference.textContent);
            line.appendChild(reference);
          }
          let control;
          if (field.kind === 'select' || field.kind === 'select_or_text' || field.kind === 'select_or_number') {
            control = document.createElement('select');
            const blank = document.createElement('option');
            blank.value = '';
            blank.textContent = '— اختر —';
            control.appendChild(blank);
            for (const choice of field.options || []) {
              if ([false, 0, 'False', 'false', '0'].includes(choice.active)) continue;
              const opt = document.createElement('option');
              opt.value = safeText(choice.id);
              opt.textContent = displayText(choice.label);
              control.appendChild(opt);
            }
          } else if (field.kind === 'number' || field.kind === 'text') {
            control = document.createElement('input');
            control.type = field.kind === 'number' ? 'number' : 'text';
            if (field.kind === 'number') control.step = Array.isArray(field.types) && field.types.includes('IntegerResultFormat') ? '1' : 'any';
          } else {
            const warning = document.createElement('em');
            warning.textContent = 'الحقل يحتاج مراجعة';
            line.appendChild(warning);
            detail.appendChild(line);
            continue;
          }
          control.dataset.sourceFormatId = safeText(field.source_format_id);
          line.appendChild(control);
          if (field.kind === 'select_or_number' || field.kind === 'select_or_text') {
            const alternative = document.createElement('input');
            alternative.type = field.kind === 'select_or_number' ? 'number' : 'text';
            if (alternative.type === 'number') alternative.step = Array.isArray(field.types) && field.types.includes('IntegerResultFormat') ? '1' : 'any';
            alternative.placeholder = 'أو أدخل قيمة';
            alternative.dataset.alternativeFor = safeText(field.source_format_id);
            line.appendChild(alternative);
          }
          detail.appendChild(line);
        }
        status.textContent = 'تم عرض حقول الفحص';
        formReady = Boolean(detail.querySelector('[data-source-format-id]'));
        saveButton.disabled = !formReady || saving;
      } catch (error) {
        if (serial === requestSerial) status.textContent = safeText(error.message);
      }
    }
    search.addEventListener('input', filter);
    picker.addEventListener('change', showSelected);
    const ready = load().catch(error => { status.textContent = safeText(error.message); throw error; });
    return { ready, refresh: load, select: showSelected };
  }
  global.NOVARoyalLabPicker = { create: createRoyalLabPicker };
})(typeof window === 'undefined' ? globalThis : window);
