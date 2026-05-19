// Auto-rellenar kilometraje al seleccionar vehículo en programar mantenimiento
let vehiculosKilometraje = {};

function cargarDatosVehiculos() {
    fetch('/api/vehiculos-kilometraje/')
        .then(response => response.json())
        .then(data => {
            vehiculosKilometraje = data;
            const vehiculoSelect = document.getElementById('id_vehiculo');
            if (vehiculoSelect && vehiculoSelect.value) {
                actualizarKilometraje(vehiculoSelect.value);
            }
        })
        .catch(error => console.error('Error al cargar datos de vehículos:', error));
}

function actualizarKilometraje(vehiculoPatente) {
    const kmInput = document.getElementById('id_km_al_ingreso');
    if (kmInput && vehiculosKilometraje[vehiculoPatente] !== undefined) {
        kmInput.value = vehiculosKilometraje[vehiculoPatente];
    }
}

document.addEventListener('DOMContentLoaded', function() {
    cargarDatosVehiculos();
    
    const vehiculoSelect = document.getElementById('id_vehiculo');
    if (vehiculoSelect) {
        vehiculoSelect.addEventListener('change', function() {
            actualizarKilometraje(this.value);
        });
    }
    
    // Validación del formulario
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            const errores = [];
            
            // Validar vehículo
            errores.push(...validarSeleccion(document.getElementById('id_vehiculo')?.value, 'vehículo', true));
            
            // Validar fecha
            errores.push(...validarFecha(document.getElementById('id_fecha_ingreso')?.value, 'fecha de ingreso', true));
            
            // Validar kilometraje
            errores.push(...validarEnteroPositivo(document.getElementById('id_km_al_ingreso')?.value, 'kilometraje', 0, 9999999, true));
            
            // Validar proveedor
            errores.push(...validarSeleccion(document.getElementById('id_proveedor')?.value, 'proveedor', true));
            
            // Validar descripción
            errores.push(...validarCampoObligatorio(document.getElementById('id_descripcion_trabajo')?.value, 'descripción del trabajo', true));
            
            if (errores.length > 0) {
                e.preventDefault();
                mostrarErroresValidacion(errores, 'Errores en el Formulario');
                return false;
            }
        });
    }
});

