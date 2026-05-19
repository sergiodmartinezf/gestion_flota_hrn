document.addEventListener('DOMContentLoaded', function() {
    // Establecer el año actual por defecto
    const anioInput = document.getElementById('{{ form.anio.id_for_label }}');
    if (anioInput && !anioInput.value) {
        const currentYear = new Date().getFullYear();
        anioInput.value = currentYear;
    }
    
    // Formatear monto asignado
    const montoInput = document.getElementById('{{ form.monto_asignado.id_for_label }}');
    if (montoInput) {
        montoInput.addEventListener('blur', function(e) {
            if (e.target.value) {
                e.target.value = parseFloat(e.target.value).toFixed(2);
            }
        });
    }
});
