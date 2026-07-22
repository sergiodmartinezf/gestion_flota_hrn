// Registro de solución aplicada a alerta
(function () {
    const modalEl = document.getElementById('modalRegistrarAccionAlerta');
    if (!modalEl) return;

    const form = document.getElementById('formRegistrarAccionAlerta');
    const patenteEl = document.getElementById('registrarAccionAlertaPatente');
    const descEl = document.getElementById('registrarAccionAlertaDescripcion');
    const nextInput = document.getElementById('registrarAccionAlertaNext');
    const solucionInput = document.getElementById('registrarAccionAlertaSolucion');

    document.querySelectorAll('.btn-registrar-accion-alerta').forEach(function (btn) {
        btn.addEventListener('click', function () {
            form.action = btn.dataset.alertaUrl;
            patenteEl.textContent = btn.dataset.alertaPatente || '';
            descEl.textContent = btn.dataset.alertaDesc || '';
            nextInput.value = btn.dataset.alertaNext || window.location.pathname;
            solucionInput.value = btn.dataset.alertaSolucion || '';
        });
    });
})();
