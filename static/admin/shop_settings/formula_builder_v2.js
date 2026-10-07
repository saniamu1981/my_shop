(function () {
    // WeakSet — не копируется при клонировании узла Django
    const initializedWidgets = new WeakSet();

    function initAllWidgets() {
        document.querySelectorAll('.fb-widget').forEach(function (root) {
            if (initializedWidgets.has(root)) return;
            initializedWidgets.add(root);

            const hiddenInput = root.querySelector('.fb-widget-hidden');
            const exprBox = root.querySelector('.fb-widget-expression');
            const clearBtn = root.querySelector('.fb-widget-clear');

            if (!hiddenInput || !exprBox) {
                console.warn('fb-widget: не найдены hidden input или expression box');
                return;
            }

            let expression = [];
            try {
                expression = JSON.parse(hiddenInput.value || '[]');
            } catch (e) { expression = []; }

            function sync() { hiddenInput.value = JSON.stringify(expression); }

            function render() {
                exprBox.innerHTML = '';
                expression.forEach(function (tok, idx) {
                    const el = document.createElement('span');
                    el.className = 'fb-widget-token fb-widget-token-' + tok.type;
                    el.innerHTML = '<span>' + tok.label + '</span>' +
                        '<button type="button" class="fb-widget-remove" data-idx="' + idx + '">×</button>';
                    exprBox.appendChild(el);
                });
                exprBox.querySelectorAll('.fb-widget-remove').forEach(function (btn) {
                    btn.addEventListener('click', function () {
                        const i = parseInt(this.dataset.idx, 10);
                        expression.splice(i, 1);
                        sync(); render();
                    });
                });
                sync();
            }

            function addToken(type, value, label) {
                expression.push({ type: type, value: value, label: label });
                sync(); render();
            }

            const blocks = root.querySelector('.fb-widget-blocks');
            if (blocks) {
                blocks.querySelectorAll('.fb-widget-btn-metric, .fb-widget-btn-variable, .fb-widget-btn-op, .fb-widget-btn-paren')
                    .forEach(function (btn) {
                        btn.addEventListener('click', function () {
                            addToken(this.dataset.type, this.dataset.value, this.dataset.label);
                        });
                    });
            }

            const numberBtn = root.querySelector('.fb-widget-btn-number');
            if (numberBtn) {
                numberBtn.addEventListener('click', function () {
                    const input = root.querySelector('.fb-widget-number-input');
                    const v = input ? input.value.trim() : '';
                    if (!v) return;
                    addToken('number', v, v);
                    if (input) input.value = '';
                });
            }

            if (clearBtn) {
                clearBtn.addEventListener('click', function () {
                    expression = []; sync(); render();
                });
            }

            const openBtn = root.querySelector('.fb-widget-open-metrics');
            const modal = root.querySelector('.fb-widget-modal');

            if (openBtn && modal) {
                const overlay = modal.querySelector('.fb-widget-modal-overlay');
                const closeBtn = modal.querySelector('.fb-widget-modal-close');

                function openModal() { modal.classList.add('is-open'); }
                function closeModal() { modal.classList.remove('is-open'); }

                openBtn.addEventListener('click', openModal);
                if (overlay) overlay.addEventListener('click', closeModal);
                if (closeBtn) closeBtn.addEventListener('click', closeModal);

                modal.querySelectorAll('.fb-widget-btn-metric').forEach(function (btn) {
                    btn.addEventListener('click', function () {
                        addToken('metric', this.dataset.value, this.dataset.label);
                        closeModal();
                    });
                });
            } else {
                console.warn('fb-widget: нет openBtn или modal');
            }

            render();
        });
    }

    function startObserver() {
        if (!document.body) return;

        let pending = false;
        const observer = new MutationObserver(function () {
            if (pending) return;
            pending = true;
            setTimeout(function () {
                pending = false;
                initAllWidgets();
            }, 50);
        });
        observer.observe(document.body, { childList: true, subtree: true });

        // Дополнительно: клик по «Добавить ещё один Формула» в inline
        document.addEventListener('click', function (e) {
            const target = e.target;
            if (target && target.classList && target.classList.contains('add-row')) {
                setTimeout(initAllWidgets, 100);
            }
        }, true);
    }

    function boot() {
        initAllWidgets();
        startObserver();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();