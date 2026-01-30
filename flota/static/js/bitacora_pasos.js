// static/js/bitacora_pasos.js - VERSIÓN CORREGIDA
class BitacoraPasos {
    constructor() {
        this.pasoActual = 1;
        this.totalPasos = 5;
        this.esCamioneta = false;
        this.datosFormulario = {};
        this.vehiculosData = {};
        
        this.init();
    }
    
    init() {
        this.cargarDatosVehiculos();
        this.setupEventListeners();
        this.configurarHoraPorDefecto();
        this.actualizarInterfaz();
    }

    // Agrega este método a tu clase BitacoraPasos
    actualizarCamposViaje() {
        const camposViajeAmbulancia = document.getElementById('campos-viaje-ambulancia');
        const camposViajeCamioneta = document.getElementById('campos-viaje-camioneta');
        
        if (this.esCamioneta) {
            // Ocultar campos de ambulancia, mostrar campos de camioneta
            if (camposViajeAmbulancia) camposViajeAmbulancia.style.display = 'none';
            if (camposViajeCamioneta) camposViajeCamioneta.style.display = 'block';
            
            // Hacer obligatorios los campos de camioneta
            this.marcarCampoRequerido('id_destino_camioneta', true);
            this.marcarCampoRequerido('id_hora_salida_viaje', true);
            this.marcarCampoRequerido('id_persona_movilizada', true);
            this.marcarCampoRequerido('id_motivo_camioneta', true);
            
            // Quitar requerido de campos de ambulancia
            this.marcarCampoRequerido('id_destino', false);
            this.marcarCampoRequerido('id_hora_salida', false);
            this.marcarCampoRequerido('id_tipo_servicio', false);
        } else {
            // Ocultar campos de camioneta, mostrar campos de ambulancia
            if (camposViajeAmbulancia) camposViajeAmbulancia.style.display = 'block';
            if (camposViajeCamioneta) camposViajeCamioneta.style.display = 'none';
            
            // Hacer obligatorios los campos de ambulancia
            this.marcarCampoRequerido('id_destino', true);
            this.marcarCampoRequerido('id_hora_salida', true);
            this.marcarCampoRequerido('id_tipo_servicio', true);
            
            // Quitar requerido de campos de camioneta
            this.marcarCampoRequerido('id_destino_camioneta', false);
            this.marcarCampoRequerido('id_hora_salida_viaje', false);
            this.marcarCampoRequerido('id_persona_movilizada', false);
            this.marcarCampoRequerido('id_motivo_camioneta', false);
        }
    }

    // En el método actualizarTipoVehiculo, llama a este nuevo método:
    actualizarTipoVehiculo(selectElement) {
        if (!selectElement || !selectElement.value) {
            this.esCamioneta = false;
            this.actualizarInterfazTipoVehiculo();
            return;
        }
        
        const option = selectElement.options[selectElement.selectedIndex];
        const tipoCarroceria = option.getAttribute('data-tipo');
        this.esCamioneta = (tipoCarroceria === 'Camioneta');
        
        // Actualizar campo oculto
        document.getElementById('id_es_camioneta').value = this.esCamioneta;
        
        // Actualizar información del vehículo
        this.actualizarInfoVehiculo(selectElement.value);
        
        // Actualizar interfaz según tipo
        this.actualizarInterfazTipoVehiculo();
        
        // Actualizar campos visibles según tipo
        this.actualizarCamposViaje();
        this.actualizarPaso2();
    }

    // Método auxiliar para marcar campos como requeridos
    marcarCampoRequerido(campoId, esRequerido) {
        const campo = document.getElementById(campoId);
        if (campo) {
            campo.required = esRequerido;
            if (esRequerido) {
                campo.setAttribute('required', 'required');
            } else {
                campo.removeAttribute('required');
            }
        }
    }
    
    cargarDatosVehiculos() {
        // Si no existe el endpoint, manejamos con datos locales
        const vehiculoSelect = document.getElementById('id_vehiculo');
        if (vehiculoSelect) {
            this.vehiculosData = {};
            Array.from(vehiculoSelect.options).forEach(option => {
                if (option.value) {
                    const km = option.getAttribute('data-km') || 0;
                    this.vehiculosData[option.value] = parseInt(km) || 0;
                }
            });
        }
    }
    
    setupEventListeners() {
        // Evento para cambio de vehículo
        const vehiculoSelect = document.getElementById('id_vehiculo');
        if (vehiculoSelect) {
            vehiculoSelect.addEventListener('change', (e) => {
                this.actualizarTipoVehiculo(e.target);
            });
        }
        
        // Configurar botones de navegación
        document.getElementById('btn-siguiente')?.addEventListener('click', () => this.siguientePaso());
        document.getElementById('btn-anterior')?.addEventListener('click', () => this.pasoAnterior());
        
        // Configurar cálculo de kilometraje
        document.getElementById('id_km_fin_viaje')?.addEventListener('input', () => this.calcularKilometraje());
        document.getElementById('id_km_inicio_viaje')?.addEventListener('input', () => this.calcularKilometraje());
        
        // Configurar submit del formulario
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
    
    configurarHoraPorDefecto() {
        // Hora actual como hora de salida por defecto
        const ahora = new Date();
        const horaStr = ahora.getHours().toString().padStart(2, '0') + ':' + 
                       ahora.getMinutes().toString().padStart(2, '0');
        
        const horaSalidaInput = document.getElementById('id_hora_salida');
        if (horaSalidaInput && !horaSalidaInput.value) {
            horaSalidaInput.value = horaStr;
        }
    }
    
    actualizarTipoVehiculo(selectElement) {
        if (!selectElement || !selectElement.value) {
            this.esCamioneta = false;
            this.actualizarInterfazTipoVehiculo();
            return;
        }
        
        const option = selectElement.options[selectElement.selectedIndex];
        const tipoCarroceria = option.getAttribute('data-tipo');
        this.esCamioneta = (tipoCarroceria === 'Camioneta');
        
        // Actualizar campo oculto
        const esCamionetaInput = document.getElementById('id_es_camioneta');
        if (esCamionetaInput) {
            esCamionetaInput.value = this.esCamioneta;
        }
        
        // Actualizar información del vehículo
        this.actualizarInfoVehiculo(selectElement.value);
        
        // Actualizar interfaz según tipo
        this.actualizarInterfazTipoVehiculo();
        
        // Actualizar campos visibles según tipo
        this.actualizarCamposVisibles();
    }
    
    actualizarInfoVehiculo(vehiculoId) {
        const kmActual = this.vehiculosData[vehiculoId] || 0;
        
        // Actualizar display de kilometraje
        const kmSpan = document.getElementById('km-actual');
        if (kmSpan) kmSpan.textContent = `${kmActual} km`;
        
        // Prellenar KM inicio si está vacío
        const kmInput = document.getElementById('id_km_inicio_viaje');
        if (kmInput && !kmInput.value) {
            kmInput.value = kmActual;
        }
    }
    
    actualizarInterfazTipoVehiculo() {
        const infoVehiculo = document.getElementById('info-vehiculo');
        const iconoVehiculo = document.getElementById('icono-vehiculo');
        const tituloVehiculo = document.getElementById('titulo-vehiculo');
        const descripcionVehiculo = document.getElementById('descripcion-vehiculo');
        
        if (!infoVehiculo || !iconoVehiculo || !tituloVehiculo || !descripcionVehiculo) return;
        
        if (this.esCamioneta) {
            infoVehiculo.className = 'vehiculo-info camioneta';
            iconoVehiculo.className = 'bi bi-truck fs-3 me-3 text-success';
            tituloVehiculo.textContent = 'Camioneta';
            descripcionVehiculo.textContent = 'Registrando salida de camioneta';
        } else {
            infoVehiculo.className = 'vehiculo-info';
            iconoVehiculo.className = 'bi bi-ambulance fs-3 me-3 text-primary';
            tituloVehiculo.textContent = 'Ambulancia';
            descripcionVehiculo.textContent = 'Registrando salida de ambulancia';
        }
    }
    
    actualizarCamposVisibles() {
        // Campos para ambulancia vs camioneta
        const camposAmbulancia = document.getElementById('campos-ambulancia');
        const camposCamioneta = document.getElementById('campos-camioneta');
        const tituloPaso2 = document.getElementById('titulo-paso-2');
        const ayudaPaso2 = document.getElementById('ayuda-paso-2');
        
        if (this.esCamioneta) {
            // Mostrar campos de camioneta
            if (camposAmbulancia) camposAmbulancia.style.display = 'none';
            if (camposCamioneta) camposCamioneta.style.display = 'block';
            if (tituloPaso2) tituloPaso2.innerHTML = '<i class="bi bi-person-badge text-success me-2"></i> Paso 2: Datos de Movilización';
            if (ayudaPaso2) ayudaPaso2.innerHTML = '<i class="bi bi-info-circle me-2"></i> Complete los datos específicos para camioneta.';
            
            // Ocultar campos específicos de ambulancia en otros pasos
            this.ocultarCamposAmbulancia();
        } else {
            // Mostrar campos de ambulancia
            if (camposAmbulancia) camposAmbulancia.style.display = 'block';
            if (camposCamioneta) camposCamioneta.style.display = 'none';
            if (tituloPaso2) tituloPaso2.innerHTML = '<i class="bi bi-people-fill text-primary me-2"></i> Paso 2: Equipo Médico';
            if (ayudaPaso2) ayudaPaso2.innerHTML = '<i class="bi bi-info-circle me-2"></i> Complete los datos del equipo médico (opcional).';
            
            // Mostrar campos específicos de ambulancia
            this.mostrarCamposAmbulancia();
        }
    }
    
    ocultarCamposAmbulancia() {
        // Ocultar campos que solo aplican a ambulancias
        const campoPaciente = document.getElementById('campo-paciente');
        const campoTipoServicio = document.getElementById('campo-tipo-servicio');
        const campoRutPaciente = document.getElementById('campo-rut-paciente');
        
        if (campoPaciente) campoPaciente.style.display = 'none';
        if (campoTipoServicio) campoTipoServicio.style.display = 'none';
        if (campoRutPaciente) campoRutPaciente.style.display = 'none';
    }
    
    mostrarCamposAmbulancia() {
        // Mostrar campos que solo aplican a ambulancias
        const campoPaciente = document.getElementById('campo-paciente');
        const campoTipoServicio = document.getElementById('campo-tipo-servicio');
        const campoRutPaciente = document.getElementById('campo-rut-paciente');
        
        if (campoPaciente) campoPaciente.style.display = 'block';
        if (campoTipoServicio) campoTipoServicio.style.display = 'block';
        if (campoRutPaciente) campoRutPaciente.style.display = 'block';
    }
    
    calcularKilometraje() {
        const inicioInput = document.getElementById('id_km_inicio_viaje');
        const finInput = document.getElementById('id_km_fin_viaje');
        const spanKm = document.getElementById('km-recorridos');
        
        if (!inicioInput || !finInput || !spanKm) return;
        
        const inicio = parseInt(inicioInput.value) || 0;
        const fin = parseInt(finInput.value) || 0;
        const recorridos = fin - inicio;
        
        if (recorridos >= 0) {
            spanKm.textContent = `${recorridos} km`;
            spanKm.className = 'fw-bold fs-5 text-success';
        } else {
            spanKm.textContent = `${recorridos} km (inválido)`;
            spanKm.className = 'fw-bold fs-5 text-danger';
        }
    }
    
    // Navegación entre pasos
    siguientePaso() {
        if (this.validarPasoActual()) {
            this.ocultarPaso(this.pasoActual);
            this.pasoActual++;
            
            // Si vamos al último paso, generar resumen
            if (this.pasoActual === this.totalPasos) {
                this.generarResumen();
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
            
            // Enfocar el primer campo del paso
            const primerCampo = pasoElement.querySelector('input, select, textarea');
            if (primerCampo) primerCampo.focus();
        }
    }
    
    ocultarPaso(numero) {
        const pasoElement = document.getElementById(`paso-${numero}`);
        if (pasoElement) {
            pasoElement.classList.remove('activo');
        }
    }
    
    actualizarInterfaz() {
        // Actualizar indicadores de pasos
        for (let i = 1; i <= this.totalPasos; i++) {
            const indicador = document.getElementById(`indicador-paso-${i}`);
            if (indicador) {
                indicador.className = 'paso-item';
                if (i < this.pasoActual) {
                    indicador.classList.add('completado');
                } else if (i === this.pasoActual) {
                    indicador.classList.add('activo');
                }
            }
        }
        
        // Actualizar barra de progreso
        const porcentaje = ((this.pasoActual - 1) / (this.totalPasos - 1)) * 100;
        const barraProgreso = document.getElementById('barra-progreso');
        if (barraProgreso) barraProgreso.style.width = `${porcentaje}%`;
        
        // Actualizar botones
        const btnAnterior = document.getElementById('btn-anterior');
        const btnSiguiente = document.getElementById('btn-siguiente');
        const btnEnviar = document.getElementById('btn-enviar');
        
        if (btnAnterior) {
            btnAnterior.disabled = (this.pasoActual === 1);
        }
        
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
    
    validarPasoActual() {
        const pasoElement = document.getElementById(`paso-${this.pasoActual}`);
        if (!pasoElement) return true;
        
        let esValido = true;
        
        // Validar campos requeridos visibles del paso
        const camposRequeridos = pasoElement.querySelectorAll('[required]');
        camposRequeridos.forEach(campo => {
            if (campo.offsetParent !== null && !campo.value.trim()) { // Solo validar si es visible
                this.mostrarError(campo.id.replace('id_', ''), 'Este campo es obligatorio');
                esValido = false;
            }
        });
        
        // Validaciones específicas por paso
        if (this.pasoActual === 4) { // Kilometraje
            const kmInicio = parseInt(document.getElementById('id_km_inicio_viaje')?.value) || 0;
            const kmFin = parseInt(document.getElementById('id_km_fin_viaje')?.value) || 0;
            
            if (kmFin <= kmInicio) {
                this.mostrarError('km_fin_viaje', 'El KM final debe ser mayor al inicial');
                esValido = false;
            }
        }
        
        // Validar campos de camioneta si aplica
        if (this.esCamioneta && this.pasoActual === 2) {
            const persona = document.getElementById('id_persona_movilizada');
            const motivo = document.getElementById('id_motivo_camioneta');
            
            if (persona && !persona.value.trim()) {
                this.mostrarError('persona_movilizada', 'Ingrese la persona movilizada');
                esValido = false;
            }
            
            if (motivo && !motivo.value.trim()) {
                this.mostrarError('motivo_camioneta', 'Ingrese el motivo del viaje');
                esValido = false;
            }
        }
        
        return esValido;
    }
    
    validarTodosLosPasos() {
        for (let i = 1; i <= this.totalPasos; i++) {
            const pasoElement = document.getElementById(`paso-${i}`);
            if (!pasoElement) continue;
            
            // Validar campos requeridos visibles
            const camposRequeridos = pasoElement.querySelectorAll('[required]');
            for (const campo of camposRequeridos) {
                if (campo.offsetParent !== null && !campo.value.trim()) {
                    return false;
                }
            }
            
            // Validación específica de kilometraje
            if (i === 4) {
                const kmInicio = parseInt(document.getElementById('id_km_inicio_viaje')?.value) || 0;
                const kmFin = parseInt(document.getElementById('id_km_fin_viaje')?.value) || 0;
                
                if (kmFin <= kmInicio) {
                    return false;
                }
            }
        }
        
        // Validar confirmación
        const checkConfirm = document.getElementById('check-confirmacion');
        if (checkConfirm && !checkConfirm.checked) {
            return false;
        }
        
        return true;
    }
    
    mostrarError(campoId, mensaje) {
        const campo = document.getElementById(`id_${campoId}`);
        const errorElement = document.getElementById(`error-${campoId}`);
        
        if (campo) {
            campo.classList.add('is-invalid');
        }
        
        if (errorElement) {
            errorElement.textContent = mensaje;
            errorElement.style.display = 'block';
        }
    }
    
    mostrarErroresFormulario() {
        // Desplazar al primer error
        const primerError = document.querySelector('.is-invalid');
        if (primerError) {
            primerError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            primerError.focus();
        }
        
        // Mostrar alerta
        const alerta = document.createElement('div');
        alerta.className = 'alert alert-danger alert-dismissible fade show mt-3';
        alerta.innerHTML = `
            <i class="bi bi-exclamation-triangle-fill"></i>
            <strong>Hay errores en el formulario.</strong> 
            Por favor corrija los campos marcados en rojo.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const form = document.getElementById('form-pasos');
        if (form) {
            form.parentNode.insertBefore(alerta, form);
        }
    }
    
    generarResumen() {
        const getVal = (id) => {
            const el = document.getElementById(id);
            return el ? (el.value || 'No especificado') : 'No especificado';
        };
        
        const getTxtSelect = (id) => {
            const el = document.getElementById(id);
            if (el && el.options && el.selectedIndex >= 0) {
                return el.options[el.selectedIndex].text;
            }
            return 'No seleccionado';
        };
        
        const kmInicio = parseInt(getVal('id_km_inicio_viaje')) || 0;
        const kmFin = parseInt(getVal('id_km_fin_viaje')) || 0;
        const kmRecorridos = Math.max(0, kmFin - kmInicio);
        
        let html = `
            <div class="table-responsive">
                <table class="table table-sm">
                    <tr>
                        <th width="30%">Vehículo:</th>
                        <td>${getTxtSelect('id_vehiculo')}</td>
                    </tr>
                    <tr>
                        <th>Fecha:</th>
                        <td>${getVal('id_fecha')}</td>
                    </tr>
                    <tr>
                        <th>Turno:</th>
                        <td>${getTxtSelect('id_turno')}</td>
                    </tr>
        `;
        
        if (this.esCamioneta) {
            html += `
                <tr>
                    <th>Persona Movilizada:</th>
                    <td>${getVal('id_persona_movilizada')}</td>
                </tr>
                <tr>
                    <th>Motivo:</th>
                    <td>${getVal('id_motivo_camioneta')}</td>
                </tr>
            `;
        } else {
            html += `
                <tr>
                    <th>Médico:</th>
                    <td>${getVal('id_medico')}</td>
                </tr>
                <tr>
                    <th>Enfermero/a:</th>
                    <td>${getVal('id_enfermero')}</td>
                </tr>
                <tr>
                    <th>TENS:</th>
                    <td>${getVal('id_tens')}</td>
                </tr>
                <tr>
                    <th>Camillero:</th>
                    <td>${getVal('id_camillero')}</td>
                </tr>
                <tr>
                    <th>Paciente:</th>
                    <td>${getVal('id_nombre_paciente')} ${getVal('id_rut_paciente') ? `(${getVal('id_rut_paciente')})` : ''}</td>
                </tr>
                <tr>
                    <th>Tipo Servicio:</th>
                    <td>${getTxtSelect('id_tipo_servicio')}</td>
                </tr>
            `;
        }
        
        html += `
                    <tr>
                        <th>Destino:</th>
                        <td>${getVal('id_destino')}</td>
                    </tr>
                    <tr>
                        <th>Hora Salida:</th>
                        <td>${getVal('id_hora_salida')}</td>
                    </tr>
                    <tr>
                        <th>Hora Llegada:</th>
                        <td>${getVal('id_hora_llegada') || 'No registrada'}</td>
                    </tr>
                    <tr class="table-info">
                        <th>KM Inicio:</th>
                        <td>${kmInicio} km</td>
                    </tr>
                    <tr class="table-info">
                        <th>KM Fin:</th>
                        <td>${kmFin} km</td>
                    </tr>
                    <tr class="table-success">
                        <th>KM Recorridos:</th>
                        <td><strong>${kmRecorridos} km</strong></td>
                    </tr>
                </table>
            </div>
        `;
        
        const resumenElement = document.getElementById('resumen-datos');
        if (resumenElement) {
            resumenElement.innerHTML = html;
        }
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    const formPasos = document.getElementById('form-pasos');
    if (formPasos) {
        window.bitacoraPasos = new BitacoraPasos();
    }
});
