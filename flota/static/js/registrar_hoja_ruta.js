// static/js/bitacora_pasos_simple.js
class BitacoraPasosSimple {
    constructor() {
        this.pasoActual = 1;
        this.totalPasos = 2;
        this.vehiculosData = {};
        
        this.init();
    }

    init() {
        this.cargarDatosVehiculos();
        this.setupEventListeners();
        this.actualizarInterfaz();
    }

    cargarDatosVehiculos() {
        const vehiculoSelect = document.getElementById('id_vehiculo');
        if (vehiculoSelect) {
            // Recopilar datos de kilometraje de todas las opciones
            Array.from(vehiculoSelect.options).forEach(option => {
                if (option.value) {
                    // Extraer patente del texto de la opción
                    const patente = option.value;
                    // Obtener kilometraje del atributo data-km
                    const km = option.getAttribute('data-km') || 0;
                    this.vehiculosData[patente] = parseInt(km) || 0;
                }
            });
            
            // Configurar evento change
            vehiculoSelect.addEventListener('change', (e) => {
                this.actualizarInfoVehiculo(e.target.value);
                this.actualizarKilometrajeInicial(e.target.value);
            });
            
            // Actualizar al inicio si hay un vehículo seleccionado
            if (vehiculoSelect.value) {
                this.actualizarInfoVehiculo(vehiculoSelect.value);
                this.actualizarKilometrajeInicial(vehiculoSelect.value);
            }
        }
    }
    
    actualizarInfoVehiculo(vehiculoId) {
        const kmActual = this.vehiculosData[vehiculoId] || 0;
        
        // Actualizar display de kilometraje
        const kmSpan = document.getElementById('km-actual');
        if (kmSpan) kmSpan.textContent = `${kmActual} km`;
    }
    
    actualizarKilometrajeInicial(vehiculoId) {
        const kmActual = this.vehiculosData[vehiculoId] || 0;
        const kmInput = document.getElementById('id_km_inicio');
        
        // Solo actualizar si el campo está vacío o si estamos en el paso 2
        if (kmInput && (kmInput.value === '' || this.pasoActual === 2)) {
            kmInput.value = kmActual;
        }
    }
    
    setupEventListeners() {
        // Configurar botones de navegación
        document.getElementById('btn-siguiente')?.addEventListener('click', () => this.siguientePaso());
        document.getElementById('btn-anterior')?.addEventListener('click', () => this.pasoAnterior());
        
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
    
    siguientePaso() {
        if (this.validarPasoActual()) {
            this.ocultarPaso(this.pasoActual);
            this.pasoActual++;
            
            // Si vamos al paso 2, actualizar kilometraje
            if (this.pasoActual === 2) {
                const vehiculoSelect = document.getElementById('id_vehiculo');
                if (vehiculoSelect && vehiculoSelect.value) {
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
            if (campo.offsetParent !== null && !campo.value.trim()) {
                this.mostrarError(campo.id.replace('id_', ''), 'Este campo es obligatorio');
                esValido = false;
            }
        });
        
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
        }
        
        // Validar confirmación (solo en paso 2)
        if (this.pasoActual === 2) {
            const checkConfirm = document.getElementById('check-confirmacion');
            if (checkConfirm && !checkConfirm.checked) {
                return false;
            }
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
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    const formPasos = document.getElementById('form-pasos');
    if (formPasos) {
        window.bitacoraPasos = new BitacoraPasosSimple();
    }
});
