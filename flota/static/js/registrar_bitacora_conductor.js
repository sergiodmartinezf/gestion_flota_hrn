class FormularioPasos {
    constructor() {
        this.pasoActual = 1;
        this.totalPasos = 8;
        this.datos = {};
        this.vehiculosKilometraje = {};
        
        this.init();
    }
    
    init() {
        this.cargarDatosVehiculos();
        this.setupEventListeners();
        this.actualizarProgreso();
    }
    
    cargarDatosVehiculos() {
        fetch('/api/vehiculos-kilometraje/')
            .then(response => response.json())
            .then(data => {
                this.vehiculosKilometraje = data;
                
                // Configurar evento cuando cambia el vehículo
                const vehiculoSelect = document.getElementById('id_vehiculo');
                if (vehiculoSelect) {
                    vehiculoSelect.addEventListener('change', (e) => {
                        this.actualizarKilometrajeVehiculo(e.target.value);
                    });
                    
                    // Si ya hay un valor seleccionado, actualizar
                    if (vehiculoSelect.value) {
                        this.actualizarKilometrajeVehiculo(vehiculoSelect.value);
                    }
                }
            })
            .catch(error => console.error('Error cargando datos de vehículos:', error));
    }
    
    actualizarKilometrajeVehiculo(patente) {
        const kmActual = this.vehiculosKilometraje[patente] || 0;
        const kmActualSpan = document.getElementById('km-actual-vehiculo');
        const kmInicioInput = document.getElementById('id_km_inicio');
        const kmFinInput = document.getElementById('id_km_fin');
        
        if (kmActualSpan) kmActualSpan.textContent = kmActual;
        if (kmInicioInput) {
            kmInicioInput.value = kmActual;
            kmInicioInput.min = kmActual;
        }
        if (kmFinInput) {
            kmFinInput.min = kmActual;
            if (parseInt(kmFinInput.value) < kmActual) {
                kmFinInput.value = kmActual;
            }
        }
    }
    
    setupEventListeners() {
        const form = document.getElementById('form-pasos');
        form.addEventListener('submit', (e) => {
            // Asegurar que todos los datos estén en campos ocultos
            this.prepararEnvio();
            
            // Validar todos los campos requeridos
            if (!this.validarTodosLosCampos()) {
                e.preventDefault();
                alert('Por favor complete todos los campos requeridos');
            }
        });

        // Botón Siguiente
        document.getElementById('btn-siguiente').addEventListener('click', () => {
            if (this.validarPasoActual()) {
                this.siguientePaso();
            }
        });
        
        // Botón Anterior
        document.getElementById('btn-anterior').addEventListener('click', () => {
            this.pasoAnterior();
        });
        
        // Validar campos al perder foco
        document.querySelectorAll('#form-pasos input, #form-pasos select, #form-pasos textarea').forEach(element => {
            element.addEventListener('blur', () => {
                if (this.obtenerPasoDesdeElemento(element) === this.pasoActual) {
                    this.validarCampo(element);
                }
            });
            
            // Permitir Enter para avanzar
            element.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    if (this.validarPasoActual()) {
                        this.siguientePaso();
                    }
                }
            });
        });
    }
    
    obtenerPasoDesdeElemento(element) {
        // Buscar el paso padre del elemento
        let pasoElement = element;
        while (pasoElement && !pasoElement.classList.contains('form-paso')) {
            pasoElement = pasoElement.parentElement;
        }
        
        if (pasoElement && pasoElement.id) {
            const pasoNum = parseInt(pasoElement.id.split('-')[1]);
            return pasoNum || 1;
        }
        return 1;
    }
    
    validarPasoActual() {
        const pasoElement = document.getElementById(`paso-${this.pasoActual}`);
        let esValido = true;
        
        // Obtener todos los campos requeridos en este paso
        const camposRequeridos = pasoElement.querySelectorAll('[required]');
        
        camposRequeridos.forEach(campo => {
            if (!this.validarCampo(campo)) {
                esValido = false;
            }
        });
        
        // Validaciones específicas por paso
        switch (this.pasoActual) {
            case 4: // KM Inicio
                const kmInicio = document.getElementById('id_km_inicio').value;
                if (kmInicio < 0) {
                    this.mostrarError('km_inicio', 'El kilometraje no puede ser negativo');
                    esValido = false;
                }
                break;
                
            case 5: // KM Fin
                const kmInicioVal = parseInt(document.getElementById('id_km_inicio').value) || 0;
                const kmFin = parseInt(document.getElementById('id_km_fin').value) || 0;
                if (kmFin < kmInicioVal) {
                    this.mostrarError('km_fin', 'El KM final debe ser mayor o igual al inicial');
                    esValido = false;
                }
                break;
        }
        
        if (esValido) {
            this.guardarDatosPaso();
        }
        
        return esValido;
    }
    
    validarCampo(campo) {
        const campoId = campo.id.replace('id_', '');
        const errorElement = document.getElementById(`error-${campoId}`);
        
        if (campo.hasAttribute('required') && !campo.value.trim()) {
            campo.classList.add('campo-invalido');
            if (errorElement) {
                errorElement.textContent = this.obtenerMensajeErrorDefault(campoId);
                errorElement.classList.add('mostrar');
            }
            return false;
        }
        
        // Validaciones específicas
        if (campo.type === 'number' && campo.value < 0) {
            campo.classList.add('campo-invalido');
            if (errorElement) {
                errorElement.textContent = 'El valor no puede ser negativo';
                errorElement.classList.add('mostrar');
            }
            return false;
        }
        
        // Si pasa todas las validaciones
        campo.classList.remove('campo-invalido');
        if (errorElement) {
            errorElement.classList.remove('mostrar');
        }
        return true;
    }
    
    obtenerMensajeErrorDefault(campoId) {
        const mensajes = {
            'vehiculo': 'Debe seleccionar un vehículo',
            'fecha': 'Debe ingresar una fecha válida',
            'turno': 'Debe seleccionar un turno',
            'km_inicio': 'Debe ingresar un valor numérico positivo',
            'km_fin': 'Debe ser mayor o igual al KM inicial'
        };
        return mensajes[campoId] || 'Campo requerido';
    }
    
    mostrarError(campoId, mensaje) {
        const campo = document.getElementById(`id_${campoId}`);
        const errorElement = document.getElementById(`error-${campoId}`);
        
        if (campo) campo.classList.add('campo-invalido');
        if (errorElement) {
            errorElement.textContent = mensaje;
            errorElement.classList.add('mostrar');
        }
    }
    
    ocultarError(campoId) {
        const campo = document.getElementById(`id_${campoId}`);
        const errorElement = document.getElementById(`error-${campoId}`);
        
        if (campo) campo.classList.remove('campo-invalido');
        if (errorElement) {
            errorElement.classList.remove('mostrar');
        }
    }
    
    guardarDatosPaso() {
        const pasoElement = document.getElementById(`paso-${this.pasoActual}`);
        const campos = pasoElement.querySelectorAll('input, select, textarea');
        
        campos.forEach(campo => {
            if (campo.id) {
                const campoId = campo.id.replace('id_', '');
                this.datos[campoId] = campo.value;
                
                // Copiar a campo oculto
                const hiddenCampo = document.getElementById(`hidden_${campoId}`);
                if (hiddenCampo) {
                    hiddenCampo.value = campo.value;
                }
            }
        });
    }
    
    siguientePaso() {
        if (this.pasoActual < this.totalPasos) {
            this.ocultarPaso(this.pasoActual);
            this.pasoActual++;
            
            // Si vamos al paso de resumen, actualizar los datos
            if (this.pasoActual === 8) {
                this.actualizarResumen();
            }
            
            this.mostrarPaso(this.pasoActual);
            this.actualizarProgreso();
            this.actualizarBotones();
        }
    }
    
    pasoAnterior() {
        if (this.pasoActual > 1) {
            this.ocultarPaso(this.pasoActual);
            this.pasoActual--;
            this.mostrarPaso(this.pasoActual);
            this.actualizarProgreso();
            this.actualizarBotones();
        }
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
    
    actualizarProgreso() {
        const porcentaje = (this.pasoActual / this.totalPasos) * 100;
        const progresoFill = document.getElementById('progreso-fill');
        const progresoTexto = document.getElementById('progreso-texto');
        
        if (progresoFill) progresoFill.style.width = `${porcentaje}%`;
        if (progresoTexto) progresoTexto.textContent = `Paso ${this.pasoActual} de ${this.totalPasos}`;
    }
    
    actualizarBotones() {
        const btnAnterior = document.getElementById('btn-anterior');
        const btnSiguiente = document.getElementById('btn-siguiente');
        const btnEnviar = document.getElementById('btn-enviar');
        
        // Botón Anterior
        btnAnterior.disabled = this.pasoActual === 1;
        
        // Botón Siguiente/Enviar
        if (this.pasoActual === this.totalPasos) {
            btnSiguiente.style.display = 'none';
            btnEnviar.style.display = 'inline-block';
        } else {
            btnSiguiente.style.display = 'inline-block';
            btnEnviar.style.display = 'none';
        }
    }
    
    actualizarResumen() {
        const resumenHtml = `
            <table class="table table-sm">
                <tr>
                    <th>Vehículo:</th>
                    <td>${this.obtenerTextoSelect('id_vehiculo')}</td>
                </tr>
                <tr>
                    <th>Fecha:</th>
                    <td>${this.datos.fecha || '-'}</td>
                </tr>
                <tr>
                    <th>Turno:</th>
                    <td>${this.obtenerTextoSelect('id_turno')}</td>
                </tr>
                <tr>
                    <th>KM Inicio:</th>
                    <td>${this.datos.km_inicio || '0'} km</td>
                </tr>
                <tr>
                    <th>KM Fin estimado:</th>
                    <td>${this.datos.km_fin || '0'} km</td>
                </tr>
                <tr>
                    <th>Médico:</th>
                    <td>${this.datos.medico || 'No especificado'}</td>
                </tr>
                <tr>
                    <th>Enfermero/a:</th>
                    <td>${this.datos.enfermero || 'No especificado'}</td>
                </tr>
                <tr>
                    <th>TENS:</th>
                    <td>${this.datos.tens || 'No especificado'}</td>
                </tr>
                <tr>
                    <th>Camillero:</th>
                    <td>${this.datos.camillero || 'No especificado'}</td>
                </tr>
                <tr>
                    <th>Observaciones:</th>
                    <td>${this.datos.observaciones || 'Ninguna'}</td>
                </tr>
            </table>
        `;
        
        document.getElementById('resumen-datos').innerHTML = resumenHtml;
    }
    
    obtenerTextoSelect(selectId) {
        const select = document.getElementById(selectId);
        if (select && select.selectedIndex >= 0) {
            return select.options[select.selectedIndex].text;
        }
        return 'No seleccionado';
    }
    
    validarTodosLosCampos() {
        let esValido = true;
        
        for (let i = 1; i <= this.totalPasos; i++) {
            const pasoElement = document.getElementById(`paso-${i}`);
            const camposRequeridos = pasoElement.querySelectorAll('[required]');
            
            camposRequeridos.forEach(campo => {
                if (!this.validarCampo(campo)) {
                    esValido = false;
                }
            });
        }
        
        return esValido;
    }
    
    prepararEnvio() {
        // Copiar todos los valores a los campos ocultos
        for (const [campoId, valor] of Object.entries(this.datos)) {
            const hiddenCampo = document.getElementById(`hidden_${campoId}`);
            if (hiddenCampo) {
                hiddenCampo.value = valor;
            }
        }
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    const formularioPasos = new FormularioPasos();
    
    // Configurar fecha actual por defecto
    const fechaInput = document.getElementById('id_fecha');
    if (fechaInput && !fechaInput.value) {
        const hoy = new Date().toISOString().split('T')[0];
        fechaInput.value = hoy;
    }
    
    // Configurar KM fin igual al inicio por defecto
    const kmInicio = document.getElementById('id_km_inicio');
    const kmFin = document.getElementById('id_km_fin');
    if (kmInicio && kmFin) {
        kmInicio.addEventListener('change', function() {
            if (kmFin.value < this.value) {
                kmFin.value = this.value;
            }
        });
    }
    
    // Limpiar errores cuando el usuario empieza a escribir
    document.querySelectorAll('#form-pasos input, #form-pasos select, #form-pasos textarea').forEach(element => {
        element.addEventListener('input', function() {
            const campoId = this.id.replace('id_', '');
            formularioPasos.ocultarError(campoId);
        });
    });
});

