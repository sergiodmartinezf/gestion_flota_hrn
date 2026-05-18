/**
 * Calcula el dígito verificador de un RUT chileno (solo cuerpo numérico).
 */
function calcularDvRut(cuerpo) {
    const secuencia = [2, 3, 4, 5, 6, 7];
    let suma = 0;
    const digitos = cuerpo.split('').reverse();
    for (let i = 0; i < digitos.length; i++) {
        suma += parseInt(digitos[i], 10) * secuencia[i % 6];
    }
    const resto = suma % 11;
    const dv = 11 - resto;
    if (dv === 11) return '0';
    if (dv === 10) return 'K';
    return String(dv);
}

/**
 * Valida RUT chileno completo (cuerpo + dígito verificador).
 * @returns {string[]} lista de mensajes de error (vacía si es válido)
 */
function validarRutChileno(rut, campo = 'RUT') {
    const errores = [];
    if (!rut || rut.toString().trim() === '') {
        errores.push(`El ${campo} es obligatorio`);
        return errores;
    }
    let valor = rut.toString().trim().toUpperCase().replace(/\./g, '').replace(/\s/g, '');
    let cuerpo, dv;
    if (valor.includes('-')) {
        const partes = valor.split('-');
        if (partes.length !== 2) {
            errores.push(`El ${campo} no tiene un formato válido`);
            return errores;
        }
        cuerpo = partes[0];
        dv = partes[1];
    } else if (valor.length >= 2) {
        cuerpo = valor.slice(0, -1);
        dv = valor.slice(-1);
    } else {
        errores.push(`El ${campo} no tiene un formato válido`);
        return errores;
    }
    if (!/^\d+$/.test(cuerpo)) {
        errores.push(`El ${campo} debe contener solo números antes del guión`);
        return errores;
    }
    if (cuerpo.length < 7) {
        errores.push(`El ${campo} debe tener al menos 7 dígitos`);
        return errores;
    }
    const dvCalculado = calcularDvRut(cuerpo);
    if (dv.toUpperCase() !== dvCalculado) {
        errores.push(`El dígito verificador del ${campo} no es correcto`);
    }
    return errores;
}

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
        const htmlErrores = errores.map(error => `<li>${error}</li>`).join('');
        const contenedor = document.querySelector('main.col-md-10.main-content, .container.py-4, .container-fluid');
        if (contenedor) {
            const alertaAnterior = contenedor.querySelector('.alert-validaciones-global');
            if (alertaAnterior) alertaAnterior.remove();
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-danger alert-validaciones-global';
            alertDiv.innerHTML = `
                <strong>${titulo}</strong>
                <ul class="mb-0 mt-2">${htmlErrores}</ul>
            `;
            contenedor.insertBefore(alertDiv, contenedor.firstChild);
            alertDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
            console.error(`${titulo}: ${errores.join(' | ')}`);
        }
    }

    return true;
}

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

function validarFortalezaPassword(password, campo = 'contraseña', mostrarAlerta = false) {
    const errores = [];

    if (!password) {
        errores.push(`La ${campo} es obligatoria`);
    } else if (password.trim() === '') {
        errores.push(`La ${campo} no puede estar compuesta solo por espacios`);
    } else {
        if (password.length < 4) {
            errores.push(`La ${campo} debe tener al menos 4 caracteres`);
        }
        if (!/[0-9]/.test(password)) {
            errores.push(`La ${campo} debe contener al menos un número (0-9)`);
        }
    }

    if (mostrarAlerta && errores.length > 0) {
        mostrarErroresValidacion(errores, `Error en ${campo}`);
    }
    return errores;
}

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

function validarPasswordCompleto(password, confirmacion, campo = 'contraseña', mostrarAlerta = false) {
    const erroresFortaleza = validarFortalezaPassword(password, campo, false);
    const erroresCoincidencia = validarCoincidenciaPassword(password, confirmacion, campo, 'confirmación de contraseña', false);
    const todosErrores = [...erroresFortaleza, ...erroresCoincidencia];

    if (mostrarAlerta && todosErrores.length > 0) {
        mostrarErroresValidacion(todosErrores, `Error en ${campo}`);
    }

    return todosErrores;
}

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
