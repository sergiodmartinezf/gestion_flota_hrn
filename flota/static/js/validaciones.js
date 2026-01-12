// Validaciones básicas para formularios del sistema de gestión de flota

// Función para mostrar errores de validación
function mostrarErroresValidacion(errores, titulo = 'Errores de Validación') {
    if (errores.length === 0) return false;
    
    const listaErrores = errores.map(error => `• ${error}`).join('\n');
    
    if (typeof Swal !== 'undefined' && Swal.fire) {
        Swal.fire({
            title: titulo,
            html: `<div style="text-align: left; color: #d33;">
                <p style="margin-bottom: 10px; font-weight: bold;">Por favor, corrija los siguientes errores:</p>
                <pre style="white-space: pre-wrap; font-family: inherit; color: #d33;">${listaErrores}</pre>
            </div>`,
            icon: 'error',
            confirmButtonColor: '#d33',
            confirmButtonText: 'Entendido',
            width: '500px'
        });
    } else {
        alert(`${titulo}\n\n${listaErrores}`);
    }
    
    return true;
}

// Validar campo obligatorio
function validarCampoObligatorio(valor, campo = 'campo', mostrarAlerta = false) {
    const errores = [];
    if (!valor || valor.toString().trim() === '') {
        errores.push(`El ${campo} es obligatorio`);
    }
    if (mostrarAlerta && errores.length > 0) {
        mostrarErroresValidacion(errores, `Error en ${campo}`);
    }
    return errores;
}

// Validar número entero positivo
function validarEnteroPositivo(valor, campo = 'valor', min = 0, max = 999999999, obligatorio = true, mostrarAlerta = false) {
    const errores = [];
    if (!valor && obligatorio) {
        errores.push(`El ${campo} es obligatorio`);
    } else if (valor) {
        if (isNaN(valor) || parseInt(valor) < min) {
            errores.push(`El ${campo} debe ser un número mayor o igual a ${min}`);
        } else if (parseInt(valor) > max) {
            errores.push(`El ${campo} no puede exceder ${max.toLocaleString('es-CL')}`);
        } else if (!/^\d+$/.test(valor.toString())) {
            errores.push(`El ${campo} debe ser un número entero`);
        }
    }
    if (mostrarAlerta && errores.length > 0) {
        mostrarErroresValidacion(errores, `Error en ${campo}`);
    }
    return errores;
}

// Validar número decimal
function validarNumeroDecimal(valor, campo = 'valor', min = 0, max = 999999.99, obligatorio = true, mostrarAlerta = false) {
    const errores = [];
    if (!valor && obligatorio) {
        errores.push(`El ${campo} es obligatorio`);
    } else if (valor) {
        if (isNaN(valor) || parseFloat(valor) < min) {
            errores.push(`El ${campo} debe ser un número mayor o igual a ${min}`);
        } else if (parseFloat(valor) > max) {
            errores.push(`El ${campo} no puede exceder ${max}`);
        } else if (!/^\d+(\.\d{1,2})?$/.test(valor.toString())) {
            errores.push(`El ${campo} debe tener máximo 2 decimales`);
        }
    }
    if (mostrarAlerta && errores.length > 0) {
        mostrarErroresValidacion(errores, `Error en ${campo}`);
    }
    return errores;
}

// Validar fecha
function validarFecha(fecha, campo = 'fecha', obligatorio = true, mostrarAlerta = false) {
    const errores = [];
    if (!fecha && obligatorio) {
        errores.push(`La ${campo} es obligatoria`);
    } else if (fecha) {
        const hoy = new Date();
        hoy.setHours(0, 0, 0, 0);
        const fechaIngreso = new Date(fecha);
        if (isNaN(fechaIngreso.getTime())) {
            errores.push(`La ${campo} tiene un formato inválido`);
        }
    }
    if (mostrarAlerta && errores.length > 0) {
        mostrarErroresValidacion(errores, `Error en ${campo}`);
    }
    return errores;
}

// Validar selección
function validarSeleccion(valor, campo = 'campo', obligatorio = true, mostrarAlerta = false) {
    const errores = [];
    if (obligatorio && (!valor || valor === "" || valor === "0")) {
        errores.push(`Debe seleccionar un ${campo} válido`);
    }
    if (mostrarAlerta && errores.length > 0) {
        mostrarErroresValidacion(errores, `Error en ${campo}`);
    }
    return errores;
}

// VALIDACIONES DE CONTRASEÑA NUEVAS

// Validar fortaleza de contraseña
function validarFortalezaPassword(password, campo = 'contraseña', mostrarAlerta = false) {
    const errores = [];
    
    if (!password) {
        errores.push(`La ${campo} es obligatoria`);
    } else {
        // Mínimo 8 caracteres
        if (password.length < 8) {
            errores.push(`La ${campo} debe tener al menos 8 caracteres`);
        }
        
        // Al menos una mayúscula
        if (!/[A-Z]/.test(password)) {
            errores.push(`La ${campo} debe contener al menos una letra mayúscula (A-Z)`);
        }
        
        // Al menos una minúscula
        if (!/[a-z]/.test(password)) {
            errores.push(`La ${campo} debe contener al menos una letra minúscula (a-z)`);
        }
        
        // Al menos un número
        if (!/[0-9]/.test(password)) {
            errores.push(`La ${campo} debe contener al menos un número (0-9)`);
        }
        
        // Al menos un símbolo especial (lista más completa)
        if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?~`]/.test(password)) {
            errores.push(`La ${campo} debe contener al menos un símbolo especial (ej: !@#$%^&*)`);
        }
        
        // Opcional: Validar caracteres no permitidos
        if (/[áéíóúÁÉÍÓÚñÑ]/.test(password)) {
            errores.push(`La ${campo} no debe contener caracteres acentuados ni la letra ñ`);
        }
    }
    
    if (mostrarAlerta && errores.length > 0) {
        mostrarErroresValidacion(errores, `Error en ${campo}`);
    }
    return errores;
}

// Validar coincidencia de contraseñas
function validarCoincidenciaPassword(password, confirmacion, campo1 = 'contraseña', campo2 = 'confirmación de contraseña', mostrarAlerta = false) {
    const errores = [];
    
    if (password !== confirmacion) {
        errores.push(`La ${campo1} y la ${campo2} no coinciden`);
    }
    
    if (mostrarAlerta && errores.length > 0) {
        mostrarErroresValidacion(errores, `Error en ${campo1} y ${campo2}`);
    }
    return errores;
}

// Validación completa de contraseña (fortaleza + coincidencia)
function validarPasswordCompleto(password, confirmacion, campo = 'contraseña', mostrarAlerta = false) {
    const erroresFortaleza = validarFortalezaPassword(password, campo, false);
    const erroresCoincidencia = validarCoincidenciaPassword(password, confirmacion, campo, 'confirmación de contraseña', false);
    const todosErrores = [...erroresFortaleza, ...erroresCoincidencia];
    
    if (mostrarAlerta && todosErrores.length > 0) {
        mostrarErroresValidacion(todosErrores, `Error en ${campo}`);
    }
    
    return todosErrores;
}

// Validar formulario completo
function validarFormulario(validaciones, titulo = 'Errores en el Formulario') {
    const todosLosErrores = [];
    validaciones.forEach(validacion => {
        const errores = validacion();
        todosLosErrores.push(...errores);
    });
    if (todosLosErrores.length > 0) {
        mostrarErroresValidacion(todosLosErrores, titulo);
        return false;
    }
    return true;
}
