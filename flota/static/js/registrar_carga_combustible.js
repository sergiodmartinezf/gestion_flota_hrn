/**
 * Validaciones para el formulario de registro de carga de combustible
 */
document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            const errores = [];
            
            errores.push(...validarSeleccion(document.getElementById('id_patente_vehiculo')?.value, 'vehículo', true));
            errores.push(...validarFecha(document.getElementById('id_fecha')?.value, 'fecha', true));
            errores.push(...validarEnteroPositivo(document.getElementById('id_kilometraje_al_cargar')?.value, 'kilometraje', 0, 9999999, true));
            errores.push(...validarNumeroDecimal(document.getElementById('id_litros')?.value, 'litros', 0, 9999, true));
            errores.push(...validarNumeroDecimal(document.getElementById('id_costo_total')?.value, 'costo total', 0, 9999999, true));
            errores.push(...validarSeleccion(document.getElementById('id_proveedor')?.value, 'proveedor', true));
            
            if (errores.length > 0) {
                e.preventDefault();
                mostrarErroresValidacion(errores, 'Errores en el Formulario');
                return false;
            }
        });
    }
});

