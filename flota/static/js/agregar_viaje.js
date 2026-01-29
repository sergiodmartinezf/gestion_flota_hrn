// static/js/agregar_viaje_pasos.js
class FormularioViajePasos {
    constructor(hojaRutaId) {
        this.pasoActual = 1;
        this.totalPasos = 6;
        this.hojaRutaId = hojaRutaId;
        this.datos = {};
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.actualizarProgreso();
        this.configurarHoraActual();
        this.configurarKilometraje();
    }
    
    setupEventListeners() {
        const form = document.getElementById('form-viaje-pasos');
        if (form) {
            form.addEventListener('submit', (e) => {
                //this.prepararEnvio();
                
                if (!this.validarTodosLosCampos()) {
                    e.preventDefault();
                    this.mostrarErrorGlobal('Por favor complete todos los campos requeridos');
                }
            });
        }

        // Botón Siguiente
        const btnSiguiente = document.getElementById('btn-viaje-siguiente');
        if (btnSiguiente) {
            btnSiguiente.addEventListener('click', () => {
                if (this.validarPasoActual()) {
                    this.siguientePaso();
                }
            });
        }
        
        // Botón Anterior
        const btnAnterior = document.getElementById('btn-viaje-anterior');
        if (btnAnterior) {
            btnAnterior.addEventListener('click', () => {
                this.pasoAnterior();
            });
        }
        
        // Validar campos al perder foco
        document.querySelectorAll('#form-viaje-pasos input, #form-viaje-pasos select, #form-viaje-pasos textarea').forEach(element => {
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
    
    configurarHoraActual() {
        // Establecer hora actual por defecto en el campo de hora salida si está vacío
        const horaSalidaInput = document.getElementById('id_hora_salida');
        if (horaSalidaInput && !horaSalidaInput.value) {
            const ahora = new Date();
            const horas = ahora.getHours().toString().padStart(2, '0');
            const minutos = ahora.getMinutes().toString().padStart(2, '0');
            horaSalidaInput.value = `${horas}:${minutos}`;
        }
    }
    
    configurarKilometraje() {
        const kmInicioInput = document.getElementById('id_km_inicio_viaje');
        const kmFinInput = document.getElementById('id_km_fin_viaje');
        
        if (kmInicioInput && kmFinInput) {
            // Función para validar en tiempo real
            const validarKmEnTiempoReal = () => {
                const kmInicio = parseInt(kmInicioInput.value) || 0;
                const kmFin = parseInt(kmFinInput.value) || 0;
                
                // Calcular KM recorridos
                const kmRecorridos = Math.max(0, kmFin - kmInicio);
                const kmRecorridosSpan = document.getElementById('km-recorridos-calculados');
                if (kmRecorridosSpan) {
                    kmRecorridosSpan.textContent = kmRecorridos;
                }
                
                // Validación en tiempo real
                if (kmFin <= kmInicio) {
                    this.mostrarError('km_fin_viaje', 'El KM final debe ser MAYOR al inicial');
                    kmFinInput.classList.add('campo-invalido');
                    return false;
                } else {
                    this.ocultarError('km_fin_viaje');
                    kmFinInput.classList.remove('campo-invalido');
                    return true;
                }
            };
            
            // Validar cuando cambia el KM de inicio
            kmInicioInput.addEventListener('input', validarKmEnTiempoReal);
            kmInicioInput.addEventListener('change', validarKmEnTiempoReal);
            
            // Validar cuando cambia el KM de fin (en tiempo real)
            kmFinInput.addEventListener('input', validarKmEnTiempoReal);
            kmFinInput.addEventListener('change', validarKmEnTiempoReal);
            
            // Calcular al inicio
            validarKmEnTiempoReal();
        }
    }
    
    obtenerPasoDesdeElemento(element) {
        let pasoElement = element;
        while (pasoElement && !pasoElement.classList.contains('viaje-paso')) {
            pasoElement = pasoElement.parentElement;
        }
        
        if (pasoElement && pasoElement.id) {
            const pasoNum = parseInt(pasoElement.id.replace('viaje-paso-', ''));
            return pasoNum || 1;
        }
        return 1;
    }
    
    validarPasoActual() {
        const pasoElement = document.getElementById(`viaje-paso-${this.pasoActual}`);
        if (!pasoElement) return true;
        
        let esValido = true;
        const camposRequeridos = pasoElement.querySelectorAll('[required]');
        
        camposRequeridos.forEach(campo => {
            if (!this.validarCampo(campo)) {
                esValido = false;
            }
        });
        
        // Validaciones específicas por paso
        switch (this.pasoActual) {
            case 5: // Kilometraje
                const kmInicio = parseInt(document.getElementById('id_km_inicio_viaje').value) || 0;
                const kmFin = parseInt(document.getElementById('id_km_fin_viaje').value) || 0;
                
                if (kmFin <= kmInicio) {  // Ahora es <= para mayor estricto
                    this.mostrarError('km_fin_viaje', 'El KM final debe ser MAYOR al inicial');
                    esValido = false;
                }
                break;
                
            case 3: // Destino
                const destino = document.getElementById('id_destino').value;
                if (destino && destino.length < 3) {
                    this.mostrarError('destino', 'El destino debe tener al menos 3 caracteres');
                    esValido = false;
                }
                break;
                
            case 1: // Hora salida
                const horaSalida = document.getElementById('id_hora_salida').value;
                if (!horaSalida) {
                    this.mostrarError('hora_salida', 'Debe ingresar la hora de salida');
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
        
        // Validación específica para kilometraje
        if (campo.id === 'id_km_fin_viaje' && campo.value) {
            const kmInicio = parseInt(document.getElementById('id_km_inicio_viaje').value) || 0;
            const kmFin = parseInt(campo.value) || 0;
            
            if (kmFin <= kmInicio) {
                campo.classList.add('campo-invalido');
                if (errorElement) {
                    errorElement.textContent = 'El KM final debe ser mayor que el inicial';
                    errorElement.classList.add('mostrar');
                }
                return false;
            }
        }

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
        
        // Validación de hora
        if (campo.type === 'time' && campo.value) {
            const regexHora = /^([0-1][0-9]|2[0-3]):[0-5][0-9]$/;
            if (!regexHora.test(campo.value)) {
                campo.classList.add('campo-invalido');
                if (errorElement) {
                    errorElement.textContent = 'Formato de hora inválido (HH:MM)';
                    errorElement.classList.add('mostrar');
                }
                return false;
            }
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
            'hora_salida': 'Debe ingresar la hora de salida',
            'destino': 'Debe ingresar un destino',
            'tipo_servicio': 'Debe seleccionar un tipo de servicio',
            'km_inicio_viaje': 'Debe ingresar el KM inicial',
            'km_fin_viaje': 'Debe ingresar el KM final'
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
    
    mostrarErrorGlobal(mensaje) {
        // Crear o mostrar alerta global
        let alertaGlobal = document.getElementById('alerta-global');
        if (!alertaGlobal) {
            alertaGlobal = document.createElement('div');
            alertaGlobal.id = 'alerta-global';
            alertaGlobal.className = 'alert alert-danger alert-dismissible fade show';
            alertaGlobal.innerHTML = `
                <i class="bi bi-exclamation-triangle"></i> ${mensaje}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            const form = document.getElementById('form-viaje-pasos');
            form.parentNode.insertBefore(alertaGlobal, form);
        } else {
            alertaGlobal.innerHTML = `<i class="bi bi-exclamation-triangle"></i> ${mensaje}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
            alertaGlobal.classList.remove('d-none');
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
        const pasoElement = document.getElementById(`viaje-paso-${this.pasoActual}`);
        if (!pasoElement) return;
        
        const campos = pasoElement.querySelectorAll('input, select, textarea');
        
        campos.forEach(campo => {
            if (campo.id) {
                const campoId = campo.id.replace('id_', '');
                this.datos[campoId] = campo.value;
                
                // Copiar a campo oculto
                //const hiddenCampo = document.getElementById(`viaje_hidden_${campoId}`);
                //if (hiddenCampo) {
                //    hiddenCampo.value = campo.value;
                //}
            }
        });
    }
    
    siguientePaso() {
        if (this.pasoActual < this.totalPasos) {
            this.ocultarPaso(this.pasoActual);
            this.pasoActual++;
            
            // Si vamos al paso de resumen, actualizar los datos
            if (this.pasoActual === this.totalPasos) {
                this.actualizarResumenViaje();
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
        const pasoElement = document.getElementById(`viaje-paso-${numero}`);
        if (pasoElement) {
            pasoElement.classList.add('activo');
            
            // Enfocar el primer campo del paso
            const primerCampo = pasoElement.querySelector('input, select, textarea');
            if (primerCampo) primerCampo.focus();
        }
    }
    
    ocultarPaso(numero) {
        const pasoElement = document.getElementById(`viaje-paso-${numero}`);
        if (pasoElement) {
            pasoElement.classList.remove('activo');
        }
    }
    
    actualizarProgreso() {
        const porcentaje = (this.pasoActual / this.totalPasos) * 100;
        const progresoFill = document.getElementById('viaje-progreso-fill');
        const progresoTexto = document.getElementById('viaje-progreso-texto');
        
        if (progresoFill) progresoFill.style.width = `${porcentaje}%`;
        if (progresoTexto) progresoTexto.textContent = `Paso ${this.pasoActual} de ${this.totalPasos}`;
    }
    
    actualizarBotones() {
        const btnAnterior = document.getElementById('btn-viaje-anterior');
        const btnSiguiente = document.getElementById('btn-viaje-siguiente');
        const btnEnviar = document.getElementById('btn-viaje-enviar');
        
        // Botón Anterior
        if (btnAnterior) {
            btnAnterior.disabled = this.pasoActual === 1;
        }
        
        // Botón Siguiente/Enviar
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
    
    actualizarResumenViaje() {
        const tipoServicioTexto = this.obtenerTextoSelect('id_tipo_servicio');
        const kmInicio = parseInt(this.datos.km_inicio_viaje) || 0;
        const kmFin = parseInt(this.datos.km_fin_viaje) || 0;
        const kmRecorridos = Math.max(0, kmFin - kmInicio);
        
        const resumenHtml = `
            <table class="table table-sm">
                <tr>
                    <th>Hora Salida:</th>
                    <td>${this.datos.hora_salida || '-'}</td>
                </tr>
                <tr>
                    <th>Hora Llegada:</th>
                    <td>${this.datos.hora_llegada || 'No registrada'}</td>
                </tr>
                <tr>
                    <th>Destino:</th>
                    <td>${this.datos.destino || '-'}</td>
                </tr>
                <tr>
                    <th>Paciente:</th>
                    <td>${this.datos.nombre_paciente || 'No especificado'} ${this.datos.rut_paciente ? `(${this.datos.rut_paciente})` : ''}</td>
                </tr>
                <tr>
                    <th>Tipo Servicio:</th>
                    <td>${tipoServicioTexto}</td>
                </tr>
                <tr>
                    <th>KM Inicio:</th>
                    <td>${kmInicio} km</td>
                </tr>
                <tr>
                    <th>KM Fin:</th>
                    <td>${kmFin} km</td>
                </tr>
                <tr class="table-info">
                    <th>KM Recorridos:</th>
                    <td><strong>${kmRecorridos} km</strong></td>
                </tr>
            </table>
        `;
        
        const resumenElement = document.getElementById('viaje-resumen-datos');
        if (resumenElement) {
            resumenElement.innerHTML = resumenHtml;
        }
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
            const pasoElement = document.getElementById(`viaje-paso-${i}`);
            if (!pasoElement) continue;
            
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
            const hiddenCampo = document.getElementById(`viaje_hidden_${campoId}`);
            if (hiddenCampo) {
                hiddenCampo.value = valor;
            }
        }
    }
}

function validarKmInmediato() {
    const kmInicio = parseInt(document.getElementById('id_km_inicio_viaje').value) || 0;
    const kmFin = parseInt(document.getElementById('id_km_fin_viaje').value) || 0;
    const kmIcono = document.getElementById('km-icono');
    const kmTexto = document.getElementById('km-validacion-texto');
    
    if (kmFin > kmInicio) {
        kmIcono.className = 'bi bi-check-circle-fill text-success';
        if (kmTexto) {
            kmTexto.textContent = '✓ Válido';
            kmTexto.className = 'text-success';
        }
    } else if (kmFin === kmInicio) {
        kmIcono.className = 'bi bi-exclamation-circle-fill text-warning';
        if (kmTexto) {
            kmTexto.textContent = '⚠ Debe ser MAYOR';
            kmTexto.className = 'text-warning';
        }
    } else {
        kmIcono.className = 'bi bi-x-circle-fill text-danger';
        if (kmTexto) {
            kmTexto.textContent = '✗ Inválido';
            kmTexto.className = 'text-danger';
        }
    }
}


// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    const hojaRutaId = document.getElementById('form-viaje-pasos')?.dataset?.hojaRutaId;
    if (hojaRutaId) {
        const formularioViajePasos = new FormularioViajePasos(hojaRutaId);
        
        // Limpiar errores cuando el usuario empieza a escribir
        document.querySelectorAll('#form-viaje-pasos input, #form-viaje-pasos select, #form-viaje-pasos textarea').forEach(element => {
            element.addEventListener('input', function() {
                const campoId = this.id.replace('id_', '');
                formularioViajePasos.ocultarError(campoId);
            });
        });
        
        // Configurar RUT con formato automático
        const rutInput = document.getElementById('id_rut_paciente');
        if (rutInput) {
            rutInput.addEventListener('input', function(e) {
                let rut = e.target.value.replace(/[^0-9kK]/g, '');
                if (rut.length > 1) {
                    rut = rut.slice(0, -1) + '-' + rut.slice(-1);
                }
                if (rut.length > 10) {
                    rut = rut.slice(0, 10);
                }
                e.target.value = rut;
            });
        }
    }
    const kmFinInput = document.getElementById('id_km_fin_viaje');
    const kmInicioInput = document.getElementById('id_km_inicio_viaje');
    
    if (kmFinInput && kmInicioInput) {
        kmFinInput.addEventListener('input', validarKmInmediato);
        kmInicioInput.addEventListener('input', validarKmInmediato);
        // Validar al cargar
        setTimeout(validarKmInmediato, 100);
    }
});
