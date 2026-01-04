// Inicializar campos de fecha
document.addEventListener('DOMContentLoaded', function() {
    // Establecer fecha actual por defecto para fecha_solicitud
    const fechaField = document.querySelector('#id_fecha_solicitud');
    if (fechaField && !fechaField.value) {
        const today = new Date().toISOString().split('T')[0];
        fechaField.value = today;
    }
});
