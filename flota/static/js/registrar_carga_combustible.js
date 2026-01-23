/**
 * Validaciones para el formulario de registro de carga de combustible
 * CON FUNCIONALIDAD PASO A PASO
 */

class FormularioCombustiblePasos {
    constructor() {
        this.pasoActual = 1;
        this.totalPasos = 4;
        this.datos = {};
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.actualizarProgreso();
        this.configurarFechaActual();
        this.configurarVehiculoKM();
    }
    
    // **AGREGAR AQUÍ LAS FUNCIONES DE VALIDACIÓN DEL ARCHIVO ORIGINAL**
    // Por ejemplo, si tenías estas funciones:
    validarSeleccion(valor, nombreCampo, esRequerido) {
        if (esRequerido && (!valor || valor.trim() === '')) {
            return [`Debe seleccionar un ${nombreCampo}`];
        }
        return [];
    }
    
    validarFecha(valor, nombreCampo, esRequerido) {
        const errores = [];
        if (esRequerido && (!valor || valor.trim() === '')) {
            errores.push(`Debe ingresar una ${nombreCampo}`);
        } else if (valor) {
            const fechaIngresada = new Date(valor);
            const hoy = new Date();
            hoy.setHours(0, 0, 0, 0);
            if (fechaIngresada > hoy) {
                errores.push('No puede seleccionar una fecha futura');
            }
        }
        return errores;
    }
    
    validarEnteroPositivo(valor, nombreCampo, min, max, esRequerido) {
        const errores = [];
        if (esRequerido && (!valor || valor.toString().trim() === '')) {
            errores.push(`Debe ingresar ${nombreCampo}`);
        } else if (valor) {
            const num = parseInt(valor);
            if (isNaN(num) || num < min) {
                errores.push(`${nombreCampo} debe ser mayor o igual a ${min}`);
            }
            if (num > max) {
                errores.push(`${nombreCampo} debe ser menor o igual a ${max}`);
            }
        }
        return errores;
    }
    
    validarNumeroDecimal(valor, nombreCampo, min, max, esRequerido) {
        const errores = [];
        if (esRequerido && (!valor || valor.toString().trim() === '')) {
            errores.push(`Debe ingresar ${nombreCampo}`);
        } else if (valor) {
            const num = parseFloat(valor);
            if (isNaN(num) || num < min) {
                errores.push(`${nombreCampo} debe ser mayor o igual a ${min}`);
            }
            if (num > max) {
                errores.push(`${nombreCampo} debe ser menor o igual a ${max}`);
            }
        }
        return errores;
    }
    
    setupEventListeners() {
        const form = document.getElementById('form-combustible-pasos');
        if (form) {
            // Mantener la validación original como respaldo
            form.addEventListener('submit', (e) => {
                this.prepararEnvio();
                
                // Validación global antes de enviar
                const errores = this.validarTodosLosCamposGlobalmente();
                if (errores.length > 0) {
                    e.preventDefault();
                    this.mostrarErroresValidacion(errores, 'Errores en el Formulario');
                }
            });
        }

        // Botón Siguiente
        const btnSiguiente = document.getElementById('btn-combustible-siguiente');
        if (btnSiguiente) {
            btnSiguiente.addEventListener('click', () => {
                if (this.validarPasoActual()) {
                    this.siguientePaso();
                }
            });
        }
        
        // Botón Anterior
        const btnAnterior = document.getElementById('btn-combustible-anterior');
        if (btnAnterior) {
            btnAnterior.addEventListener('click', () => {
                this.pasoAnterior();
            });
        }
        
        // Validar campos al perder foco
        document.querySelectorAll('#form-combustible-pasos input, #form-combustible-pasos select').forEach(element => {
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
    
    configurarFechaActual() {
        const fechaInput = document.getElementById('id_fecha');
        if (fechaInput && !fechaInput.value) {
            const hoy = new Date().toISOString().split('T')[0];
            fechaInput.value = hoy;
        }
    }
    
    configurarVehiculoKM() {
        const vehiculoSelect = document.getElementById('id_patente_vehiculo');
        const infoVehiculoDiv = document.getElementById('info-vehiculo');
        const kmActualSpan = document.getElementById('km-actual-vehiculo');
        const kilometrajeInput = document.getElementById('id_kilometraje_al_cargar');
        
        if (vehiculoSelect) {
            vehiculoSelect.addEventListener('change', function() {
                const selectedOption = this.options[this.selectedIndex];
                const kmActual = selectedOption.getAttribute('data-km-actual') || '0';
                
                if (infoVehiculoDiv && kmActualSpan) {
                    kmActualSpan.textContent = kmActual;
                    infoVehiculoDiv.style.display = 'block';
                }
                
                if (kilometrajeInput && !kilometrajeInput.value) {
                    kilometrajeInput.value = kmActual;
                }
                
                if (kilometrajeInput) {
                    kilometrajeInput.min = kmActual;
                }
            });
            
            if (vehiculoSelect.value) {
                const event = new Event('change');
                vehiculoSelect.dispatchEvent(event);
            }
        }
    }
    
    obtenerPasoDesdeElemento(element) {
        let pasoElement = element;
        while (pasoElement && !pasoElement.classList.contains('combustible-paso')) {
            pasoElement = pasoElement.parentElement;
        }
        
        if (pasoElement && pasoElement.id) {
            const pasoNum = parseInt(pasoElement.id.replace('combustible-paso-', ''));
            return pasoNum || 1;
        }
        return 1;
    }
    
    validarPasoActual() {
        const pasoElement = document.getElementById(`combustible-paso-${this.pasoActual}`);
        if (!pasoElement) return true;
        
        let esValido = true;
        const camposRequeridos = pasoElement.querySelectorAll('[required]');
        
        camposRequeridos.forEach(campo => {
            if (!this.validarCampo(campo)) {
                esValido = false;
            }
        });
        
        // Validaciones específicas por paso usando las funciones originales
        switch (this.pasoActual) {
            case 1:
                const fecha = document.getElementById('id_fecha').value;
                const fechaErrores = this.validarFecha(fecha, 'fecha', true);
                if (fechaErrores.length > 0) {
                    fechaErrores.forEach(error => this.mostrarError('fecha', error));
                    esValido = false;
                }
                
                const vehiculo = document.getElementById('id_patente_vehiculo').value;
                const vehiculoErrores = this.validarSeleccion(vehiculo, 'vehículo', true);
                if (vehiculoErrores.length > 0) {
                    vehiculoErrores.forEach(error => this.mostrarError('patente_vehiculo', error));
                    esValido = false;
                }
                break;
                
            case 2:
                const kilometraje = document.getElementById('id_kilometraje_al_cargar').value;
                const kmErrores = this.validarEnteroPositivo(kilometraje, 'kilometraje', 0, 9999999, true);
                if (kmErrores.length > 0) {
                    kmErrores.forEach(error => this.mostrarError('kilometraje_al_cargar', error));
                    esValido = false;
                }
                
                const litros = document.getElementById('id_litros').value;
                const litrosErrores = this.validarNumeroDecimal(litros, 'litros', 0.1, 9999, true);
                if (litrosErrores.length > 0) {
                    litrosErrores.forEach(error => this.mostrarError('litros', error));
                    esValido = false;
                }
                break;
                
            case 3:
                const costo = document.getElementById('id_costo_total').value;
                const costoErrores = this.validarNumeroDecimal(costo, 'costo total', 1, 9999999, true);
                if (costoErrores.length > 0) {
                    costoErrores.forEach(error => this.mostrarError('costo_total', error));
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
        
        campo.classList.remove('campo-invalido');
        if (errorElement) {
            errorElement.classList.remove('mostrar');
        }
        return true;
    }
    
    obtenerMensajeErrorDefault(campoId) {
        const mensajes = {
            'fecha': 'Debe seleccionar una fecha',
            'patente_vehiculo': 'Debe seleccionar un vehículo',
            'kilometraje_al_cargar': 'Debe ingresar el kilometraje',
            'litros': 'Debe ingresar los litros cargados',
            'costo_total': 'Debe ingresar el monto total'
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
    
    // **FUNCIÓN ORIGINAL PARA MOSTRAR ERRORES**
    mostrarErroresValidacion(errores, titulo) {
        let alertaGlobal = document.getElementById('alerta-global');
        if (!alertaGlobal) {
            alertaGlobal = document.createElement('div');
            alertaGlobal.id = 'alerta-global';
            alertaGlobal.className = 'alert alert-danger alert-dismissible fade show';
            document.querySelector('.container-fluid').insertBefore(alertaGlobal, document.querySelector('.container-fluid').firstChild);
        }
        
        let contenido = `<h5><i class="bi bi-exclamation-triangle"></i> ${titulo}</h5><ul>`;
        errores.forEach(error => {
            contenido += `<li>${error}</li>`;
        });
        contenido += '</ul><button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
        
        alertaGlobal.innerHTML = contenido;
        alertaGlobal.classList.remove('d-none');
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
        const pasoElement = document.getElementById(`combustible-paso-${this.pasoActual}`);
        if (!pasoElement) return;
        
        const campos = pasoElement.querySelectorAll('input, select');
        
        campos.forEach(campo => {
            if (campo.id) {
                const campoId = campo.id.replace('id_', '');
                this.datos[campoId] = campo.value;
                
                const hiddenCampo = document.getElementById(`combustible_hidden_${campoId}`);
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
            
            if (this.pasoActual === this.totalPasos) {
                this.actualizarResumenCombustible();
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
        const pasoElement = document.getElementById(`combustible-paso-${numero}`);
        if (pasoElement) {
            pasoElement.classList.add('activo');
            
            const primerCampo = pasoElement.querySelector('input, select');
            if (primerCampo) primerCampo.focus();
        }
    }
    
    ocultarPaso(numero) {
        const pasoElement = document.getElementById(`combustible-paso-${numero}`);
        if (pasoElement) {
            pasoElement.classList.remove('activo');
        }
    }
    
    actualizarProgreso() {
        const porcentaje = (this.pasoActual / this.totalPasos) * 100;
        const progresoFill = document.getElementById('combustible-progreso-fill');
        const progresoTexto = document.getElementById('combustible-progreso-texto');
        
        if (progresoFill) progresoFill.style.width = `${porcentaje}%`;
        if (progresoTexto) progresoTexto.textContent = `Paso ${this.pasoActual} de ${this.totalPasos}`;
    }
    
    actualizarBotones() {
        const btnAnterior = document.getElementById('btn-combustible-anterior');
        const btnSiguiente = document.getElementById('btn-combustible-siguiente');
        const btnEnviar = document.getElementById('btn-combustible-enviar');
        
        if (btnAnterior) {
            btnAnterior.disabled = this.pasoActual === 1;
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
    
    actualizarResumenCombustible() {
        const fecha = this.datos.fecha || '';
        const vehiculoId = this.datos.patente_vehiculo || '';
        const kilometraje = this.datos.kilometraje_al_cargar || '0';
        const litros = this.datos.litros || '0';
        const costo = this.datos.costo_total || '0';
        const nroBoleta = this.datos.nro_boleta || 'No especificado';
        
        let vehiculoNombre = 'No seleccionado';
        const vehiculoSelect = document.getElementById('id_patente_vehiculo');
        if (vehiculoSelect && vehiculoSelect.value) {
            vehiculoNombre = vehiculoSelect.options[vehiculoSelect.selectedIndex].text;
        }
        
        const litrosNum = parseFloat(litros) || 1;
        const costoNum = parseFloat(costo) || 0;
        const precioLitro = litrosNum > 0 ? (costoNum / litrosNum).toFixed(2) : '0.00';
        
        const costoFormateado = new Intl.NumberFormat('es-CL', {
            style: 'currency',
            currency: 'CLP',
            minimumFractionDigits: 0
        }).format(costoNum);
        
        const precioLitroFormateado = new Intl.NumberFormat('es-CL', {
            style: 'currency',
            currency: 'CLP',
            minimumFractionDigits: 2
        }).format(precioLitro);
        
        const resumenHtml = `
            <table class="table table-sm">
                <tr>
                    <th>Fecha:</th>
                    <td>${fecha}</td>
                </tr>
                <tr>
                    <th>Vehículo:</th>
                    <td>${vehiculoNombre}</td>
                </tr>
                <tr>
                    <th>Kilometraje:</th>
                    <td>${kilometraje} km</td>
                </tr>
                <tr>
                    <th>Litros cargados:</th>
                    <td>${litros} L</td>
                </tr>
                <tr>
                    <th>Costo total:</th>
                    <td>${costoFormateado}</td>
                </tr>
                <tr>
                    <th>Precio por litro:</th>
                    <td>${precioLitroFormateado}/L</td>
                </tr>
                <tr>
                    <th>N° Boleta:</th>
                    <td>${nroBoleta}</td>
                </tr>
            </table>
        `;
        
        const resumenElement = document.getElementById('combustible-resumen-datos');
        if (resumenElement) {
            resumenElement.innerHTML = resumenHtml;
        }
    }
    
    validarTodosLosCamposGlobalmente() {
        const errores = [];
        
        // Usar las funciones de validación originales para todos los campos
        errores.push(...this.validarSeleccion(
            document.getElementById('id_patente_vehiculo')?.value, 
            'vehículo', 
            true
        ));
        
        errores.push(...this.validarFecha(
            document.getElementById('id_fecha')?.value, 
            'fecha', 
            true
        ));
        
        errores.push(...this.validarEnteroPositivo(
            document.getElementById('id_kilometraje_al_cargar')?.value, 
            'kilometraje', 
            0, 
            9999999, 
            true
        ));
        
        errores.push(...this.validarNumeroDecimal(
            document.getElementById('id_litros')?.value, 
            'litros', 
            0.1, 
            9999, 
            true
        ));
        
        errores.push(...this.validarNumeroDecimal(
            document.getElementById('id_costo_total')?.value, 
            'costo total', 
            1, 
            9999999, 
            true
        ));
        
        return errores;
    }
    
    prepararEnvio() {
        for (const [campoId, valor] of Object.entries(this.datos)) {
            const hiddenCampo = document.getElementById(`combustible_hidden_${campoId}`);
            if (hiddenCampo) {
                hiddenCampo.value = valor;
            }
        }
        
        const selects = document.querySelectorAll('#form-combustible-pasos select');
        selects.forEach(select => {
            if (select.id) {
                const campoId = select.id.replace('id_', '');
                const hiddenCampo = document.getElementById(`combustible_hidden_${campoId}`);
                if (hiddenCampo) {
                    hiddenCampo.value = select.value;
                }
            }
        });
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    const formularioCombustiblePasos = new FormularioCombustiblePasos();
    
    // Limpiar errores cuando el usuario empieza a escribir
    document.querySelectorAll('#form-combustible-pasos input, #form-combustible-pasos select').forEach(element => {
        element.addEventListener('input', function() {
            const campoId = this.id.replace('id_', '');
            formularioCombustiblePasos.ocultarError(campoId);
        });
    });
    
    // Formatear monto al perder foco
    const costoInput = document.getElementById('id_costo_total');
    if (costoInput) {
        costoInput.addEventListener('blur', function() {
            const valor = parseFloat(this.value);
            if (!isNaN(valor)) {
                this.value = Math.round(valor);
            }
        });
    }
    
    // Formatear litros al perder foco
    const litrosInput = document.getElementById('id_litros');
    if (litrosInput) {
        litrosInput.addEventListener('blur', function() {
            const valor = parseFloat(this.value);
            if (!isNaN(valor)) {
                this.value = Math.round(valor * 10) / 10;
            }
        });
    }
    
    // **MANTENER LA VALIDACIÓN ORIGINAL COMO RESPALDO**
    // Si hay un formulario no-paso-a-paso (por compatibilidad)
    const formOriginal = document.querySelector('form:not(#form-combustible-pasos)');
    if (formOriginal) {
        formOriginal.addEventListener('submit', function(e) {
            const errores = [];
            
            // Usar las funciones de validación integradas
            const formulario = new FormularioCombustiblePasos();
            
            errores.push(...formulario.validarSeleccion(
                document.getElementById('id_patente_vehiculo')?.value, 
                'vehículo', 
                true
            ));
            
            errores.push(...formulario.validarFecha(
                document.getElementById('id_fecha')?.value, 
                'fecha', 
                true
            ));
            
            errores.push(...formulario.validarEnteroPositivo(
                document.getElementById('id_kilometraje_al_cargar')?.value, 
                'kilometraje', 
                0, 
                9999999, 
                true
            ));
            
            errores.push(...formulario.validarNumeroDecimal(
                document.getElementById('id_litros')?.value, 
                'litros', 
                0.1, 
                9999, 
                true
            ));
            
            errores.push(...formulario.validarNumeroDecimal(
                document.getElementById('id_costo_total')?.value, 
                'costo total', 
                1, 
                9999999, 
                true
            ));
            
            if (errores.length > 0) {
                e.preventDefault();
                formulario.mostrarErroresValidacion(errores, 'Errores en el Formulario');
            }
        });
    }
});

