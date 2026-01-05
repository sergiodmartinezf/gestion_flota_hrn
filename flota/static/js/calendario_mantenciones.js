// Variables globales
let vehiculosKilometraje = {};
let calendar;

// Cargar kilometraje de vehículos
function cargarKilometrajeVehiculos() {
    fetch('/api/vehiculos-kilometraje/')
        .then(response => response.json())
        .then(data => {
            vehiculosKilometraje = data;
        })
        .catch(error => console.error('Error al cargar kilometraje:', error));
}

// Actualizar kilometraje en formulario de programar
function actualizarKilometrajeProgramar(patente) {
    const kmInput = document.getElementById('programar_km_al_ingreso');
    if (kmInput && vehiculosKilometraje[patente] !== undefined) {
        kmInput.value = vehiculosKilometraje[patente];
    }
}

// Enviar formulario de programar
function enviarProgramar() {
    const form = document.getElementById('formProgramar');
    if (form) {
        form.submit();
    }
}

document.addEventListener('DOMContentLoaded', function() {
    cargarKilometrajeVehiculos();
    
    var calendarEl = document.getElementById('calendar');
    var eventsUrl = calendarEl.getAttribute('data-events-url');
    
    calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        locale: 'es',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,listMonth'
        },
        events: eventsUrl,
        
        // Permitir crear eventos al hacer clic en una fecha
        dateClick: function(info) {
            {% if user.rol == 'Administrador' %}
            // Abrir modal para programar mantenimiento
            const modalProgramar = new bootstrap.Modal(document.getElementById('modalProgramar'));
            document.getElementById('programar_fecha_ingreso').value = info.dateStr;
            document.getElementById('programar_fecha_programada').value = info.dateStr;
            modalProgramar.show();
            {% endif %}
        },
        
        // Acción al hacer clic en un evento existente
        eventClick: function(info) {
            var evento = info.event;
            var props = evento.extendedProps;
            
            // Llenar datos del modal
            document.getElementById('modalTitulo').innerText = evento.title;
            document.getElementById('modalEstado').innerText = props.estado;
            document.getElementById('modalInicio').innerText = evento.start.toLocaleDateString('es-CL');
            document.getElementById('modalFin').innerText = evento.end ? evento.end.toLocaleDateString('es-CL') : 'En curso/Pendiente';
            document.getElementById('modalCosto').innerText = props.costo || '0';
            document.getElementById('modalDescripcion').innerText = props.descripcion || 'Sin observaciones';
            
            // Configurar botones de acción
            var editUrl = "/mantenimientos/" + evento.id + "/editar/";
            var deleteUrl = "/mantenimientos/" + evento.id + "/eliminar/";
            
            var btnEditar = document.getElementById('btnEditar');
            var formEliminar = document.getElementById('formEliminar');
            
            if(btnEditar) btnEditar.href = editUrl;
            if(formEliminar) formEliminar.action = deleteUrl;
            
            // Mostrar Modal
            var modal = new bootstrap.Modal(document.getElementById('eventoModal'));
            modal.show();
        }
    });
    
    calendar.render();
    
    // Event listener para actualizar kilometraje al seleccionar vehículo
    const selectVehiculo = document.getElementById('programar_vehiculo');
    if (selectVehiculo) {
        selectVehiculo.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            const kilometraje = selectedOption.getAttribute('data-kilometraje');
            const kmInput = document.getElementById('programar_km_al_ingreso');
            if (kmInput && kilometraje) {
                kmInput.value = kilometraje;
            }
        });
    }
});
