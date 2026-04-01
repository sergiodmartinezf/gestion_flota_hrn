/**
 * registrar_hoja_ruta.js
 * Manejo del formulario de Hoja de Ruta en 2 pasos:
 * Paso 1: Vehículo, turno y tripulación.
 * Paso 2: Confirmación y KM inicial.
 */

class BitacoraPasos {
    constructor() {
        this.pasoActual = 1;
        this.totalPasos = 2;
        this.vehiculosData = {};
        this.init();
    }

    init() {
        this.cargarDatosVehiculos();
        this.configurarCamposCondicionales();
        this.setupEventListeners();
        this.actualizarInterfaz();
        this.establecerFechaPorDefecto();
        // Si ya hay vehículo seleccionado (edición), ajustar personal
        const selectVehiculo = document.getElementById('id_vehiculo');
        if (selectVehiculo && selectVehiculo.value) {
            this.actualizarPersonalSegunVehiculo(selectVehiculo);
        }
    }

    // ------------------------------------------------------------
    // 1. Fecha por defecto
    // ------------------------------------------------------------
    establecerFechaPorDefecto() {
        const fechaInput = document.querySelector('input[name="fecha"]');
        if (fechaInput && !fechaInput.value) {
            const hoy = new Date();
            const año = hoy.getFullYear();
            const mes = String(hoy.getMonth() + 1).padStart(2, '0');
            const dia = String(hoy.getDate()).padStart(2, '0');
            fechaInput.value = `${año}-${mes}-${dia}`;
        }
    }

    // ------------------------------------------------------------
    // 2. Datos de vehículos (para KM inicial)
    // ------------------------------------------------------------
    cargarDatosVehiculos() {
        const vehiculoSelect = document.getElementById('id_vehiculo');
        if (vehiculoSelect) {
            Array.from(vehiculoSelect.options).forEach(option => {
                if (option.value) {
                    const patente = option.value;
                    const km = option.getAttribute('data-km') || 0;
                    this.vehiculosData[patente] = parseInt(km) || 0;
                }
            });
            vehiculoSelect.addEventListener('change', (e) => {
                this.actualizarInfoVehiculo(e.target.value);
                this.actualizarKilometrajeInicial(e.target.value);
                this.actualizarPersonalSegunVehiculo(e.target);
            });
        }
    }

    actualizarInfoVehiculo(vehiculoId) {
        const kmActual = this.vehiculosData[vehiculoId] || 0;
        const kmSpan = document.getElementById('km-actual');
        if (kmSpan) kmSpan.textContent = `${kmActual} km`;
    }

    actualizarKilometrajeInicial(vehiculoId) {
        const kmActual = this.vehiculosData[vehiculoId] || 0;
        const kmInput = document.getElementById('id_km_inicio');
        if (kmInput) {
            kmInput.value = kmActual;
        }
    }

    // ------------------------------------------------------------
    // 3. Lógica de personal y checkboxes "No aplica"
    // ------------------------------------------------------------
    configurarCamposCondicionales() {
        // Configurar checkboxes "No aplica" para Enfermero y Camillero
        this.manejarCheckboxCondicional('id_no_aplica_enfermero', 'id_enfermero');
        this.manejarCheckboxCondicional('id_no_aplica_camillero', 'id_camillero');
    }

    manejarCheckboxCondicional(checkboxId, campoId) {
        const check = document.getElementById(checkboxId);
        const field = document.getElementById(campoId);
        if (!check || !field) return;

        const actualizarEstado = () => {
            field.required = !check.checked;
            field.disabled = check.checked;
            if (check.checked) field.value = '';
        };

        // Estado inicial
        actualizarEstado();

        // Evento change
        check.addEventListener('change', actualizarEstado);
    }

    actualizarPersonalSegunVehiculo(selectElement) {
        const selectedOption = selectElement.options[selectElement.selectedIndex];
        if (!selectedOption || !selectedOption.value) return;

        const esCamioneta = selectedOption.text.includes('Camioneta') || 
                            (selectedOption.getAttribute('data-tipo') === 'Camioneta');
        
        const turnoSelect = document.getElementById('id_turno');
        const medicoContainer = document.getElementById('personal-medico-container');
        const adminContainer = document.getElementById('personal-administrativo-container');
        
        // Campos específicos
        const medicoField = document.getElementById('id_medico_derivador');
        const tensField = document.getElementById('id_tens');
        const enfermeroField = document.getElementById('id_enfermero');
        const camilleroField = document.getElementById('id_camillero');
        const noAplicaEnfermero = document.getElementById('id_no_aplica_enfermero');
        const noAplicaCamillero = document.getElementById('id_no_aplica_camillero');

        // --- Opciones de turno ---
        turnoSelect.innerHTML = '';
        if (esCamioneta) {
            // Solo turno administrativo
            const opt = new Option('Turno 08:00 a 17:00 (Horario Administrativo)', '08-17');
            turnoSelect.appendChild(opt);
            turnoSelect.value = '08-17';
        } else {
            // Turnos para ambulancia
            const opciones = [
                {value: '08-20', text: 'Turno 08:00 a 20:00'},
                {value: '20-08', text: 'Turno 20:00 a 08:00'},
                {value: '09-20', text: 'Turno 09:00 a 20:00 (fin de semana/feriado)'},
                {value: '20-09', text: 'Turno 20:00 a 09:00 (fin de semana/feriado)'}
            ];
            opciones.forEach(o => turnoSelect.appendChild(new Option(o.text, o.value)));
            
            // Seleccionar turno según fecha
            const fechaInput = document.querySelector('input[name="fecha"]');
            if (fechaInput && fechaInput.value) {
                const dia = new Date(fechaInput.value + 'T12:00:00').getDay();
                turnoSelect.value = (dia === 0 || dia === 6) ? '09-20' : '08-20';
            } else {
                turnoSelect.value = '08-20';
            }
        }

        // --- Visibilidad de los bloques de personal ---
        if (esCamioneta) {
            // Ocultar personal médico, mostrar mensaje administrativo
            if (medicoContainer) medicoContainer.style.display = 'none';
            if (adminContainer) adminContainer.style.display = 'block';

            // Deshabilitar TODOS los campos de personal médico y quitar required
            [medicoField, tensField, enfermeroField, camilleroField].forEach(f => {
                if (f) {
                    f.disabled = true;
                    f.required = false;
                    f.value = '';
                }
            });
            // Forzar checkboxes "No aplica" y actualizar estado
            if (noAplicaEnfermero) {
                noAplicaEnfermero.checked = true;
                noAplicaEnfermero.dispatchEvent(new Event('change'));
            }
            if (noAplicaCamillero) {
                noAplicaCamillero.checked = true;
                noAplicaCamillero.dispatchEvent(new Event('change'));
            }
        } else {
            // Mostrar personal médico
            if (medicoContainer) medicoContainer.style.display = 'block';
            if (adminContainer) adminContainer.style.display = 'none';

            // Habilitar campos y restaurar required
            if (medicoField) {
                medicoField.disabled = false;
                medicoField.required = true;
            }
            if (tensField) {
                tensField.disabled = false;
                tensField.required = true;
            }
            if (enfermeroField) enfermeroField.disabled = false;
            if (camilleroField) camilleroField.disabled = false;

            // Restablecer checkboxes a false (no marcados) y disparar evento
            if (noAplicaEnfermero) {
                noAplicaEnfermero.checked = false;
                noAplicaEnfermero.dispatchEvent(new Event('change'));
            }
            if (noAplicaCamillero) {
                noAplicaCamillero.checked = false;
                noAplicaCamillero.dispatchEvent(new Event('change'));
            }
        }
    }

    // ------------------------------------------------------------
    // 4. Navegación entre pasos
    // ------------------------------------------------------------
    setupEventListeners() {
        document.getElementById('btn-siguiente')?.addEventListener('click', () => this.siguientePaso());
        document.getElementById('btn-anterior')?.addEventListener('click', () => this.pasoAnterior());
        
        const form = document.getElementById('form-pasos');
        if (form) {
            form.addEventListener('submit', (e) => {
                if (!this.validarTodosLosPasos()) {
                    e.preventDefault();
                    this.mostrarErroresFormulario();
                }
            });
        }
    }

    siguientePaso() {
        if (this.validarPasoActual()) {
            this.ocultarPaso(this.pasoActual);
            this.pasoActual++;
            if (this.pasoActual === 2) {
                const vehiculoSelect = document.getElementById('id_vehiculo');
                if (vehiculoSelect?.value) {
                    this.actualizarKilometrajeInicial(vehiculoSelect.value);
                }
            }
            this.mostrarPaso(this.pasoActual);
            this.actualizarInterfaz();
        }
    }

    pasoAnterior() {
        this.ocultarPaso(this.pasoActual);
        this.pasoActual--;
        this.mostrarPaso(this.pasoActual);
        this.actualizarInterfaz();
    }

    mostrarPaso(numero) {
        const pasoElement = document.getElementById(`paso-${numero}`);
        if (pasoElement) {
            pasoElement.classList.add('activo');
            const primerCampo = pasoElement.querySelector('input:not([disabled]):not([type=hidden]), select:not([disabled]), textarea:not([disabled])');
            if (primerCampo) primerCampo.focus();
        }
    }

    ocultarPaso(numero) {
        const pasoElement = document.getElementById(`paso-${numero}`);
        if (pasoElement) pasoElement.classList.remove('activo');
    }

    actualizarInterfaz() {
        // Actualizar indicadores de pasos
        for (let i = 1; i <= this.totalPasos; i++) {
            const indicador = document.getElementById(`indicador-paso-${i}`);
            if (indicador) {
                indicador.className = 'paso-item';
                if (i < this.pasoActual) indicador.classList.add('completado');
                else if (i === this.pasoActual) indicador.classList.add('activo');
            }
        }
        // Barra de progreso
        const porcentaje = ((this.pasoActual - 1) / (this.totalPasos - 1)) * 100;
        const barraProgreso = document.getElementById('barra-progreso');
        if (barraProgreso) barraProgreso.style.width = `${porcentaje}%`;
        
        // Botones
        const btnAnterior = document.getElementById('btn-anterior');
        const btnSiguiente = document.getElementById('btn-siguiente');
        const btnEnviar = document.getElementById('btn-enviar');
        
        if (btnAnterior) btnAnterior.disabled = (this.pasoActual === 1);
        
        if (btnSiguiente && btnEnviar) {
            if (this.pasoActual === this.totalPasos) {
                btnSiguiente.style.display = 'none';
                btnEnviar.style.display = 'inline-block';
            } else {
                btnSiguiente.style.display = 'inline-block';
                btnEnviar.style.display = 'none';
            }
        }
    }

    // ------------------------------------------------------------
    // 5. Validaciones
    // ------------------------------------------------------------
    validarPasoActual() {
        const pasoElement = document.getElementById(`paso-${this.pasoActual}`);
        if (!pasoElement) return true;
        
        let esValido = true;
        // Limpiar errores previos
        pasoElement.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
        pasoElement.querySelectorAll('.mensaje-error').forEach(el => el.style.display = 'none');

        // Validar campos requeridos visibles y no deshabilitados
        const camposRequeridos = pasoElement.querySelectorAll('[required]');
        camposRequeridos.forEach(campo => {
            if (campo.offsetParent !== null && !campo.disabled && !campo.value.trim()) {
                this.mostrarError(campo, 'Este campo es obligatorio');
                esValido = false;
            }
        });

        // Validaciones específicas del paso 1 (personal médico)
        if (this.pasoActual === 1) {
            const vehiculoSelect = document.getElementById('id_vehiculo');
            if (vehiculoSelect && !vehiculoSelect.value) {
                this.mostrarError(vehiculoSelect, 'Seleccione un vehículo');
                esValido = false;
            }

            // Validar reglas de enfermero y camillero (solo si es ambulancia)
            const esCamioneta = this.vehiculoEsCamioneta();
            if (!esCamioneta) {
                const noAplicaEnfermero = document.getElementById('id_no_aplica_enfermero');
                const enfermero = document.getElementById('id_enfermero');
                if (noAplicaEnfermero && !noAplicaEnfermero.checked && (!enfermero || !enfermero.value.trim())) {
                    this.mostrarError(enfermero, 'Debe ingresar el nombre del Enfermero o marcar "No aplica"');
                    esValido = false;
                }

                const noAplicaCamillero = document.getElementById('id_no_aplica_camillero');
                const camillero = document.getElementById('id_camillero');
                if (noAplicaCamillero && !noAplicaCamillero.checked && (!camillero || !camillero.value.trim())) {
                    this.mostrarError(camillero, 'Debe ingresar el nombre del Camillero o marcar "No aplica"');
                    esValido = false;
                }
            }
        }

        // Validación paso 2: KM inicial y confirmación
        if (this.pasoActual === 2) {
            const kmInicio = document.getElementById('id_km_inicio');
            if (kmInicio && (!kmInicio.value || parseInt(kmInicio.value) <= 0)) {
                this.mostrarError(kmInicio, 'Ingrese un kilometraje inicial válido');
                esValido = false;
            }

            const checkConfirm = document.getElementById('check-confirmacion');
            if (checkConfirm && !checkConfirm.checked) {
                const errorDiv = document.getElementById('error-confirmacion');
                if (errorDiv) {
                    errorDiv.style.display = 'block';
                    errorDiv.textContent = 'Debe confirmar para crear la hoja de ruta';
                }
                esValido = false;
            }
        }

        return esValido;
    }

    vehiculoEsCamioneta() {
        const select = document.getElementById('id_vehiculo');
        if (!select || !select.value) return false;
        const option = select.options[select.selectedIndex];
        return option.text.includes('Camioneta') || option.getAttribute('data-tipo') === 'Camioneta';
    }

    validarTodosLosPasos() {
        // Guardar paso actual
        const pasoOriginal = this.pasoActual;
        
        // Validar paso 1
        this.pasoActual = 1;
        const paso1Valido = this.validarPasoActual();
        
        // Validar paso 2
        this.pasoActual = 2;
        const paso2Valido = this.validarPasoActual();
        
        // Restaurar paso
        this.pasoActual = pasoOriginal;
        
        return paso1Valido && paso2Valido;
    }

    mostrarError(campo, mensaje) {
        if (!campo) return;
        campo.classList.add('is-invalid');
        
        // Buscar el div de error correspondiente
        const fieldName = campo.name || campo.id;
        let errorId = '';
        if (fieldName.includes('vehiculo')) errorId = 'error-vehiculo';
        else if (fieldName.includes('fecha')) errorId = 'error-fecha';
        else if (fieldName.includes('turno')) errorId = 'error-turno';
        else if (fieldName.includes('medico')) errorId = 'error-medico_derivador';
        else if (fieldName.includes('tens')) errorId = 'error-tens';
        else if (fieldName.includes('enfermero')) errorId = 'error-enfermero';
        else if (fieldName.includes('camillero')) errorId = 'error-camillero';
        else if (fieldName.includes('km_inicio')) errorId = 'error-km_inicio';
        else if (fieldName.includes('check-confirmacion')) errorId = 'error-confirmacion';
        
        if (errorId) {
            const errorElement = document.getElementById(errorId);
            if (errorElement) {
                errorElement.textContent = mensaje;
                errorElement.style.display = 'block';
            }
        }
    }

    mostrarErroresFormulario() {
        // Remover alerta previa si existe
        const alertaExistente = document.querySelector('.alert-danger');
        if (alertaExistente) alertaExistente.remove();

        const alerta = document.createElement('div');
        alerta.className = 'alert alert-danger alert-dismissible fade show mt-3';
        alerta.innerHTML = `
            <i class="bi bi-exclamation-triangle-fill"></i>
            <strong>Hay errores en el formulario.</strong> 
            Por favor corrija los campos marcados en rojo.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const form = document.getElementById('form-pasos');
        if (form) form.parentNode.insertBefore(alerta, form);
        
        // Scroll al primer error
        const primerError = document.querySelector('.is-invalid');
        if (primerError) {
            primerError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            primerError.focus();
        }
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('form-pasos')) {
        window.bitacoraPasos = new BitacoraPasos();
    }
});
