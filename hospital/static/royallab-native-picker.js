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
      saveButton.disabled = true;
      saveSelectedDraft().catch(function (error) {
        status.textContent = safeText(error.message);
      }).finally(function () { saveButton.disabled = !picker.value || !detail.querySelector('[data-source-format-id]'); });
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
        option.textContent = displayText(test.name);
        picker.appendChild(option);
      }
      detail.replaceChildren();
      saveButton.disabled = true;
    }
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
      status.textContent = 'تم تحميل ' + data.total + ' فحص';
    }
    async function showSelected() {
      const id = picker.value;
      const serial = ++requestSerial;
      detail.replaceChildren();
      saveButton.disabled = true;
      if (!id) return;
      status.textContent = 'جاري تحميل حقول الفحص...';
      try {
        const response = await fetch(base + '/form/' + encodeURIComponent(id), { credentials: 'same-origin' });
        if (!response.ok) throw new Error('تعذر تحميل حقول الفحص');
        const data = await response.json();
        if (serial !== requestSerial) return;
        if (!data.test || safeText(data.test.source_test_id) !== id) throw new Error('هوية الفحص غير متطابقة');
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
            if (field.kind === 'number') control.step = 'any';
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
            if (alternative.type === 'number') alternative.step = 'any';
            alternative.placeholder = 'أو أدخل قيمة';
            alternative.dataset.alternativeFor = safeText(field.source_format_id);
            line.appendChild(alternative);
          }
          detail.appendChild(line);
        }
        status.textContent = 'تم عرض حقول الفحص';
        saveButton.disabled = !detail.querySelector('[data-source-format-id]');
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
