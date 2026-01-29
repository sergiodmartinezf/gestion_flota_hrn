class FormularioUnificado {
    constructor() {
        this.pasoActual = 1;
        this.totalPasos = 6;
        this.vehiculosKilometraje = {};
        
        this.init();
    }
    
    init() {
        this.cargarDatosVehiculos();
        this.configurarHora();
        this.setupEventListeners();
        this.actualizarProgreso();
        this.prepararInputsWidgets();
    }
    
    prepararInputsWidgets() {
        // Asegurar que los inputs generados por Django tengan la clase form-control
        document.querySelectorAll('input, select, textarea').forEach(el => {
            if (!el.classList.contains('form-control') && !el.classList.contains('form-select') && !el.classList.contains('form-check-input')) {
                el.classList.add('form-control');
            }
        });
    }

    configurarHora() {
        // Poner hora actual en salida si está vacía
        const ahora = new Date();
        const horaStr = ahora.getHours().toString().padStart(2, '0') + ':' + ahora.getMinutes().toString().padStart(2, '0');
        const inputHora = document.getElementById('id_hora_salida');
        if (inputHora && !inputHora.value) inputHora.value = horaStr;
    }
    
    cargarDatosVehiculos() {
        fetch('/api/vehiculos-kilometraje/')
            .then(response => response.json())
            .then(data => {
                this.vehiculosKilometraje = data;
                
                const vehiculoSelect = document.getElementById('id_vehiculo');
                if (vehiculoSelect) {
                    vehiculoSelect.addEventListener('change', (e) => {
                        this.actualizarInfoVehiculo(e.target.value);
                    });
                    if (vehiculoSelect.value) this.actualizarInfoVehiculo(vehiculoSelect.value);
                }
            })
            .catch(err => console.error('Error API:', err));
    }
    
    actualizarInfoVehiculo(id) {
        const kmActual = this.vehiculosKilometraje[id] || 0;
        
        // Actualizar visualizador
        const spanKm = document.getElementById('span-km-actual');
        if (spanKm) spanKm.textContent = kmActual + ' km';
        
        // Actualizar inputs de KM
        const inputInicio = document.getElementById('id_km_inicio_viaje');
        const inputFin = document.getElementById('id_km_fin_viaje');
        
        if (inputInicio) {
            inputInicio.value = kmActual;
            inputInicio.min = 0; 
        }
        
        if (inputFin) {
            inputFin.min = kmActual;
            // Disparar validación si hay valor
            if (inputFin.value) this.calcularRecorrido();
        }
    }
    
    calcularRecorrido() {
        const inicio = parseInt(document.getElementById('id_km_inicio_viaje').value) || 0;
        const fin = parseInt(document.getElementById('id_km_fin_viaje').value) || 0;
        const span = document.getElementById('kms-recorridos-calc');
        
        if (!span) return;

        const diff = fin - inicio;
        if (diff >= 0) {
            span.textContent = `Recorridos: ${diff} km`;
            span.className = 'text-success fw-bold d-block mt-1';
        } else {
            span.textContent = 'Error: KM Fin menor a Inicio';
            span.className = 'text-danger fw-bold d-block mt-1';
        }
    }
    
    setupEventListeners() {
        // Cálculo de KM en tiempo real
        const kmIn = document.getElementById('id_km_inicio_viaje');
        const kmOut = document.getElementById('id_km_fin_viaje');
        
        if (kmIn) kmIn.addEventListener('input', () => this.calcularRecorrido());
        if (kmOut) kmOut.addEventListener('input', () => this.calcularRecorrido());

        // Botones Navegación
        const btnSig = document.getElementById('btn-siguiente');
        const btnAnt = document.getElementById('btn-anterior');

        if(btnSig) {
            btnSig.addEventListener('click', () => {
                if (this.validarPasoActual()) this.cambiarPaso(1);
            });
        }
        
        if(btnAnt) {
            btnAnt.addEventListener('click', () => {
                this.cambiarPaso(-1);
            });
        }
        
        // Submit
        const form = document.getElementById('form-pasos');
        if(form) {
            form.addEventListener('submit', (e) => {
                const checkConfirm = document.getElementById('check-confirmacion');
                
                if (!this.validarPasoActual() || (checkConfirm && !checkConfirm.checked)) {
                    e.preventDefault();
                    if (checkConfirm && !checkConfirm.checked) {
                        const errDiv = document.getElementById('error-confirmacion');
                        if(errDiv) errDiv.classList.add('mostrar');
                    }
                } else {
                    // Sincronizar campos ocultos para HojaRuta
                    const kmInicioHoja = document.getElementById('hidden_km_inicio_hoja');
                    const kmFinHoja = document.getElementById('hidden_km_fin_hoja');
                    
                    if(kmInicioHoja) kmInicioHoja.value = document.getElementById('id_km_inicio_viaje').value;
                    if(kmFinHoja) kmFinHoja.value = document.getElementById('id_km_fin_viaje').value;
                }
            });
        }

        // Navegación con Enter
        document.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
                e.preventDefault();
                if (this.pasoActual < this.totalPasos) {
                    const btn = document.getElementById('btn-siguiente');
                    if(btn) btn.click();
                }
            }
        });
    }
    
    validarPasoActual() {
        const pasoEl = document.getElementById(`paso-${this.pasoActual}`);
        if (!pasoEl) return true;

        const inputs = pasoEl.querySelectorAll('input[required], select[required]');
        let valido = true;
        
        inputs.forEach(input => {
            if (!input.value.trim()) {
                this.mostrarError(input, 'Este campo es obligatorio');
                valido = false;
            } else {
                this.ocultarError(input);
            }
        });

        // Validaciones específicas
        if (this.pasoActual === 4) { // Paso KM y Horas
            // 1. Kilometraje
            const inicio = parseInt(document.getElementById('id_km_inicio_viaje').value) || 0;
            const fin = parseInt(document.getElementById('id_km_fin_viaje').value) || 0;
            
            if (fin <= inicio) {
                this.mostrarError(document.getElementById('id_km_fin_viaje'), 'El KM final debe ser mayor al inicial');
                valido = false;
            }

            // 2. Horas (Validar llegada vs salida)
            const horaSalida = document.getElementById('id_hora_salida').value;
            const horaLlegadaInput = document.getElementById('id_hora_llegada');
            const horaLlegada = horaLlegadaInput ? horaLlegadaInput.value : null;

            if (horaSalida && horaLlegada) {
                if (horaLlegada < horaSalida) {
                    this.mostrarError(horaLlegadaInput, 'La hora de llegada no puede ser anterior a la salida');
                    valido = false;
                } else if (horaLlegada === horaSalida) {
                     this.mostrarError(horaLlegadaInput, 'La hora de llegada debe ser posterior a la salida');
                     valido = false;
                }
            }
        }

        return valido;
    }
    
    mostrarError(input, msg) {
        input.classList.add('campo-invalido');
        // Buscar div de error hermano o por ID
        let errorDiv = input.parentElement.querySelector('.error-mensaje');
        if (!errorDiv && input.id) errorDiv = document.getElementById(`error-${input.id.replace('id_', '')}`);
        
        if (errorDiv) {
            errorDiv.textContent = msg;
            errorDiv.classList.add('mostrar');
        }
    }
    
    ocultarError(input) {
        input.classList.remove('campo-invalido');
        let errorDiv = input.parentElement.querySelector('.error-mensaje');
        if (!errorDiv && input.id) errorDiv = document.getElementById(`error-${input.id.replace('id_', '')}`);
        if (errorDiv) errorDiv.classList.remove('mostrar');
    }
    
    cambiarPaso(direccion) {
        const pasoActualEl = document.getElementById(`paso-${this.pasoActual}`);
        if(pasoActualEl) pasoActualEl.classList.remove('activo');
        
        this.pasoActual += direccion;
        
        const nuevoPaso = document.getElementById(`paso-${this.pasoActual}`);
        if(nuevoPaso) {
            nuevoPaso.classList.add('activo');
            
            // Foco al primer input
            const primerInput = nuevoPaso.querySelector('input, select');
            if (primerInput) primerInput.focus();
        }

        // Lógica específica al entrar al Paso 4 (Copiar hora visual)
        if (this.pasoActual === 4) {
            const horaSalidaVal = document.getElementById('id_hora_salida').value;
            const visualSalida = document.getElementById('visual_hora_salida');
            if (visualSalida) visualSalida.value = horaSalidaVal;
            
            // Prellenar hora llegada con actual si está vacía
            const horaLlegada = document.getElementById('id_hora_llegada');
            if (horaLlegada && !horaLlegada.value) {
                const ahora = new Date();
                horaLlegada.value = ahora.getHours().toString().padStart(2, '0') + ':' + ahora.getMinutes().toString().padStart(2, '0');
            }
        }
        
        if (this.pasoActual === this.totalPasos) {
            this.generarResumen();
        }
        
        this.actualizarInterfaz();
    }
    
    actualizarInterfaz() {
        // Barra Progreso
        const porcentaje = ((this.pasoActual - 1) / (this.totalPasos - 1)) * 100;
        const progFill = document.getElementById('progreso-fill');
        const progText = document.getElementById('progreso-texto');
        
        if(progFill) progFill.style.width = `${porcentaje}%`;
        if(progText) progText.textContent = `Paso ${this.pasoActual} de ${this.totalPasos}`;
        
        // Botones
        const btnAnt = document.getElementById('btn-anterior');
        const btnSig = document.getElementById('btn-siguiente');
        const btnEnv = document.getElementById('btn-enviar');
        
        if(btnAnt) btnAnt.disabled = (this.pasoActual === 1);
        
        if (this.pasoActual === this.totalPasos) {
            if(btnSig) btnSig.style.display = 'none';
            if(btnEnv) btnEnv.style.display = 'inline-block';
        } else {
            if(btnSig) btnSig.style.display = 'inline-block';
            if(btnEnv) btnEnv.style.display = 'none';
        }
    }
    
    generarResumen() {
        const getVal = (id) => document.getElementById(id)?.value || '-';
        const getTxt = (id) => {
            const el = document.getElementById(id);
            return el && el.options && el.selectedIndex >= 0 ? el.options[el.selectedIndex].text : '-';
        };
        
        const html = `
            <div class="row">
                <div class="col-6 mb-2"><strong>Vehículo:</strong><br>${getTxt('id_vehiculo')}</div>
                <div class="col-6 mb-2"><strong>Fecha:</strong><br>${getVal('id_fecha')}</div>
                <div class="col-6 mb-2"><strong>Turno:</strong><br>${getTxt('id_turno')}</div>
                <div class="col-6 mb-2"><strong>Destino:</strong><br>${getVal('id_destino')}</div>
                <div class="col-6 mb-2"><strong>Paciente:</strong><br>${getVal('id_nombre_paciente')}</div>
                <div class="col-6 mb-2"><strong>Hora Salida:</strong><br>${getVal('id_hora_salida')}</div>
                <div class="col-6 mb-2"><strong>Hora Llegada:</strong><br>${getVal('id_hora_llegada')}</div>
                
                <div class="col-12 border-top pt-2 mt-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <span><strong>KM Inicio:</strong> ${getVal('id_km_inicio_viaje')}</span>
                        <i class="bi bi-arrow-right text-muted"></i>
                        <span><strong>KM Fin:</strong> ${getVal('id_km_fin_viaje')}</span>
                    </div>
                </div>
            </div>
        `;
        const resumenContenido = document.getElementById('resumen-contenido');
        if(resumenContenido) resumenContenido.innerHTML = html;
    }
}

document.addEventListener('DOMContentLoaded', () => new FormularioUnificado());

