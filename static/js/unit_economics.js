(function () {
    'use strict';

    const CSRF = window.UNIT.csrf;
    const URLS = window.UNIT.urls;
    const BUILTIN = window.UNIT.builtinMetrics;
    const VARIABLES = window.UNIT.variables;

    function post(url, data) {
        const fd = new FormData();
        for (const k in data) fd.append(k, data[k]);
        return fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': CSRF, 'X-Requested-With': 'XMLHttpRequest' },
            body: fd,
        }).then(r => r.json());
    }

    function postJson(url, data) {
        return fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': CSRF,
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        }).then(r => r.json());
    }

    /* ===== ПЕРЕМЕННЫЕ ===== */

    function bindVariableRow(row) {
        const saveBtn = row.querySelector('.variable-save-btn');
        const delBtn = row.querySelector('.variable-delete-btn');
        if (!saveBtn || !delBtn) return;

        saveBtn.addEventListener('click', function () {
            const id = row.dataset.variableId || '';
            const name = row.querySelector('.variable-name') ?
                row.querySelector('.variable-name').textContent.trim() :
                row.querySelector('.variable-name-input').value.trim();
            const value = row.querySelector('.variable-value').value;
            const description = row.querySelector('.variable-description').value;

            post(URLS.variableSave, { id, name, value, description })
                .then(data => {
                    if (!data.success) { alert(data.error); return; }
                    // обновляем в памяти
                    const idx = VARIABLES.findIndex(v => v.name === name);
                    if (idx >= 0) VARIABLES[idx].value = data.variable.value;
                    else VARIABLES.push({ name: data.variable.name, value: data.variable.value });
                    // обновляем кнопки во всех редакторах формул
                    refreshFormulaVariables();
                    flash(saveBtn);
                });
        });

        delBtn.addEventListener('click', function () {
            if (!confirm('Удалить переменную?')) return;
            const id = row.dataset.variableId;
            post(URLS.variableDelete, { id })
                .then(data => {
                    if (!data.success) { alert(data.error); return; }
                    const name = row.querySelector('.variable-name')?.textContent.trim()
                        || row.querySelector('.variable-name-input')?.value.trim();
                    const idx = VARIABLES.findIndex(v => v.name === name);
                    if (idx >= 0) VARIABLES.splice(idx, 1);
                    row.remove();
                    refreshFormulaVariables();
                });
        });
    }

    document.querySelectorAll('#variablesTable tbody tr[data-variable-id]').forEach(bindVariableRow);

    document.getElementById('addVariableBtn')?.addEventListener('click', function () {
        const tbody = document.querySelector('#variablesTable tbody');
        const emptyRow = tbody.querySelector('.empty-row');
        if (emptyRow) emptyRow.remove();

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="text" class="form-control form-control-sm variable-name-input" placeholder="tax"></td>
            <td><input type="number" step="0.01" class="form-control form-control-sm variable-value" value="0"></td>
            <td><input type="text" class="form-control form-control-sm variable-description" placeholder=""></td>
            <td class="text-end">
                <button type="button" class="btn btn-sm btn-outline-success variable-save-btn"><i class="bi bi-check-lg"></i></button>
                <button type="button" class="btn btn-sm btn-outline-danger variable-delete-btn"><i class="bi bi-trash"></i></button>
            </td>
        `;
        tbody.appendChild(tr);

        const saveBtn = tr.querySelector('.variable-save-btn');
        const delBtn = tr.querySelector('.variable-delete-btn');
        const nameInput = tr.querySelector('.variable-name-input');
        const valueInput = tr.querySelector('.variable-value');
        const descInput = tr.querySelector('.variable-description');

        saveBtn.addEventListener('click', function () {
            const name = nameInput.value.trim();
            if (!name) { alert('Введите название'); return; }
            post(URLS.variableSave, { id: '', name, value: valueInput.value, description: descInput.value })
                .then(data => {
                    if (!data.success) { alert(data.error); return; }
                    tr.dataset.variableId = data.variable.id;
                    // заменим inputs на code/span
                    const tdName = tr.children[0];
                    tdName.innerHTML = `<code class="variable-name">${data.variable.name}</code>`;
                    VARIABLES.push({ name: data.variable.name, value: data.variable.value });
                    refreshFormulaVariables();
                    flash(saveBtn);
                });
        });

        delBtn.addEventListener('click', function () {
            if (tr.dataset.variableId) {
                post(URLS.variableDelete, { id: tr.dataset.variableId }).then(() => {});
            }
            tr.remove();
        });
    });

    /* ===== ТОВАРЫ ===== */

    document.querySelectorAll('tr[data-cost-id]').forEach(function (row) {
        const btn = row.querySelector('.cost-save-btn');
        const input = row.querySelector('.cost-value');
        if (!btn || !input) return;
        btn.addEventListener('click', function () {
            post(URLS.costSave, { id: row.dataset.costId, cost: input.value })
                .then(data => {
                    if (!data.success) { alert(data.error); return; }
                    flash(btn);
                });
        });
    });

    /* ===== ФОРМУЛЫ ===== */

    function refreshFormulaVariables() {
        document.querySelectorAll('.formula-variables-list').forEach(function (list) {
            list.innerHTML = '';
            VARIABLES.forEach(function (v) {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'fb-widget-btn fb-widget-btn-variable';
                btn.dataset.type = 'variable';
                btn.dataset.value = v.name;
                btn.dataset.label = v.name;
                btn.textContent = `🔢 ${v.name} = ${v.value}`;
                list.appendChild(btn);
            });
        });
    }

    function initFormulaCard(card) {
        const editBtn = card.querySelector('.formula-edit-btn');
        const delBtn = card.querySelector('.formula-delete-btn');
        const editArea = card.querySelector('.formula-edit-area');
        const saveBtn = card.querySelector('.formula-save-btn');
        const cancelBtn = card.querySelector('.formula-cancel-btn');
        const clearBtn = card.querySelector('.formula-clear-btn');
        const exprBox = card.querySelector('.formula-expression');
        const openMetricsBtn = card.querySelector('.fb-widget-open-metrics');
        const numberBtn = card.querySelector('.fb-widget-btn-number');
        const numberInput = card.querySelector('.fb-widget-number-input');
        const errorEl = card.querySelector('.formula-save-error');

        let expression = [];
        const exprScript = card.querySelector('script.formula-expr-json');
        if (exprScript) {
            try {
                expression = JSON.parse(exprScript.textContent || '[]');
            } catch (e) {
                console.error('Bad formula JSON:', e, exprScript.textContent);
                expression = [];
            }
        }

        function renderExpression() {
            exprBox.innerHTML = '';
            expression.forEach(function (tok, idx) {
                const el = document.createElement('span');
                el.className = 'fb-widget-token fb-widget-token-' + tok.type;
                el.innerHTML = '<span>' + tok.label + '</span>' +
                    '<button type="button" class="fb-widget-remove" data-idx="' + idx + '">×</button>';
                exprBox.appendChild(el);
            });
            exprBox.querySelectorAll('.fb-widget-remove').forEach(function (b) {
                b.addEventListener('click', function () {
                    const i = parseInt(this.dataset.idx, 10);
                    expression.splice(i, 1);
                    renderExpression();
                });
            });
        }

        function addToken(type, value, label) {
            expression.push({ type: type, value: value, label: label });
            renderExpression();
        }

        card.querySelectorAll('.fb-widget-btn-op, .fb-widget-btn-paren').forEach(function (btn) {
            btn.addEventListener('click', function () {
                addToken(this.dataset.type, this.dataset.value, this.dataset.label);
            });
        });

        // Свои переменные — делегируем
        card.addEventListener('click', function (e) {
            const btn = e.target.closest('.fb-widget-btn-variable');
            if (btn) addToken('variable', btn.dataset.value, btn.dataset.label);
        });

        if (openMetricsBtn) {
            openMetricsBtn.addEventListener('click', function () {
                openMetricPicker(function (m) {
                    addToken('metric', m.code, m.label);
                });
            });
        }

        if (numberBtn) {
            numberBtn.addEventListener('click', function () {
                const v = (numberInput.value || '').trim();
                if (!v) return;
                addToken('number', v, v);
                numberInput.value = '';
            });
        }

        if (clearBtn) {
            clearBtn.addEventListener('click', function () {
                expression = [];
                renderExpression();
            });
        }

        if (editBtn) {
            editBtn.addEventListener('click', function () {
                card.querySelector('.formula-edit-area').style.display = 'block';
                card.querySelector('.formula-card-header').style.display = 'none';
                renderExpression();
            });
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', function () {
                card.querySelector('.formula-edit-area').style.display = 'none';
                card.querySelector('.formula-card-header').style.display = '';
            });
        }

        if (saveBtn) {
            saveBtn.addEventListener('click', function () {
                const id = card.dataset.formulaId || '';
                const name = card.querySelector('.formula-input-name').value.trim();
                const order = parseInt(card.querySelector('.formula-input-order').value, 10) || 0;
                const isTotal = card.querySelector('.formula-input-total').checked;
                const description = card.querySelector('.formula-input-description').value.trim();

                if (!name) { errorEl.textContent = 'Введите название'; errorEl.style.display = 'block'; return; }
                if (!expression.length) { errorEl.textContent = 'Формула пуста'; errorEl.style.display = 'block'; return; }

                postJson(URLS.formulaSave, {
                    id: id, name, description, expression, order,
                    is_total: isTotal, is_active: true,
                })
                .then(data => {
                    if (!data.success) { errorEl.textContent = data.error; errorEl.style.display = 'block'; return; }
                    location.reload();
                })
                .catch(() => { errorEl.textContent = 'Ошибка сети'; errorEl.style.display = 'block'; });
            });
        }

        if (delBtn) {
            delBtn.addEventListener('click', function () {
                if (!confirm('Удалить формулу?')) return;
                post(URLS.formulaDelete, { id: card.dataset.formulaId })
                    .then(data => {
                        if (data.success) card.remove();
                    });
            });
        }
    }

    document.querySelectorAll('.formula-card').forEach(initFormulaCard);
    refreshFormulaVariables();

    document.getElementById('addFormulaBtn')?.addEventListener('click', function () {
        const html = `
            <div class="formula-card" data-formula-id="">
                <script type="application/json" class="formula-expr-json">[]</script>
                <div class="formula-card-header" style="display:none;">
                    <strong>Новая формула</strong>
                </div>
                <div class="formula-edit-area">
                    <div class="row g-2 mb-2">
                        <div class="col-md-6">
                            <label class="form-label small">Название</label>
                            <input type="text" class="form-control form-control-sm formula-input-name" value="">
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small">Порядок</label>
                            <input type="number" class="form-control form-control-sm formula-input-order" value="0" min="0">
                        </div>
                        <div class="col-md-3 d-flex align-items-end">
                            <div class="form-check">
                                <input type="checkbox" class="form-check-input formula-input-total">
                                <label class="form-check-label small">Итоговое</label>
                            </div>
                        </div>
                    </div>
                    <div class="mb-2">
                        <label class="form-label small">Описание</label>
                        <input type="text" class="form-control form-control-sm formula-input-description" value="">
                    </div>
                    <div class="row g-2">
                        <div class="col-md-5">
                            <div class="fb-widget-blocks">
                                <div class="fb-widget-group">
                                    <div class="fb-widget-group-title">Встроенные правила</div>
                                    <button type="button" class="fb-widget-btn fb-widget-open-metrics">📊 Все правила</button>
                                </div>
                                <div class="fb-widget-group">
                                    <div class="fb-widget-group-title">Свои переменные</div>
                                    <div class="fb-widget-buttons formula-variables-list"></div>
                                </div>
                                <div class="fb-widget-group">
                                    <div class="fb-widget-group-title">Число</div>
                                    <div class="d-flex gap-1">
                                        <input type="number" step="0.01" class="fb-widget-number-input" placeholder="100">
                                        <button type="button" class="fb-widget-btn fb-widget-btn-number">➕</button>
                                    </div>
                                </div>
                                <div class="fb-widget-group">
                                    <div class="fb-widget-group-title">Знаки и скобки</div>
                                    <div class="fb-widget-buttons">
                                        <button type="button" class="fb-widget-btn fb-widget-btn-op" data-type="operator" data-value="+" data-label="+">+</button>
                                        <button type="button" class="fb-widget-btn fb-widget-btn-op" data-type="operator" data-value="-" data-label="−">−</button>
                                        <button type="button" class="fb-widget-btn fb-widget-btn-op" data-type="operator" data-value="*" data-label="×">×</button>
                                        <button type="button" class="fb-widget-btn fb-widget-btn-op" data-type="operator" data-value="/" data-label="÷">÷</button>
                                        <button type="button" class="fb-widget-btn fb-widget-btn-paren" data-type="paren" data-value="(" data-label="(">(</button>
                                        <button type="button" class="fb-widget-btn fb-widget-btn-paren" data-type="paren" data-value=")" data-label=")">)</button>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-7">
                            <label class="form-label small">Формула</label>
                            <div class="fb-widget-expression formula-expression"></div>
                            <button type="button" class="btn btn-sm btn-outline-secondary formula-clear-btn mt-2">Очистить</button>
                        </div>
                    </div>
                    <div class="mt-3 d-flex gap-2">
                        <button type="button" class="btn btn-sm btn-success formula-save-btn">💾 Сохранить</button>
                        <button type="button" class="btn btn-sm btn-secondary formula-cancel-btn">Отмена</button>
                    </div>
                    <div class="formula-save-error text-danger small mt-2" style="display:none;"></div>
                </div>
            </div>
        `;
        const container = document.getElementById('formulasContainer');
        const wrapper = document.createElement('div');
        wrapper.innerHTML = html;
        const card = wrapper.firstElementChild;
        container.appendChild(card);
        refreshFormulaVariables();
        initFormulaCard(card);

        // Показать редактор сразу
        card.querySelector('.formula-edit-area').style.display = 'block';

        // Отмена = удаляем карточку
        card.querySelector('.formula-cancel-btn').addEventListener('click', function () {
            card.remove();
        }, { once: true });
    });

    /* ===== МОДАЛКА ВЫБОРА ПРАВИЛА ===== */

    let metricPickerCallback = null;

    function openMetricPicker(callback) {
        metricPickerCallback = callback;
        const modalEl = document.getElementById('metricPickerModal');
        const body = document.getElementById('metricPickerBody');

        // Группируем
        const grouped = {};
        BUILTIN.forEach(function (m) {
            const group = groupOf(m.code);
            if (!grouped[group]) grouped[group] = [];
            grouped[group].push(m);
        });

        let html = '';
        Object.keys(grouped).forEach(function (group) {
            html += `<div class="mb-3">
                <div class="text-muted small text-uppercase mb-2">${group}</div>
                <div class="d-flex flex-wrap gap-2">`;
            grouped[group].forEach(function (m) {
                html += `<button type="button" class="fb-widget-btn fb-widget-btn-metric metric-pick-btn"
                            data-code="${m.code}" data-label="${m.label}">📊 ${m.label}</button>`;
            });
            html += `</div></div>`;
        });
        body.innerHTML = html;

        body.querySelectorAll('.metric-pick-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                if (metricPickerCallback) {
                    metricPickerCallback({ code: this.dataset.code, label: this.dataset.label });
                }
                bootstrap.Modal.getInstance(modalEl).hide();
            });
        });

        bootstrap.Modal.getOrCreateInstance(modalEl).show();
    }

    function groupOf(code) {
        if (code.startsWith('sum_items_')) return 'Заказы: Сумма';
        if (code.startsWith('count_items_')) return 'Заказы: Количество';
        if (code.startsWith('cost_items_')) return 'Заказы: Себестоимости';
        if (code.startsWith('return_refund_')) return 'Возвраты: Сумма (деньги)';
        if (code.startsWith('return_items_')) return 'Возвраты: Сумма (товары)';
        if (code.startsWith('return_count_')) return 'Возвраты: Количество';
        if (code.startsWith('return_cost_')) return 'Возвраты: Себестоимости';
        return 'Прочее';
    }

    /* ===== ВСПОМОГАТЕЛЬНОЕ ===== */

    function flash(btn) {
        const orig = btn.innerHTML;
        btn.innerHTML = '<i class="bi bi-check-lg"></i>';
        btn.classList.remove('btn-outline-success');
        btn.classList.add('btn-success');
        setTimeout(function () {
            btn.innerHTML = orig;
            btn.classList.add('btn-outline-success');
            btn.classList.remove('btn-success');
        }, 1200);
    }

})();