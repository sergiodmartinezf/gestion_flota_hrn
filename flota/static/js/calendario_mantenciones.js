document.addEventListener('DOMContentLoaded', function() {
    var calendarEl = document.getElementById('calendar');
    
    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        locale: 'es',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,listMonth'
        },
        events: "{% url 'api_mantenimientos' %}", // Fuente de datos JSON
        
        // Acción al hacer clic en un evento
        eventClick: function(info) {
            var evento = info.event;
            var props = evento.extendedProps;
            
            // Llenar datos del modal
            document.getElementById('modalTitulo').innerText = evento.title;
            document.getElementById('modalEstado').innerText = props.estado;
            document.getElementById('modalInicio').innerText = evento.start.toLocaleDateString();
            document.getElementById('modalFin').innerText = evento.end ? evento.end.toLocaleDateString() : 'En curso/Pendiente';
            document.getElementById('modalCosto').innerText = props.costo;
            document.getElementById('modalDescripcion').innerText = props.descripcion;
            
            // Configurar botones de acción (CRUD)
            // Asumimos que las URLs son /mantenimientos/ID/editar
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
});
