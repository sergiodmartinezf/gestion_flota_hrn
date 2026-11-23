// Validación del formulario de modificación de bitácora
document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            const errores = [];

            errores.push(...validarSeleccion(document.getElementById('id_vehiculo')?.value, 'vehículo', true));
            errores.push(...validarFecha(document.getElementById('id_fecha')?.value, 'fecha', true));
            errores.push(...validarSeleccion(document.getElementById('id_turno')?.value, 'turno', true));
            errores.push(...validarEnteroPositivo(document.getElementById('id_km_inicio')?.value, 'kilometraje inicio', 0, 9999999, true));
            errores.push(...validarEnteroPositivo(document.getElementById('id_km_fin')?.value, 'kilometraje fin', 0, 9999999, false));

            // Validar que km_fin >= km_inicio (si ambos están informados)
            const kmInicio = parseInt(document.getElementById('id_km_inicio')?.value || 0);
            const kmFinVal = document.getElementById('id_km_fin')?.value;
            const kmFin = kmFinVal !== '' && kmFinVal != null ? parseInt(kmFinVal) : null;
            if (kmFin !== null && kmFin < kmInicio) {
                errores.push('El kilometraje fin debe ser mayor o igual al kilometraje inicio');
            }
            const margenKm = 400;
            if (kmFin !== null && kmFin > kmInicio + margenKm) {
                e.preventDefault();
                alert(`El KM final (${kmFin.toLocaleString('es-CL')} km) es demasiado elevado para el KM inicial (${kmInicio.toLocaleString('es-CL')} km). El margen permitido es de ${margenKm} km (máximo ${ (kmInicio + margenKm).toLocaleString('es-CL') } km). Corrija el dato antes de guardar.`);
                document.getElementById('id_km_fin')?.focus();
                document.getElementById('id_km_fin')?.select();
                return false;
            }

            if (errores.length > 0) {
                e.preventDefault();
                mostrarErroresValidacion(errores, 'Errores en el Formulario');
                return false;
            }
        });
    }
});

