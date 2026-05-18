/**
 * Aviso de inactividad: "¿Sigues ahí?" con cuenta regresiva antes de cerrar sesión.
 */
(function() {
    const IDLE_MS = 15 * 60 * 1000;
    const WARNING_SEC = 60;
    const logoutUrl = document.body.dataset.logoutUrl;
    if (!logoutUrl) return;

    let idleTimer = null;
    let countdownTimer = null;
    let secondsLeft = WARNING_SEC;
    let modalInstance = null;

    const modalEl = document.getElementById('modalSesionInactiva');
    const countdownEl = document.getElementById('sesion-countdown');
    const btnContinuar = document.getElementById('btn-sesion-continuar');

    function resetIdleTimer() {
        clearTimeout(idleTimer);
        idleTimer = setTimeout(showWarning, IDLE_MS);
    }

    function hideWarning() {
        if (modalInstance) {
            modalInstance.hide();
        }
        clearInterval(countdownTimer);
        countdownTimer = null;
        secondsLeft = WARNING_SEC;
        if (countdownEl) countdownEl.textContent = String(WARNING_SEC);
        resetIdleTimer();
    }

    function logout() {
        window.location.href = logoutUrl;
    }

    function showWarning() {
        if (!modalEl || typeof bootstrap === 'undefined') {
            logout();
            return;
        }
        secondsLeft = WARNING_SEC;
        if (countdownEl) countdownEl.textContent = String(secondsLeft);
        if (!modalInstance) {
            modalInstance = new bootstrap.Modal(modalEl, { backdrop: 'static', keyboard: false });
        }
        modalInstance.show();
        clearInterval(countdownTimer);
        countdownTimer = setInterval(function() {
            secondsLeft -= 1;
            if (countdownEl) countdownEl.textContent = String(secondsLeft);
            if (secondsLeft <= 0) {
                clearInterval(countdownTimer);
                logout();
            }
        }, 1000);
    }

    const eventos = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart', 'click'];
    eventos.forEach(function(ev) {
        document.addEventListener(ev, resetIdleTimer, { passive: true });
    });

    if (btnContinuar) {
        btnContinuar.addEventListener('click', hideWarning);
    }

    resetIdleTimer();
})();
