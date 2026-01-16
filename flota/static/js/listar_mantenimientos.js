// Cambio de estado directo sin formulario aparte
document.addEventListener('DOMContentLoaded', function() {
    const selects = document.querySelectorAll('.estado-mantenimiento');
    selects.forEach(select => {
        select.addEventListener('change', function() {
            const mantenimientoId = this.dataset.id;
            const nuevoEstado = this.value;
            const estadoTexto = this.options[this.selectedIndex].text;
            
            if (confirm(`¿Está seguro de cambiar el estado a "${estadoTexto}"?`)) {
                // Obtener CSRF token
                const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                                 getCookie('csrftoken');
                
                fetch(`/mantenimientos/${mantenimientoId}/cambiar-estado/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrftoken
                    },
                    body: JSON.stringify({estado: nuevoEstado})
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        location.reload();
                    } else {
                        alert('Error al cambiar el estado: ' + (data.error || 'Error desconocido'));
                        location.reload();
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error al cambiar el estado');
                    location.reload();
                });
            } else {
                location.reload();
            }
        });
    });
});

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

