/* Royal Lab replacement catalogue UI, independent of legacy NOVA test names.
   Mount on an authenticated lab container; the existing gateway enforces roles.
   No printing, pharmacy or cashier code is modified. */
(function (global) {
  'use strict';
  function safeText(value) { return String(value == null ? '' : value); }
  function createRoyalLabPicker(root, apiBase) {
    if (!root || typeof root.appendChild !== 'function') throw new Error('Lab container required');
    const base = apiBase || '/api/hospital/royallab-native';
    root.replaceChildren();
    const search = document.createElement('input');
    search.type = 'search';
    search.placeholder = 'ابحث عن فحص Royal Lab';
    search.setAttribute('aria-label', 'بحث فحوصات المعمل');
    const picker = document.createElement('select');
    picker.setAttribute('aria-label', 'فحوصات Royal Lab');
    const detail = document.createElement('section');
    detail.dir = 'rtl';
    const status = document.createElement('p');
    status.setAttribute('role', 'status');
    root.dir = 'rtl';
    root.append(search, picker, status, detail);
    let tests = [];
    let requestSerial = 0;
    function filter() {
      const q = search.value.trim().toLocaleLowerCase();
      picker.replaceChildren();
      const empty = document.createElement('option');
      empty.value = '';
      empty.textContent = '— اختر الفحص —';
      picker.appendChild(empty);
      for (const test of tests) {
        if (!safeText(test.name).toLocaleLowerCase().includes(q) &&
            !safeText(test.source_test_id).toLocaleLowerCase().includes(q)) continue;
        const option = document.createElement('option');
        option.value = safeText(test.source_test_id);
        option.textContent = safeText(test.name);
        picker.appendChild(option);
      }
      detail.replaceChildren();
    }
    async function load() {
      status.textContent = 'جاري تحميل كتالوج Royal Lab...';
      const response = await fetch(base + '/tests', { credentials: 'same-origin' });
      if (!response.ok) throw new Error('تعذر تحميل فحوصات المعمل');
      const data = await response.json();
      if (!Array.isArray(data.tests) || data.total !== 367 || data.tests.length !== 367)
        throw new Error('كتالوج Royal Lab غير مكتمل');
      tests = data.tests;
      filter();
      status.textContent = 'تم تحميل 367 فحص من Royal Lab';
    }
    async function showSelected() {
      const id = picker.value;
      const serial = ++requestSerial;
      detail.replaceChildren();
      if (!id) return;
      status.textContent = 'جاري تحميل حقول الفحص...';
      try {
        const response = await fetch(base + '/form/' + encodeURIComponent(id), { credentials: 'same-origin' });
        if (!response.ok) throw new Error('تعذر تحميل حقول الفحص');
        const data = await response.json();
        if (serial !== requestSerial) return;
        if (!data.test || safeText(data.test.source_test_id) !== id) throw new Error('هوية الفحص غير متطابقة');
        const title = document.createElement('h3');
        title.textContent = safeText(data.test.name);
        detail.appendChild(title);
        for (const field of data.test.fields || []) {
          const line = document.createElement('label');
          line.className = 'royal-lab-field';
          const label = document.createElement('span');
          label.textContent = safeText(field.label) + (field.unit ? ' (' + safeText(field.unit) + ')' : '');
          line.appendChild(label);
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
              opt.textContent = safeText(choice.label);
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
