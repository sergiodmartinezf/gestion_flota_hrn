document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('input[name="km_cierre"]').forEach(function (campoKm) {
        const formulario = campoKm.closest('form');
        if (!formulario) return;

        const validarMargen = function () {
            const kmInicio = Number(campoKm.dataset.kmInicio);
            const margen = Number(campoKm.dataset.margenKm || 400);
            const kmMaximo = kmInicio + margen;
            campoKm.setCustomValidity(
                campoKm.value !== '' && Number(campoKm.value) > kmMaximo
                    ? `El KM final supera el margen de ${margen} km. Máximo permitido: ${kmMaximo} km.`
                    : ''
            );
        };

        campoKm.addEventListener('input', validarMargen);
        campoKm.addEventListener('invalid', function (evento) {
            validarMargen();
            if (campoKm.validationMessage && campoKm.value !== '' && Number(campoKm.value) > Number(campoKm.dataset.kmInicio) + Number(campoKm.dataset.margenKm || 400)) {
                evento.preventDefault();
                alert(campoKm.validationMessage + ' Corrija el dato antes de cerrar la hoja.');
                campoKm.focus();
                campoKm.select();
            }
        });

        formulario.addEventListener('submit', function (evento) {
            const kmInicio = Number(campoKm.dataset.kmInicio);
            const margen = Number(campoKm.dataset.margenKm || 400);
            const kmFinal = Number(campoKm.value);
            const kmMaximo = kmInicio + margen;

            validarMargen();

            if (campoKm.value !== '' && Number.isFinite(kmFinal) && kmFinal > kmMaximo) {
                evento.preventDefault();
                alert(
                    `El kilometraje final (${kmFinal.toLocaleString('es-CL')} km) es demasiado elevado ` +
                    `para el inicial (${kmInicio.toLocaleString('es-CL')} km). ` +
                    `El margen permitido es de ${margen} km (máximo ${kmMaximo.toLocaleString('es-CL')} km). ` +
                    'Corrija el dato antes de cerrar la hoja.'
                );
                campoKm.focus();
                campoKm.select();
            }
        });
    });
});

