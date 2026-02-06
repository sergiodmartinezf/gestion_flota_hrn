document.addEventListener('DOMContentLoaded', function() {
    // 1. Inicializar lógica de traslados
    initLogicaTraslados();
    
    // 2. Inicializar formset de pacientes
    initFormsetPacientes();
    
    // 3. Configurar validación del formulario
    configurarValidacionFormulario();
    
    // 4. Configurar observador de cambios en pacientes
    const pacientesContainer = document.getElementById('pacientes-container');
    if (pacientesContainer) {
        const observer = new MutationObserver(function() {
            toggleHorasHBO();
        });
        
        observer.observe(pacientesContainer, {
            childList: true,
            subtree: true
        });
    }
    
    // 5. Verificar horas HBO inicialmente
    setTimeout(toggleHorasHBO, 100);
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
                if (altaSelect) altaSelect.setAttribute('required', 'required');
            } else {
                altaContainer.style.display = 'none';
                if (altaSelect) {
                    altaSelect.removeAttribute('required');
                    altaSelect.value = ''; // Limpiar
                }
            }
        });
        // Disparar al cargar por si hay error de validación y volvemos
        catSelect.dispatchEvent(new Event('change'));
    }
}

// 2. Lógica Dinámica de Pacientes (Formset) - VERSIÓN SIMPLIFICADA Y SEGURA
function initFormsetPacientes() {
    const container = document.getElementById('pacientes-container');
    const addButton = document.getElementById('add-paciente');
    const totalFormsInput = document.getElementById('id_pacientes-TOTAL_FORMS');

    // A. Agregar nuevo paciente
    addButton.addEventListener('click', function() {
        const formIdx = parseInt(totalFormsInput.value);
        
        // Crear nuevo formulario usando template
        const template = document.getElementById('empty-form-template');
        if (!template) {
            console.error('No se encontró el template con id="empty-form-template"');
            return;
        }
        
        const clone = template.content.cloneNode(true);
        const newForm = clone.querySelector('.paciente-row');
        
        if (!newForm) {
            console.error('No se encontró .paciente-row en el template');
            return;
        }
        
        // Reemplazar todos los __prefix__ en el nuevo formulario
        const allElements = newForm.querySelectorAll('[name], [id], [for]');
        allElements.forEach(el => {
            if (el.name) el.name = el.name.replace('__prefix__', formIdx);
            if (el.id) el.id = el.id.replace('__prefix__', formIdx);
            if (el.getAttribute('for')) el.setAttribute('for', el.getAttribute('for').replace('__prefix__', formIdx));
        });
        
        // Agregar al contenedor
        container.appendChild(newForm);
        
        // Actualizar el contador
        totalFormsInput.value = formIdx + 1;
        
        // Inicializar listeners en el nuevo elemento
        initRowListeners(newForm);
        
        // Enfocar el primer campo
        setTimeout(() => {
            const firstField = newForm.querySelector('input, select');
            if (firstField) firstField.focus();
        }, 50);
    });

    // B. Inicializar listeners en filas existentes
    if (container) {
        const existingRows = container.querySelectorAll('.paciente-row');
        existingRows.forEach(function(row) {
            initRowListeners(row);
        });
    }
}

// Configura el comportamiento de una fila de paciente
function initRowListeners(rowElement) {
    if (!rowElement) return;
    
    // 1. Lógica Destino -> Dirección
    const destinoSelect = rowElement.querySelector('.destino-selector');
    const dirContainer = rowElement.querySelector('.container-direccion');
    const dirInput = rowElement.querySelector('.direccion-input');

    if (destinoSelect) {
        const handleDestinoChange = function() {
            // Mostrar input si es Domicilio u Otro
            if (this.value === 'DOMICILIO' || this.value === 'OTRO') {
                if (dirContainer) dirContainer.style.display = 'block';
                if (dirInput) {
                    dirInput.setAttribute('required', 'required');
                }
            } else {
                if (dirContainer) dirContainer.style.display = 'none';
                if (dirInput) {
                    dirInput.removeAttribute('required');
                    if (dirInput.value) dirInput.value = '';
                }
            }
            
            // Actualizar horas HBO
            setTimeout(toggleHorasHBO, 50);
        };
        
        destinoSelect.addEventListener('change', handleDestinoChange);
        
        // Trigger inicial si ya tiene valor
        if (destinoSelect.value) {
            handleDestinoChange.call(destinoSelect);
        }
    }

    // 2. Botón Quitar
    const removeBtn = rowElement.querySelector('.remove-paciente');
    if (removeBtn) {
        removeBtn.addEventListener('click', function() {
            if (rowElement && rowElement.parentNode) {
                rowElement.remove();
                // Actualizar TOTAL_FORMS
                const container = document.getElementById('pacientes-container');
                const totalFormsInput = document.getElementById('id_pacientes-TOTAL_FORMS');
                if (container && totalFormsInput) {
                    const currentForms = container.querySelectorAll('.paciente-row').length;
                    totalFormsInput.value = currentForms;
                    // Actualizar horas HBO después de eliminar
                    setTimeout(toggleHorasHBO, 100);
                }
            }
        });
    }
}

// 3. Función para verificar si algún paciente tiene destino HBO
function toggleHorasHBO() {
    const pacientesContainer = document.getElementById('pacientes-container');
    const hboContainers = document.querySelectorAll('#hbo-horas-container');
    
    if (!pacientesContainer || hboContainers.length === 0) return;
    
    // Verificar si algún paciente tiene destino HBO
    const destinoSelects = pacientesContainer.querySelectorAll('.destino-selector');
    let tieneDestinoHBO = false;
    
    destinoSelects.forEach(function(select) {
        if (select.value === 'HBO') {
            tieneDestinoHBO = true;
        }
    });
    
    // Mostrar u ocultar contenedores
    hboContainers.forEach(container => {
        if (tieneDestinoHBO) {
            container.style.display = 'block';
        } else {
            container.style.display = 'none';
        }
    });
    
    // Manejar campos requeridos
    const horaSalidaHBO = document.querySelector('[name="hora_salida_hbo"]');
    const horaLlegadaHBO = document.querySelector('[name="hora_llegada_hbo"]');
    
    if (tieneDestinoHBO) {
        if (horaSalidaHBO) horaSalidaHBO.setAttribute('required', 'required');
        if (horaLlegadaHBO) horaLlegadaHBO.setAttribute('required', 'required');
    } else {
        if (horaSalidaHBO) {
            horaSalidaHBO.removeAttribute('required');
            if (horaSalidaHBO.value) horaSalidaHBO.value = '';
        }
        if (horaLlegadaHBO) {
            horaLlegadaHBO.removeAttribute('required');
            if (horaLlegadaHBO.value) horaLlegadaHBO.value = '';
        }
    }
}

// 4. Configurar validación del formulario
function configurarValidacionFormulario() {
    const form = document.getElementById('form-viaje');
    if (form) {
        // Agregar novalidate para desactivar validación nativa del navegador
        form.setAttribute('novalidate', 'novalidate');
        
        form.addEventListener('submit', function(event) {
            // Validar campos requeridos
            const requiredFields = form.querySelectorAll('[required]');
            let formIsValid = true;
            const errorMessages = [];
            
            requiredFields.forEach(field => {
                // Solo validar campos visibles
                if (field.offsetParent !== null && !field.value.trim()) {
                    field.classList.add('is-invalid');
                    formIsValid = false;
                    
                    // Obtener nombre del campo
                    const fieldName = field.name || field.id || 'Campo';
                    const label = form.querySelector(`label[for="${field.id}"]`) || field.previousElementSibling;
                    const labelText = label ? label.textContent : fieldName;
                    
                    errorMessages.push(`${labelText} es obligatorio`);
                } else if (field.offsetParent !== null) {
                    field.classList.remove('is-invalid');
                }
            });
            
            // Validar que haya al menos un paciente
            const pacienteRows = document.querySelectorAll('.paciente-row');
            if (pacienteRows.length === 0) {
                formIsValid = false;
                errorMessages.push('Debe agregar al menos un paciente/pasajero');
            }
            
            // Mostrar errores si los hay
            if (!formIsValid) {
                event.preventDefault();
                event.stopPropagation();
                
                // Mostrar mensaje de error
                const errorDiv = document.createElement('div');
                errorDiv.className = 'alert alert-danger mt-3';
                errorDiv.innerHTML = `
                    <h5 class="alert-heading">Hay errores en el formulario</h5>
                    <ul>
                        ${errorMessages.map(msg => `<li>${msg}</li>`).join('')}
                    </ul>
                `;
                
                // Insertar antes del formulario
                form.parentNode.insertBefore(errorDiv, form);
                
                // Hacer scroll al error
                errorDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
                
                return false;
            }
            
            return true;
        });
    }
}

