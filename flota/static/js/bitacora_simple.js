class BitacoraSimple {
    constructor() {
        this.esCamioneta = false;
        this.vehiculosData = {};
        this.init();
    }
    
    init() {
        this.cargarKilometrajeVehiculos();
        this.setupEventListeners();
        this.configurarHoraPorDefecto();
        this.setupValidaciones();
    }
    
    cargarKilometrajeVehiculos() {
        fetch('/api/vehiculos-kilometraje/')
            .then(response => response.json())
            .then(data => {
                this.vehiculosData = data;
                console.log('Datos de vehículos cargados:', data);
            })
            .catch(err => console.error('Error cargando kilometraje:', err));
    }
    
    setupEventListeners() {
        // Cambio de vehículo
        const vehiculoSelect = document.getElementById('id_vehiculo');
        if (vehiculoSelect) {
            vehiculoSelect.addEventListener('change', (e) => {
                this.actualizarTipoVehiculo(e.target.value);
                this.actualizarKilometrajeVehiculo(e.target.value);
            });
            
            // Si ya hay un vehículo seleccionado (en edición)
            if (vehiculoSelect.value) {
                this.actualizarTipoVehiculo(vehiculoSelect.value);
                this.actualizarKilometrajeVehiculo(vehiculoSelect.value);
            }
        }
        
        // Cambio en KM para calcular automáticamente
        document.getElementById('id_km_inicio_viaje')?.addEventListener('input', () => this.calcularKilometraje());
        document.getElementById('id_km_fin_viaje')?.addEventListener('input', () => this.calcularKilometraje());
        
        // Validación del formulario antes de enviar
        document.getElementById('form-bitacora')?.addEventListener('submit', (e) => {
            if (!this.validarFormulario()) {
                e.preventDefault();
                this.mostrarErrores();
            } else {
                this.prepararEnvio();
            }
        });
    }
    
    configurarHoraPorDefecto() {
        // Configurar hora actual como hora de salida por defecto
        const ahora = new Date();
        const horaStr = ahora.getHours().toString().padStart(2, '0') + ':' + 
                       ahora.getMinutes().toString().padStart(2, '0');
        
        const horaSalidaInput = document.getElementById('id_hora_salida');
        if (horaSalidaInput && !horaSalidaInput.value) {
            horaSalidaInput.value = horaStr;
        }
        
        // Configurar hora de llegada 1 hora después por defecto
        const horaMasUna = new Date(ahora.getTime() + 60 * 60000);
        const horaMasUnaStr = horaMasUna.getHours().toString().padStart(2, '0') + ':' + 
                             horaMasUna.getMinutes().toString().padStart(2, '0');
        
        const horaLlegadaInput = document.getElementById('id_hora_llegada');
        if (horaLlegadaInput && !horaLlegadaInput.value) {
            horaLlegadaInput.value = horaMasUnaStr;
        }
    }
    
    actualizarTipoVehiculo(vehiculoId) {
        if (!vehiculoId) return;
        
        const select = document.getElementById('id_vehiculo');
        const option = select.options[select.selectedIndex];
        const tipoCarroceria = option.getAttribute('data-tipo');
        
        this.esCamioneta = (tipoCarroceria === 'Camioneta');
        document.getElementById('id_es_camioneta').value = this.esCamioneta;
        
        this.actualizarInterfazTipoVehiculo();

        
        if (!selectElement || !selectElement.value) {
            this.esCamioneta = false;
            this.actualizarInterfazTipoVehiculo();
            return;
        }
        
        const option = selectElement.options[selectElement.selectedIndex];
        const tipoCarroceria = option.getAttribute('data-tipo');
        this.esCamioneta = (tipoCarroceria === 'Camioneta');
        
        // IMPORTANTE: Actualizar campo oculto con valor booleano como string
        const esCamionetaInput = document.getElementById('id_es_camioneta');
        if (esCamionetaInput) {
            esCamionetaInput.value = this.esCamioneta.toString(); // "true" o "false"
            console.log('Campo es_camioneta actualizado a:', esCamionetaInput.value);
        }
    }
    
    actualizarInterfazTipoVehiculo() {
        const seccionAmbulancia = document.getElementById('seccion-ambulancia');
        const seccionCamioneta = document.getElementById('seccion-camioneta');
        const campoPaciente = document.getElementById('campo-paciente');
        const campoTipoServicio = document.getElementById('campo-tipo-servicio');
        
        // Actualizar estado del formulario
        const estadoMsg = document.getElementById('estado-formulario');
        if (estadoMsg) {
            estadoMsg.textContent = this.esCamioneta ? 
                'Registrando salida de camioneta' : 
                'Registrando salida de ambulancia';
            estadoMsg.className = this.esCamioneta ? 
                'alert alert-success' : 'alert alert-primary';
        }
        
        if (this.esCamioneta) {
            // Mostrar sección de camioneta, ocultar de ambulancia
            if (seccionAmbulancia) seccionAmbulancia.classList.remove('mostrar');
            if (seccionCamioneta) seccionCamioneta.classList.add('mostrar');
            
            // Ocultar campos específicos de ambulancia
            if (campoPaciente) campoPaciente.style.display = 'none';
            if (campoTipoServicio) campoTipoServicio.style.display = 'none';
            
            // Hacer obligatorios los campos de camioneta
            this.marcarCampoRequerido('id_persona_movilizada', true);
            this.marcarCampoRequerido('id_motivo_camioneta', true);
            
        } else {
            // Mostrar sección de ambulancia, ocultar de camioneta
            if (seccionAmbulancia) seccionAmbulancia.classList.add('mostrar');
            if (seccionCamioneta) seccionCamioneta.classList.remove('mostrar');
            
            // Mostrar campos específicos de ambulancia
            if (campoPaciente) campoPaciente.style.display = 'block';
            if (campoTipoServicio) campoTipoServicio.style.display = 'block';
            
            // Quitar requerido de campos de camioneta
            this.marcarCampoRequerido('id_persona_movilizada', false);
            this.marcarCampoRequerido('id_motivo_camioneta', false);
        }
    }
    
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
    
    actualizarKilometrajeVehiculo(vehiculoId) {
        const kmActual = this.vehiculosData[vehiculoId] || 0;
        const kmSpan = document.getElementById('km-actual-vehiculo');
        const kmInput = document.getElementById('id_km_inicio_viaje');
        
        if (kmSpan) kmSpan.textContent = `${kmActual} km`;
        if (kmInput && !kmInput.value) {
            kmInput.value = kmActual;
        }
    }
    
    calcularKilometraje() {
        const inicio = parseInt(document.getElementById('id_km_inicio_viaje').value) || 0;
        const fin = parseInt(document.getElementById('id_km_fin_viaje').value) || 0;
        const spanKm = document.getElementById('km-recorridos');
        
        if (!spanKm) return;
        
        const recorridos = fin - inicio;
        
        if (recorridos >= 0) {
            spanKm.textContent = `${recorridos} km`;
            spanKm.className = 'text-success';
        } else {
            spanKm.textContent = `Error: ${recorridos} km`;
            spanKm.className = 'text-danger';
        }
        
        // Actualizar campos ocultos de la hoja de ruta
        document.getElementById('hidden_km_inicio').value = inicio;
        document.getElementById('hidden_km_fin').value = fin;
    }
    
    setupValidaciones() {
        // Validación personalizada para KM
        const kmFinInput = document.getElementById('id_km_fin_viaje');
        if (kmFinInput) {
            kmFinInput.addEventListener('blur', () => {
                this.validarKilometraje();
            });
        }
        
        // Validación para horas
        const horaSalida = document.getElementById('id_hora_salida');
        const horaLlegada = document.getElementById('id_hora_llegada');
        
        if (horaLlegada) {
            horaLlegada.addEventListener('change', () => {
                this.validarHoras();
            });
        }
    }
    
    validarKilometraje() {
        const inicio = parseInt(document.getElementById('id_km_inicio_viaje').value) || 0;
        const fin = parseInt(document.getElementById('id_km_fin_viaje').value) || 0;
        const inputFin = document.getElementById('id_km_fin_viaje');
        
        if (fin <= inicio && fin > 0) {
            inputFin.classList.add('is-invalid');
            return false;
        } else {
            inputFin.classList.remove('is-invalid');
            return true;
        }
    }
    
    validarHoras() {
        const horaSalida = document.getElementById('id_hora_salida').value;
        const horaLlegada = document.getElementById('id_hora_llegada').value;
        
        if (horaLlegada && horaSalida > horaLlegada) {
            document.getElementById('id_hora_llegada').classList.add('is-invalid');
            return false;
        } else {
            document.getElementById('id_hora_llegada').classList.remove('is-invalid');
            return true;
        }
    }
    
    validarFormulario() {
        let esValido = true;
        
        // Validar campos requeridos
        const camposRequeridos = document.querySelectorAll('#form-bitacora [required]');
        camposRequeridos.forEach(campo => {
            if (!campo.value.trim()) {
                campo.classList.add('is-invalid');
                esValido = false;
            } else {
                campo.classList.remove('is-invalid');
            }
        });
        
        // Validaciones específicas
        if (!this.validarKilometraje()) esValido = false;
        if (!this.validarHoras()) esValido = false;
        
        // Validar confirmación
        const checkConfirm = document.getElementById('check-confirmacion');
        if (!checkConfirm.checked) {
            checkConfirm.classList.add('is-invalid');
            esValido = false;
        } else {
            checkConfirm.classList.remove('is-invalid');
        }
        
        return esValido;
    }
    
    mostrarErrores() {
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
        
        const form = document.getElementById('form-bitacora');
        form.parentNode.insertBefore(alerta, form);
        
        // Auto-eliminar la alerta después de 5 segundos
        setTimeout(() => {
            if (alerta.parentNode) {
                alerta.remove();
            }
        }, 5000);
    }
    
    prepararEnvio() {
        // Sincronizar todos los datos antes de enviar
        this.calcularKilometraje();
        
        // Deshabilitar botón para evitar doble envío
        const submitBtn = document.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Procesando...';
        }
    }
}

// Función global para actualizar tipo de vehículo
function actualizarTipoVehiculo(selectElement) {
    const bitacora = window.bitacoraApp;
    if (bitacora) {
        bitacora.actualizarTipoVehiculo(selectElement.value);
    }
}

// Función global para calcular kilometraje
function calcularKilometraje() {
    const bitacora = window.bitacoraApp;
    if (bitacora) {
        bitacora.calcularKilometraje();
    }
}

// Inicializar aplicación cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    window.bitacoraApp = new BitacoraSimple();
});
