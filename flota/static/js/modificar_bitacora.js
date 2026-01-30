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
            errores.push(...validarEnteroPositivo(document.getElementById('id_km_fin')?.value, 'kilometraje fin', 0, 9999999, true));

            // Validar que km_fin >= km_inicio
            const kmInicio = parseInt(document.getElementById('id_km_inicio')?.value || 0);
            const kmFin = parseInt(document.getElementById('id_km_fin')?.value || 0);
            if (kmFin < kmInicio) {
                errores.push('El kilometraje fin debe ser mayor o igual al kilometraje inicio');
            }

            if (errores.length > 0) {
                e.preventDefault();
                mostrarErroresValidacion(errores, 'Errores en el Formulario');
                return false;
            }
        });
    }
});
