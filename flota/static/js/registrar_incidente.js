class FormularioIncidentePasos {
    constructor() {
        this.pasoActual = 1;
        this.totalPasos = 3;
        this.datos = {};
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.actualizarProgreso();
        this.configurarFechaActual();
        this.configurarVehiculoInfo();
    }
    
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
    
    validarCampoObligatorio(valor, nombreCampo, esRequerido) {
        const errores = [];
        if (esRequerido && (!valor || valor.trim() === '')) {
            errores.push(`Debe ingresar ${nombreCampo}`);
        }
        return errores;
    }
    
    setupEventListeners() {
        const form = document.getElementById('form-incidente-pasos');
        if (form) {
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
        const btnSiguiente = document.getElementById('btn-incidente-siguiente');
        if (btnSiguiente) {
            btnSiguiente.addEventListener('click', () => {
                if (this.validarPasoActual()) {
                    this.siguientePaso();
                }
            });
        }
        
        // Botón Anterior
        const btnAnterior = document.getElementById('btn-incidente-anterior');
        if (btnAnterior) {
            btnAnterior.addEventListener('click', () => {
                this.pasoAnterior();
            });
        }
        
        // Validar campos al perder foco
        document.querySelectorAll('#form-incidente-pasos input, #form-incidente-pasos select, #form-incidente-pasos textarea').forEach(element => {
            element.addEventListener('blur', () => {
                if (this.obtenerPasoDesdeElemento(element) === this.pasoActual) {
                    this.validarCampo(element);
                }
            });
            
            // Permitir Enter para avanzar (excepto en textarea)
            if (element.tagName !== 'TEXTAREA') {
                element.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        if (this.validarPasoActual()) {
                            this.siguientePaso();
                        }
                    }
                });
            }
        });
    }
    
    configurarFechaActual() {
        const fechaInput = document.getElementById('id_fecha_reporte');
        if (fechaInput && !fechaInput.value) {
            const hoy = new Date().toISOString().split('T')[0];
            fechaInput.value = hoy;
        }
    }
    
    configurarVehiculoInfo() {
        const vehiculoSelect = document.getElementById('id_vehiculo');
        
        if (vehiculoSelect) {
            vehiculoSelect.addEventListener('change', function() {
                const selectedOption = this.options[this.selectedIndex];
                const marca = selectedOption.getAttribute('data-marca') || '';
                const modelo = selectedOption.getAttribute('data-modelo') || '';
                
                // Aquí podrías mostrar información adicional si lo deseas
            });
            
            if (vehiculoSelect.value) {
                const event = new Event('change');
                vehiculoSelect.dispatchEvent(event);
            }
        }
    }
    
    obtenerPasoDesdeElemento(element) {
        let pasoElement = element;
        while (pasoElement && !pasoElement.classList.contains('incidente-paso')) {
            pasoElement = pasoElement.parentElement;
        }
        
        if (pasoElement && pasoElement.id) {
            const pasoNum = parseInt(pasoElement.id.replace('incidente-paso-', ''));
            return pasoNum || 1;
        }
        return 1;
    }
    
    validarPasoActual() {
        const pasoElement = document.getElementById(`incidente-paso-${this.pasoActual}`);
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
            case 1:
                const vehiculo = document.getElementById('id_vehiculo').value;
                const vehiculoErrores = this.validarSeleccion(vehiculo, 'vehículo', true);
                if (vehiculoErrores.length > 0) {
                    vehiculoErrores.forEach(error => this.mostrarError('vehiculo', error));
                    esValido = false;
                }
                
                const fecha = document.getElementById('id_fecha_reporte').value;
                const fechaErrores = this.validarFecha(fecha, 'fecha de reporte', true);
                if (fechaErrores.length > 0) {
                    fechaErrores.forEach(error => this.mostrarError('fecha_reporte', error));
                    esValido = false;
                }
                break;
                
            case 2:
                const descripcion = document.getElementById('id_descripcion').value;
                const descripcionErrores = this.validarCampoObligatorio(descripcion, 'descripción', true);
                if (descripcionErrores.length > 0) {
                    descripcionErrores.forEach(error => this.mostrarError('descripcion', error));
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
            'vehiculo': 'Debe seleccionar un vehículo',
            'fecha_reporte': 'Debe seleccionar una fecha',
            'descripcion': 'Debe ingresar una descripción'
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
        const pasoElement = document.getElementById(`incidente-paso-${this.pasoActual}`);
        if (!pasoElement) return;
        
        const campos = pasoElement.querySelectorAll('input, select, textarea');
        
        campos.forEach(campo => {
            if (campo.id) {
                const campoId = campo.id.replace('id_', '');
                this.datos[campoId] = campo.value;
                
                const hiddenCampo = document.getElementById(`incidente_hidden_${campoId}`);
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
                this.actualizarResumenIncidente();
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
        const pasoElement = document.getElementById(`incidente-paso-${numero}`);
        if (pasoElement) {
            pasoElement.classList.add('activo');
            
            const primerCampo = pasoElement.querySelector('input, select, textarea');
            if (primerCampo) primerCampo.focus();
        }
    }
    
    ocultarPaso(numero) {
        const pasoElement = document.getElementById(`incidente-paso-${numero}`);
        if (pasoElement) {
            pasoElement.classList.remove('activo');
        }
    }
    
    actualizarProgreso() {
        const porcentaje = (this.pasoActual / this.totalPasos) * 100;
        const progresoFill = document.getElementById('incidente-progreso-fill');
        const progresoTexto = document.getElementById('incidente-progreso-texto');
        
        if (progresoFill) progresoFill.style.width = `${porcentaje}%`;
        if (progresoTexto) progresoTexto.textContent = `Paso ${this.pasoActual} de ${this.totalPasos}`;
    }
    
    actualizarBotones() {
        const btnAnterior = document.getElementById('btn-incidente-anterior');
        const btnSiguiente = document.getElementById('btn-incidente-siguiente');
        const btnEnviar = document.getElementById('btn-incidente-enviar');
        
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
    
    actualizarResumenIncidente() {
        const fecha = this.datos.fecha_reporte || '';
        const vehiculoId = this.datos.vehiculo || '';
        const descripcion = this.datos.descripcion || 'No especificada';
        
        let vehiculoNombre = 'No seleccionado';
        const vehiculoSelect = document.getElementById('id_vehiculo');
        if (vehiculoSelect && vehiculoSelect.value) {
            vehiculoNombre = vehiculoSelect.options[vehiculoSelect.selectedIndex].text;
        }
        
        // Formatear fecha
        const fechaObj = new Date(fecha);
        const fechaFormateada = fechaObj.toLocaleDateString('es-CL', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
        
        const resumenHtml = `
            <table class="table table-sm">
                <tr>
                    <th style="width: 30%">Vehículo:</th>
                    <td>${vehiculoNombre}</td>
                </tr>
                <tr>
                    <th>Fecha de reporte:</th>
                    <td>${fechaFormateada}</td>
                </tr>
                <tr>
                    <th>Descripción:</th>
                    <td>${descripcion}</td>
                </tr>
            </table>
        `;
        
        const resumenElement = document.getElementById('incidente-resumen-datos');
        if (resumenElement) {
            resumenElement.innerHTML = resumenHtml;
        }
    }
    
    validarTodosLosCamposGlobalmente() {
        const errores = [];
        
        errores.push(...this.validarSeleccion(
            document.getElementById('id_vehiculo')?.value, 
            'vehículo', 
            true
        ));
        
        errores.push(...this.validarFecha(
            document.getElementById('id_fecha_reporte')?.value, 
            'fecha de reporte', 
            true
        ));
        
        errores.push(...this.validarCampoObligatorio(
            document.getElementById('id_descripcion')?.value, 
            'descripción', 
            true
        ));
        
        return errores;
    }
    
    prepararEnvio() {
        for (const [campoId, valor] of Object.entries(this.datos)) {
            const hiddenCampo = document.getElementById(`incidente_hidden_${campoId}`);
            if (hiddenCampo) {
                hiddenCampo.value = valor;
            }
        }
        
        const selects = document.querySelectorAll('#form-incidente-pasos select');
        selects.forEach(select => {
            if (select.id) {
                const campoId = select.id.replace('id_', '');
                const hiddenCampo = document.getElementById(`incidente_hidden_${campoId}`);
                if (hiddenCampo) {
                    hiddenCampo.value = select.value;
                }
            }
        });
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    const formularioIncidentePasos = new FormularioIncidentePasos();
    
    // Limpiar errores cuando el usuario empieza a escribir
    document.querySelectorAll('#form-incidente-pasos input, #form-incidente-pasos select, #form-incidente-pasos textarea').forEach(element => {
        element.addEventListener('input', function() {
            const campoId = this.id.replace('id_', '');
            formularioIncidentePasos.ocultarError(campoId);
        });
    });
    
    // Formatear descripción (opcional)
    const descripcionInput = document.getElementById('id_descripcion');
    if (descripcionInput) {
        descripcionInput.addEventListener('input', function() {
            if (this.value.length > 1000) {
                this.value = this.value.substring(0, 1000);
            }
        });
    }
    
    // Mantener la validación original como respaldo
    const formOriginal = document.querySelector('form:not(#form-incidente-pasos)');
    if (formOriginal) {
        formOriginal.addEventListener('submit', function(e) {
            const errores = [];
            
            const formulario = new FormularioIncidentePasos();
            
            errores.push(...formulario.validarSeleccion(
                document.getElementById('id_vehiculo')?.value, 
                'vehículo', 
                true
            ));
            
            errores.push(...formulario.validarFecha(
                document.getElementById('id_fecha_reporte')?.value, 
                'fecha de reporte', 
                true
            ));
            
            errores.push(...formulario.validarCampoObligatorio(
                document.getElementById('id_descripcion')?.value, 
                'descripción', 
                true
            ));
            
            if (errores.length > 0) {
                e.preventDefault();
                formulario.mostrarErroresValidacion(errores, 'Errores en el Formulario');
            }
        });
    }
});
