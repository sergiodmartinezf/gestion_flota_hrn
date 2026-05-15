/** Formato RUT chileno; expone `window.formatearRUT`. */
document.addEventListener('DOMContentLoaded', function() {
    function formatearRUT(input) {
        let valor = input.value.replace(/[^0-9kK]/g, '');

        if (valor.length > 9) {
            valor = valor.substring(0, 9);
        }

        if (valor.length > 1) {
            const cuerpo = valor.slice(0, -1);
            const dv = valor.slice(-1).toUpperCase();
            let cuerpoFormateado = cuerpo.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
            input.value = cuerpoFormateado + '-' + dv;
        } else if (valor.length === 1) {
            input.value = valor.toUpperCase();
        } else {
            input.value = valor;
        }
    }

    window.formatearRUT = formatearRUT;

    const rutInputs = document.querySelectorAll('input[id*="rut"], input[id*="RUT"], input[name*="rut"], input[name*="RUT"]');

    rutInputs.forEach(function(input) {
        input.addEventListener('input', function() {
            formatearRUT(this);
        });

        input.addEventListener('blur', function() {
            if (this.value) {
                formatearRUT(this);
            }
        });

        input.addEventListener('keypress', function(e) {
            const char = String.fromCharCode(e.which);
            if (!/[0-9kK]/.test(char) && !/[0-9]/.test(e.key)) {
                if (![8, 9, 13, 27, 37, 38, 39, 40, 46].includes(e.keyCode)) {
                    e.preventDefault();
                }
            }
        });
    });
});
