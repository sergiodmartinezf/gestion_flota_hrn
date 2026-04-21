// registrar_usuario.js
// Validación del formulario de registro/edición de usuarios

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('registroUsuarioForm');
    if (!form) return;

    // Obtener IDs de campos desde data attributes
    const passwordId = form.dataset.passwordId;
    const passwordConfirmId = form.dataset.passwordConfirmId;
    const esNuevoUsuario = form.dataset.esNuevoUsuario === 'true';

    // Referencias a los inputs
    const nombreInput = document.getElementById('{{ form.nombre.id_for_label }}');
    const apellidoInput = document.getElementById('{{ form.apellido.id_for_label }}');
    const emailInput = document.getElementById('{{ form.email.id_for_label }}');
    const passwordInput = document.getElementById(passwordId);
    const passwordConfirmInput = document.getElementById(passwordConfirmId);
    const rolSelect = document.getElementById('{{ form.rol.id_for_label }}');
    const activoCheck = document.getElementById('{{ form.activo.id_for_label }}');

    // Si alguno de los campos críticos no existe, abortar
    if (!nombreInput || !apellidoInput || !emailInput || !passwordInput || !passwordConfirmInput) return;

    // Función auxiliar para mostrar errores en un elemento específico
    function mostrarErrorCampo(campo, mensaje) {
        let errorDiv = campo.parentNode.querySelector('.invalid-feedback');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback';
            campo.parentNode.appendChild(errorDiv);
        }
        errorDiv.textContent = mensaje;
        campo.classList.add('is-invalid');
    }

    function limpiarErrorCampo(campo) {
        campo.classList.remove('is-invalid');
        const errorDiv = campo.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) errorDiv.remove();
    }

    // Validación en tiempo real para campos obligatorios
    function validarCampoNoVacio(campo, nombreCampo) {
        const valor = campo.value.trim();
        if (!valor) {
            mostrarErrorCampo(campo, `El campo ${nombreCampo} es obligatorio.`);
            return false;
        } else {
            limpiarErrorCampo(campo);
            return true;
        }
    }

    nombreInput.addEventListener('input', () => validarCampoNoVacio(nombreInput, 'Nombre'));
    apellidoInput.addEventListener('input', () => validarCampoNoVacio(apellidoInput, 'Apellido'));
    emailInput.addEventListener('input', () => {
        const valor = emailInput.value.trim();
        if (!valor) {
            mostrarErrorCampo(emailInput, 'El email es obligatorio.');
        } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(valor)) {
            mostrarErrorCampo(emailInput, 'Introduzca una dirección de correo electrónico válida.');
        } else {
            limpiarErrorCampo(emailInput);
        }
    });

    // Validación de contraseña (similar a la del backend)
    function validarPassword(password) {
        const errores = [];
        const trimmed = password.trim();
        if (trimmed === '') {
            errores.push('La contraseña no puede estar compuesta solo por espacios.');
        } else {
            if (password.length < 8) errores.push('La contraseña debe tener al menos 8 caracteres.');
            if (!/[A-Z]/.test(password)) errores.push('Debe contener al menos una letra mayúscula.');
            if (!/[a-z]/.test(password)) errores.push('Debe contener al menos una letra minúscula.');
            if (!/[0-9]/.test(password)) errores.push('Debe contener al menos un número.');
            if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) errores.push('Debe contener al menos un símbolo especial.');
        }
        return errores;
    }

    function validarConfirmacion(password, confirmacion) {
        if (password !== confirmacion) return ['Las contraseñas no coinciden.'];
        return [];
    }

    passwordInput.addEventListener('input', function() {
        if (esNuevoUsuario || this.value.trim() !== '') {
            const errores = validarPassword(this.value);
            if (errores.length > 0) {
                mostrarErrorCampo(this, errores[0]); // muestra el primer error
            } else {
                limpiarErrorCampo(this);
                // También validar confirmación si tiene contenido
                if (passwordConfirmInput.value.trim() !== '') {
                    passwordConfirmInput.dispatchEvent(new Event('input'));
                }
            }
        } else {
            limpiarErrorCampo(this);
        }
    });

    passwordConfirmInput.addEventListener('input', function() {
        if (esNuevoUsuario || (passwordInput.value.trim() !== '' || this.value.trim() !== '')) {
            const errores = validarConfirmacion(passwordInput.value, this.value);
            if (errores.length > 0) {
                mostrarErrorCampo(this, errores[0]);
            } else {
                limpiarErrorCampo(this);
            }
        } else {
            limpiarErrorCampo(this);
        }
    });

    // Validación al enviar el formulario
    form.addEventListener('submit', function(event) {
        let errores = [];

        // Validar campos obligatorios
        if (!validarCampoNoVacio(nombreInput, 'Nombre')) errores.push('Nombre es obligatorio.');
        if (!validarCampoNoVacio(apellidoInput, 'Apellido')) errores.push('Apellido es obligatorio.');
        
        const emailVal = emailInput.value.trim();
        if (!emailVal) {
            mostrarErrorCampo(emailInput, 'El email es obligatorio.');
            errores.push('Email es obligatorio.');
        } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailVal)) {
            mostrarErrorCampo(emailInput, 'Email inválido.');
            errores.push('Email inválido.');
        } else {
            limpiarErrorCampo(emailInput);
        }

        // Validar contraseña según si es nuevo o edición con cambio
        if (esNuevoUsuario) {
            const passErrores = validarPassword(passwordInput.value);
            if (passErrores.length > 0) {
                mostrarErrorCampo(passwordInput, passErrores[0]);
                errores.push(...passErrores);
            } else {
                limpiarErrorCampo(passwordInput);
                const confirmErrores = validarConfirmacion(passwordInput.value, passwordConfirmInput.value);
                if (confirmErrores.length > 0) {
                    mostrarErrorCampo(passwordConfirmInput, confirmErrores[0]);
                    errores.push(...confirmErrores);
                } else {
                    limpiarErrorCampo(passwordConfirmInput);
                }
            }
        } else {
            // Edición: solo validar si se ingresó algo en alguno de los dos campos
            if (passwordInput.value.trim() !== '' || passwordConfirmInput.value.trim() !== '') {
                const passErrores = validarPassword(passwordInput.value);
                if (passErrores.length > 0) {
                    mostrarErrorCampo(passwordInput, passErrores[0]);
                    errores.push(...passErrores);
                } else {
                    limpiarErrorCampo(passwordInput);
                    const confirmErrores = validarConfirmacion(passwordInput.value, passwordConfirmInput.value);
                    if (confirmErrores.length > 0) {
                        mostrarErrorCampo(passwordConfirmInput, confirmErrores[0]);
                        errores.push(...confirmErrores);
                    } else {
                        limpiarErrorCampo(passwordConfirmInput);
                    }
                }
            } else {
                // No se ingresó contraseña, limpiamos posibles errores
                limpiarErrorCampo(passwordInput);
                limpiarErrorCampo(passwordConfirmInput);
            }
        }

        // Si hay errores, prevenir envío y mostrar resumen
        if (errores.length > 0) {
            event.preventDefault();
            // Mostrar mensaje de error general (opcional)
            let errorSummary = document.getElementById('error-summary');
            if (!errorSummary) {
                errorSummary = document.createElement('div');
                errorSummary.id = 'error-summary';
                errorSummary.className = 'alert alert-danger';
                form.insertBefore(errorSummary, form.firstChild);
            }
            errorSummary.innerHTML = '<strong>Errores en el formulario:</strong><ul>' + 
                errores.map(e => `<li>${e}</li>`).join('') + '</ul>';
            // Scroll al primer campo con error
            const firstError = form.querySelector('.is-invalid');
            if (firstError) firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
            // Limpiar resumen si existe
            const summary = document.getElementById('error-summary');
            if (summary) summary.remove();
        }
    });
});
