// Datos de kilometraje de vehículos
let vehiculosKilometraje = {};

// Función para cargar los datos de los vehículos
function cargarDatosVehiculos() {
    // Hacer una petición AJAX para obtener los datos de los vehículos
    fetch('/api/vehiculos-kilometraje/')
        .then(response => response.json())
        .then(data => {
            vehiculosKilometraje = data;
            
            // Si ya hay un vehículo seleccionado, actualizar el kilometraje
            const vehiculoSelect = document.getElementById('id_vehiculo');
            if (vehiculoSelect.value) {
                actualizarKilometrajeInicio(vehiculoSelect.value);
            }
        })
        .catch(error => console.error('Error al cargar datos de vehículos:', error));
}

// Función para actualizar el campo de kilometraje inicio
function actualizarKilometrajeInicio(vehiculoPatente) {
    const kmInicioInput = document.getElementById('id_km_inicio');
    if (vehiculosKilometraje[vehiculoPatente] !== undefined) {
        kmInicioInput.value = vehiculosKilometraje[vehiculoPatente];
        
        // También actualizar el valor mínimo del campo km_fin
        const kmFinInput = document.getElementById('id_km_fin');
        if (kmFinInput) {
            kmFinInput.min = vehiculosKilometraje[vehiculoPatente];
            
            // Si el valor actual es menor, actualizarlo
            if (parseInt(kmFinInput.value) < parseInt(kmInicioInput.value)) {
                kmFinInput.value = kmInicioInput.value;
            }
        }
    }
}

// Esperar a que el DOM esté completamente cargado
document.addEventListener('DOMContentLoaded', function() {
    // Cargar los datos de los vehículos
    cargarDatosVehiculos();
    
    // Escuchar cambios en el select de vehículo
    const vehiculoSelect = document.getElementById('id_vehiculo');
    if (vehiculoSelect) {
        vehiculoSelect.addEventListener('change', function() {
            actualizarKilometrajeInicio(this.value);
        });
    }
    
    // Validación para que km_fin sea mayor que km_inicio
    const kmInicioInput = document.getElementById('id_km_inicio');
    const kmFinInput = document.getElementById('id_km_fin');
    
    if (kmInicioInput && kmFinInput) {
        kmInicioInput.addEventListener('change', function() {
            if (kmFinInput) {
                kmFinInput.min = this.value;
                if (parseInt(kmFinInput.value) < parseInt(this.value)) {
                    kmFinInput.value = this.value;
                }
            }
        });
        
        kmFinInput.addEventListener('change', function() {
            if (parseInt(this.value) < parseInt(kmInicioInput.value)) {
                alert('El kilometraje fin debe ser mayor o igual al kilometraje inicio');
                this.value = kmInicioInput.value;
            }
        });
    }
});

