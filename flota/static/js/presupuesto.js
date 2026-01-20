// Validación de presupuesto en tiempo real
function verificarPresupuesto() {
    const vehiculoSelect = document.querySelector('#id_vehiculo');
    const cuentaSelect = document.querySelector('#id_cuenta_presupuestaria');
    const costoEstimadoInput = document.querySelector('#id_costo_estimado');
    const anioInput = document.querySelector('#id_fecha_ingreso');
    
    if (!vehiculoSelect || !cuentaSelect) return;
    
    const vehiculo = vehiculoSelect.value;
    const cuenta = cuentaSelect.value;
    
    if (!vehiculo || !cuenta) return;
    
    // Extraer año de la fecha
    let anio = new Date().getFullYear();
    if (anioInput && anioInput.value) {
        anio = new Date(anioInput.value).getFullYear();
    }
    
    // Obtener monto estimado
    let monto = 0;
    if (costoEstimadoInput && costoEstimadoInput.value) {
        monto = parseFloat(costoEstimadoInput.value);
    }
    
    // Llamar a la API
    fetch(`/api/verificar-presupuesto/?vehiculo=${vehiculo}&cuenta=${cuenta}&anio=${anio}&monto=${monto}`)
        .then(response => response.json())
        .then(data => {
            // Mostrar mensaje de presupuesto
            let alertDiv = document.querySelector('#presupuesto-alert');
            if (!alertDiv) {
                alertDiv = document.createElement('div');
                alertDiv.id = 'presupuesto-alert';
                alertDiv.className = 'alert mt-3';
                document.querySelector('form').prepend(alertDiv);
            }
            
            if (data.tiene_presupuesto) {
                alertDiv.className = 'alert alert-info mt-3';
                alertDiv.innerHTML = `
                    <i class="fas fa-check-circle"></i> ${data.mensaje}
                    <div class="progress mt-2">
                        <div class="progress-bar" role="progressbar" 
                             style="width: ${data.porcentaje_ejecutado}%" 
                             aria-valuenow="${data.porcentaje_ejecutado}" 
                             aria-valuemin="0" 
                             aria-valuemax="100">
                            ${data.porcentaje_ejecutado.toFixed(1)}% ejecutado
                        </div>
                    </div>
                `;
            } else {
                alertDiv.className = 'alert alert-danger mt-3';
                alertDiv.innerHTML = `
                    <i class="fas fa-exclamation-triangle"></i> ${data.mensaje}
                    <br><small>No podrá guardar el mantenimiento sin presupuesto suficiente.</small>
                `;
            }
        })
        .catch(error => {
            console.error('Error verificando presupuesto:', error);
        });
}

// Llamar a la función cuando cambien los campos relevantes
document.addEventListener('DOMContentLoaded', function() {
    const vehiculoSelect = document.querySelector('#id_vehiculo');
    const cuentaSelect = document.querySelector('#id_cuenta_presupuestaria');
    const costoEstimadoInput = document.querySelector('#id_costo_estimado');
    const fechaIngresoInput = document.querySelector('#id_fecha_ingreso');
    
    if (vehiculoSelect) {
        vehiculoSelect.addEventListener('change', verificarPresupuesto);
    }
    if (cuentaSelect) {
        cuentaSelect.addEventListener('change', verificarPresupuesto);
    }
    if (costoEstimadoInput) {
        costoEstimadoInput.addEventListener('input', verificarPresupuesto);
    }
    if (fechaIngresoInput) {
        fechaIngresoInput.addEventListener('change', verificarPresupuesto);
    }
    
    // Verificar al cargar la página
    setTimeout(verificarPresupuesto, 500);
});
