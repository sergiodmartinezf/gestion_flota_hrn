document.addEventListener('DOMContentLoaded', function() {
    initLlevaPacientes();
    initFormsetPacientes();
    restriccionesCamionetaFilas();
    
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

    // 6. Establecer hora actual en el campo hora_salida
    const horaSalidaInput = document.querySelector('[name="hora_salida"]');
    if (horaSalidaInput) {
        const ahora = new Date();
        const horas = ahora.getHours().toString().padStart(2, '0');
        const minutos = ahora.getMinutes().toString().padStart(2, '0');
        horaSalidaInput.value = `${horas}:${minutos}`;
    }

    if (window.tipoVehiculo === 'Camioneta') {
        // Cambiar etiquetas de "Paciente" a "Pasajero" en todo el formulario
        const labels = document.querySelectorAll('label');
        labels.forEach(label => {
            if (label.innerText.includes('Paciente')) {
                label.innerText = label.innerText.replace('Paciente', 'Pasajero');
            }
        });
        
        // Cambiar el título de la sección de pacientes/pasajeros
        const headerLabel = document.getElementById('paciente-label');
        if (headerLabel) headerLabel.innerText = '2. Pasajeros';
        
        // Fijar la categoría de traslado a 'Administrativo' y deshabilitar el campo (aunque esté oculto)
        // Cambiar textos específicos adicionales
        const addButton = document.getElementById('add-paciente');
        if (addButton) addButton.innerHTML = '<i class="bi bi-person-plus"></i> Agregar Pasajero';
        
        const selectLabel = document.querySelector('label[for^="id_pacientes"]') || 
                            document.querySelector('.paciente-anterior-select')?.closest('.row')?.querySelector('label');
        if (selectLabel && selectLabel.innerText.includes('Paciente')) {
            selectLabel.innerText = selectLabel.innerText.replace('Paciente', 'Pasajero');
        }
        
    }
});

/** Checkbox: el viaje incluye pacientes/pasajeros antes de poder agregar filas. */
function initLlevaPacientes() {
    const checkbox = document.getElementById('lleva-pacientes');
    const seccion = document.getElementById('seccion-pacientes');
    const addButton = document.getElementById('add-paciente');
    const container = document.getElementById('pacientes-container');
    if (!checkbox || !seccion) return;

    function aplicarEstado() {
        const activo = checkbox.checked;
        seccion.style.display = activo ? 'block' : 'none';
        if (addButton) addButton.disabled = !activo;
        if (!activo && container) {
            container.querySelectorAll('.paciente-row').forEach(row => row.remove());
            const totalFormsInput = document.getElementById('id_pacientes-TOTAL_FORMS');
            if (totalFormsInput) totalFormsInput.value = '0';
        }
    }

    checkbox.addEventListener('change', aplicarEstado);
    aplicarEstado();
}

/** Oculta categoría/sentido visualmente en camioneta (valores fijos vienen del servidor). */
function restriccionesCamionetaFilas() {
    if (window.tipoVehiculo !== 'Camioneta') return;
    document.querySelectorAll('.fila-categoria-paciente').forEach(function (row) {
        row.style.display = 'none';
    });
}

/** Por fila: mostrar origen alta solo si categoría es ALTA. */
function initFilaPaciente(row) {
    if (!row) return;
    const cat = row.querySelector('.categoria-traslado-select');
    const altaBox = row.querySelector('.container-origen-alta');
    const altaSel = row.querySelector('.detalle-origen-alta-select');
    if (!cat || !altaBox) return;

    function syncAlta() {
        if (cat.value === 'ALTA') {
            altaBox.style.display = 'block';
            if (altaSel) altaSel.setAttribute('required', 'required');
        } else {
            altaBox.style.display = 'none';
            if (altaSel) {
                altaSel.removeAttribute('required');
                altaSel.value = '';
            }
        }
    }
    cat.addEventListener('change', syncAlta);
    syncAlta();
}

// Lógica Dinámica de Pacientes (Formset)
function initFormsetPacientes() {
    const container = document.getElementById('pacientes-container');
    const addButton = document.getElementById('add-paciente');
    const totalFormsInput = document.getElementById('id_pacientes-TOTAL_FORMS');

    if (!addButton || !container || !totalFormsInput) return;

    addButton.addEventListener('click', function() {
        try {
            let formIdx = parseInt(totalFormsInput.value, 10);
            if (Number.isNaN(formIdx) || formIdx < 0) {
                formIdx = container.querySelectorAll('.paciente-row').length;
            }
            const template = document.getElementById('empty-form-template');
            if (!template) {
                console.error('No se encuentra el template vacío');
                return;
            }
            const clone = template.content.cloneNode(true);
            const newForm = clone.querySelector('.paciente-row');
            if (!newForm) {
                console.error('El template no contiene .paciente-row');
                return;
            }
            
            // Reemplazar __prefix__
            const allElements = newForm.querySelectorAll('[name], [id], [for]');
            allElements.forEach(el => {
                if (el.name) el.name = el.name.replace('__prefix__', formIdx);
                if (el.id) el.id = el.id.replace('__prefix__', formIdx);
                if (el.getAttribute('for')) el.setAttribute('for', el.getAttribute('for').replace('__prefix__', formIdx));
            });
            
            container.appendChild(newForm);
            totalFormsInput.value = formIdx + 1;
            initRowListeners(newForm);
            restriccionesCamionetaFilas();

            setTimeout(() => {
                const firstField = newForm.querySelector('input, select');
                if (firstField) firstField.focus();
            }, 50);
        } catch (e) {
            console.error('Error al agregar paciente:', e);
            if (typeof mostrarErroresValidacion === 'function') {
                mostrarErroresValidacion(
                    ['Ocurrió un error al agregar el pasajero. Recarga la página y vuelve a intentar.'],
                    'Error al agregar pasajero'
                );
            }
        }
    });

    // Delegación de eventos para formatear RUT en inputs agregados dinámicamente
    const pacientesContainer = document.getElementById('pacientes-container');
    if (pacientesContainer) {
        // Evento 'input' para formatear mientras escribe
        pacientesContainer.addEventListener('input', function(e) {
            const target = e.target;
            if (target.matches('input[name*="-rut"]') && typeof window.formatearRUT === 'function') {
                window.formatearRUT(target);
            }
        });
        // Evento 'blur' para asegurar el formato al salir del campo
        pacientesContainer.addEventListener('blur', function(e) {
            const target = e.target;
            if (target.matches('input[name*="-rut"]') && typeof window.formatearRUT === 'function') {
                window.formatearRUT(target);
            }
        }, true);
    }

    // Además, formatea los RUT que ya existan al cargar la página
    document.querySelectorAll('input[name*="-rut"]').forEach(input => {
        if (typeof window.formatearRUT === 'function') window.formatearRUT(input);
    });

    // Inicializar filas existentes
    const existingRows = container.querySelectorAll('.paciente-row');
    existingRows.forEach(row => initRowListeners(row));
}

// Configura el comportamiento de una fila de paciente
function initRowListeners(rowElement) {
    if (!rowElement) return;
    
    // Autocompletar desde pacientes anteriores
    const pacienteAnteriorSelect = rowElement.querySelector('.paciente-anterior-select');
    if (pacienteAnteriorSelect) {
        pacienteAnteriorSelect.addEventListener('change', function() {
            const opt = this.options[this.selectedIndex];
            if (!opt || !opt.value) return;
            const rut = opt.getAttribute('data-rut') || '';
            const rutInput = rowElement.querySelector('input[name*="-rut"]') || rowElement.querySelector('.paciente-rut');
            if (!rutInput) return;
            rutInput.value = rut;
            if (typeof formatearRUT === 'function') {
                formatearRUT(rutInput);
            }
        });
    }

    const rutInputReq = rowElement.querySelector('input[name*="-rut"]') || rowElement.querySelector('.paciente-rut');
    if (rutInputReq) {
        rutInputReq.setAttribute('required', 'required');
    }
    
    // Lógica Destino -> Dirección
    const destinoSelect = rowElement.querySelector('.destino-selector');
    const dirContainer = rowElement.querySelector('.container-direccion');
    const dirInput = rowElement.querySelector('.direccion-input');

    if (destinoSelect) {
        const handleDestinoChange = function() {
            if (this.value === 'DOMICILIO' || this.value === 'OTRO') {
                if (dirContainer) dirContainer.style.display = 'block';
                if (dirInput) dirInput.setAttribute('required', 'required');
            } else {
                if (dirContainer) dirContainer.style.display = 'none';
                if (dirInput) {
                    dirInput.removeAttribute('required');
                    if (dirInput.value) dirInput.value = '';
                }
            }
            setTimeout(toggleHorasHBO, 50);
        };
        destinoSelect.addEventListener('change', handleDestinoChange);
        if (destinoSelect.value) handleDestinoChange.call(destinoSelect);
    }

    // Botón Quitar
    const removeBtn = rowElement.querySelector('.remove-paciente');
    if (removeBtn) {
        removeBtn.addEventListener('click', function() {
            if (rowElement && rowElement.parentNode) {
                rowElement.remove();
                setTimeout(toggleHorasHBO, 100);
            }
        });
    }

    // Para filas dinámicas de pacientes/pasajeros en registro de viajes
    if (destinoSelect && window.tipoVehiculo === 'Camioneta') {
        const hboOption = Array.from(destinoSelect.options).find(opt => opt.value === 'HBO');
        if (hboOption && !hboOption.disabled) {
            hboOption.disabled = true;
            // Si se quiere el texto modificado, hacerlo aquí una sola vez
            if (!hboOption.hasAttribute('data-disabled')) {
                hboOption.setAttribute('data-disabled', 'true');
                hboOption.textContent += ' (no disponible)';
            }
        }
    }

    initFilaPaciente(rowElement);
}

// 3. Función para verificar si algún paciente tiene destino HBO
function toggleHorasHBO() {
    // Si es camioneta, no hacer nada
    if (window.tipoVehiculo === 'Camioneta') return;

    const pacientesContainer = document.getElementById('pacientes-container');
    const hboContainers = document.querySelectorAll('#hbo-horas-container');
    if (!pacientesContainer || hboContainers.length === 0) return;
    
    const destinoSelects = pacientesContainer.querySelectorAll('.destino-selector');
    let tieneDestinoHBO = false;
    destinoSelects.forEach(select => {
        if (select.value === 'HBO') tieneDestinoHBO = true;
    });
    
    hboContainers.forEach(container => {
        container.style.display = tieneDestinoHBO ? 'block' : 'none';
    });
    
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
    const kmSalida = document.querySelector('[name="km_salida"]');
    const kmLlegada = document.querySelector('[name="km_llegada"]');

    if (kmSalida && kmLlegada) {
        function validarKmEnTiempoReal() {
            const salida = parseInt(kmSalida.value);
            const llegada = parseInt(kmLlegada.value);
            if (!isNaN(salida) && !isNaN(llegada) && llegada < salida) {
                kmLlegada.classList.add('is-invalid');
            } else {
                kmLlegada.classList.remove('is-invalid');
            }
        }
        kmSalida.addEventListener('input', validarKmEnTiempoReal);
        kmLlegada.addEventListener('input', validarKmEnTiempoReal);
        validarKmEnTiempoReal();
    }

    const form = document.getElementById('form-viaje');
    if (!form) return;
    
    form.setAttribute('novalidate', 'novalidate');
    form.addEventListener('submit', function(event) {
        const oldAlert = form.parentNode.querySelector('.alert-danger');
        if (oldAlert) oldAlert.remove();

        let formIsValid = true;
        const errorMessages = [];
        
        // 1. Validar campos requeridos visibles
        const requiredFields = form.querySelectorAll('[required]');
        requiredFields.forEach(field => {
            if (field.offsetParent !== null && !field.value.trim()) {
                field.classList.add('is-invalid');
                formIsValid = false;
                const label = form.querySelector(`label[for="${field.id}"]`) || field.previousElementSibling;
                const labelText = label ? label.textContent.trim() : (field.name || 'Campo');
                errorMessages.push(`${labelText} es obligatorio`);
            } else if (field.offsetParent !== null) {
                field.classList.remove('is-invalid');
            }
        });
        
        // 2. Validar KM Llegada no menor que KM Salida (solo si llegada no está vacío)
        if (kmLlegada && kmLlegada.value.trim() !== '') {
            const salida = parseInt(kmSalida.value);
            const llegada = parseInt(kmLlegada.value);
            if (!isNaN(salida) && !isNaN(llegada) && llegada < salida) {
                formIsValid = false;
                errorMessages.push('El KM de llegada no puede ser menor que el KM de salida');
                kmLlegada.classList.add('is-invalid');
            } else {
                kmLlegada.classList.remove('is-invalid');
            }
        }
        
        const llevaPacientes = document.getElementById('lleva-pacientes');
        if (llevaPacientes && !llevaPacientes.checked) {
            const totalFormsInput = document.getElementById('id_pacientes-TOTAL_FORMS');
            const pacientesContainer = document.getElementById('pacientes-container');
            if (pacientesContainer) {
                pacientesContainer.querySelectorAll('.paciente-row').forEach(row => row.remove());
            }
            if (totalFormsInput) totalFormsInput.value = '0';
        } else {
            const pacienteRows = document.querySelectorAll('.paciente-row');
            pacienteRows.forEach(row => {
                const deleteCheckbox = row.querySelector('input[name*="-DELETE"]');
                const isDeleted = deleteCheckbox && deleteCheckbox.checked;
                if (!isDeleted) {
                    const rutInput = row.querySelector('input[name*="-rut"]');
                    if (rutInput) {
                        const rutVal = rutInput.value.trim();
                        if (!rutVal) {
                            formIsValid = false;
                            errorMessages.push('Complete el RUT de cada paciente/pasajero (o elimine la fila).');
                            rutInput.classList.add('is-invalid');
                        } else if (typeof validarRutChileno === 'function') {
                            const rutErrores = validarRutChileno(rutVal, 'RUT');
                            if (rutErrores.length > 0) {
                                formIsValid = false;
                                errorMessages.push(rutErrores[0]);
                                rutInput.classList.add('is-invalid');
                            }
                        }
                    }
                }
            });
        }
        
        if (!formIsValid) {
            event.preventDefault();
            event.stopPropagation();
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-danger mt-3';
            errorDiv.innerHTML = `
                <h5 class="alert-heading">Hay errores en el formulario</h5>
                <ul>
                    ${errorMessages.map(msg => `<li>${msg}</li>`).join('')}
                </ul>
            `;
            form.parentNode.insertBefore(errorDiv, form);
            errorDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
            return false;
        }
        return true;
    });
}

