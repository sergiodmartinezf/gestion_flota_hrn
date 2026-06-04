// Variables globales
let vehiculosKilometraje = {};
let calendar;

// Función para actualizar kilometraje basado en el vehículo seleccionado
function actualizarKilometrajeProgramar() {
    const selectVehiculo = document.getElementById('programar_vehiculo');
    const kmInput = document.getElementById('programar_km_al_ingreso');

    if (selectVehiculo && kmInput) {
        const selectedOption = selectVehiculo.options[selectVehiculo.selectedIndex];
        let kilometraje = selectedOption.getAttribute('data-kilometraje');
        if (kilometraje) {
            // Extraer solo dígitos (0-9)
            const kmLimpio = String(kilometraje).replace(/\D/g, '');
            if (kmLimpio) {
                kmInput.value = kmLimpio;
            } else {
                console.warn('No se pudo extraer un kilometraje válido de:', kilometraje);
                kmInput.value = '';
            }
        } else {
            kmInput.value = '';
        }
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
    var calendarEl = document.getElementById('calendar');
    var eventsUrl = calendarEl.getAttribute('data-events-url');
    
    calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        locale: 'es',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,listMonth'
        },
        events: eventsUrl,
        
        // Permitir crear eventos al hacer clic en una fecha
        dateClick: function(info) {
            if (typeof ES_ADMIN !== 'undefined' && ES_ADMIN) {
                const modalProgramar = new bootstrap.Modal(
                    document.getElementById('modalProgramar')
                );
                document.getElementById('programar_fecha_ingreso').value = info.dateStr;
                document.getElementById('programar_fecha_programada').value = info.dateStr;
                modalProgramar.show();
            }
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
            var editUrl = "/mantenimientos/editar/" + evento.id + "/";
            
            var btnEditar = document.getElementById('btnEditar');
            var formEliminar = document.getElementById('formEliminar');
            
            if(btnEditar) btnEditar.href = editUrl;
            
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
            actualizarKilometrajeProgramar();
        });
    }
});
