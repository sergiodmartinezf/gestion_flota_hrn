document.addEventListener('DOMContentLoaded', function() {
    initLogicaTraslados();
    initFormsetPacientes();
});

// 1. Lógica de Categorías de Traslado
function initLogicaTraslados() {
    const catSelect = document.getElementById('id_categoria_traslado');
    const altaContainer = document.getElementById('container-origen-alta');
    const altaSelect = document.getElementById('id_detalle_origen_alta');

    if (catSelect) {
        catSelect.addEventListener('change', function() {
            if (this.value === 'ALTA') {
                altaContainer.style.display = 'block';
                altaSelect.setAttribute('required', 'required');
            } else {
                altaContainer.style.display = 'none';
                altaSelect.removeAttribute('required');
                altaSelect.value = ''; // Limpiar
            }
        });
        // Disparar al cargar por si hay error de validación y volvemos
        catSelect.dispatchEvent(new Event('change'));
    }
}

// 2. Lógica Dinámica de Pacientes (Formset)
function initFormsetPacientes() {
    const container = document.getElementById('pacientes-container');
    const addButton = document.getElementById('add-paciente');
    const totalFormsInput = document.getElementById('id_pacientes-TOTAL_FORMS');
    const emptyFormTemplate = document.getElementById('empty-form').innerHTML;

    // A. Agregar nuevo paciente
    addButton.addEventListener('click', function() {
        const formIdx = parseInt(totalFormsInput.value);
        const newFormHtml = emptyFormTemplate.replace(/__prefix__/g, formIdx);
        
        const div = document.createElement('div');
        div.innerHTML = newFormHtml;
        container.appendChild(div.firstElementChild);
        
        totalFormsInput.value = formIdx + 1;
        
        // Inicializar listeners en el nuevo elemento
        initRowListeners(container.lastElementChild);
    });

    // B. Inicializar listeners en filas existentes (las que vienen del servidor)
    const existingRows = container.querySelectorAll('.paciente-row');
    existingRows.forEach(row => initRowListeners(row));
}

// Configura el comportamiento de una fila de paciente (existente o nueva)
function initRowListeners(rowElement) {
    // 1. Lógica Destino -> Dirección
    const destinoSelect = rowElement.querySelector('.destino-selector');
    const dirContainer = rowElement.querySelector('.container-direccion');
    const dirInput = rowElement.querySelector('.direccion-input');

    if (destinoSelect) {
        destinoSelect.addEventListener('change', function() {
            // Mostrar input si es Domicilio u Otro
            if (this.value === 'DOMICILIO' || this.value === 'OTRO') {
                dirContainer.style.display = 'block';
                dirInput.setAttribute('required', 'required');
            } else {
                dirContainer.style.display = 'none';
                dirInput.removeAttribute('required');
            }
        });
        // Trigger inicial
        destinoSelect.dispatchEvent(new Event('change'));
    }

    // 2. Botón Quitar (solo para elementos dinámicos JS)
    const removeBtn = rowElement.querySelector('.remove-paciente');
    if (removeBtn) {
        removeBtn.addEventListener('click', function() {
            rowElement.remove();
            // Nota: No actualizamos TOTAL_FORMS al bajar, Django maneja los huecos, 
            // pero si es estricto, habría que re-indexar. Para simplicidad, ocultar o borrar funciona en POST.
            // Una solución simple es marcar un input hidden DELETE si existiera, pero aquí lo removemos del DOM.
        });
    }
}
