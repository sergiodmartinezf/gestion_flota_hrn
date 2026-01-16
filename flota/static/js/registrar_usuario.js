document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('registroUsuarioForm');
    if (!form) return; // Si no existe el formulario, salir
    
    // Obtener valores de los data attributes
    const passwordId = form.dataset.passwordId;
    const passwordConfirmId = form.dataset.passwordConfirmId;
    const esNuevoUsuario = form.dataset.esNuevoUsuario === 'true';
    
    // Obtener inputs usando los IDs
    const passwordInput = document.getElementById(passwordId);
    const passwordConfirmInput = document.getElementById(passwordConfirmId);
    
    // Si no existen los inputs, salir
    if (!passwordInput || !passwordConfirmInput) return;
    
    // Validar al enviar el formulario
    form.addEventListener('submit', function(event) {
        let errores = [];
        
        // Si es nuevo usuario, validar obligatoriamente
        if (esNuevoUsuario) {
            errores = validarPasswordCompleto(
                passwordInput.value, 
                passwordConfirmInput.value, 
                'contraseña', 
                false
            );
        } else {
            // Si es edición, validar solo si se ingresó alguna contraseña
            if (passwordInput.value || passwordConfirmInput.value) {
                errores = validarPasswordCompleto(
                    passwordInput.value, 
                    passwordConfirmInput.value, 
                    'contraseña', 
                    false
                );
            }
        }
        
        // Si hay errores, prevenir el envío y mostrarlos
        if (errores.length > 0) {
            event.preventDefault();
            mostrarErroresValidacion(errores, 'Errores en Contraseña');
        }
    });
    
    // Validación en tiempo real para la contraseña
    passwordInput.addEventListener('input', function() {
        const password = this.value;
        if (password.length > 0) {
            // Limpiar indicadores anteriores
            this.classList.remove('is-invalid', 'is-valid');
            
            const errores = validarFortalezaPassword(password, 'contraseña', false);
            
            if (errores.length === 0) {
                this.classList.add('is-valid');
            } else if (password.length >= 8) {
                // Solo mostrar como inválido si ya tiene longitud mínima
                this.classList.add('is-invalid');
            }
        }
    });
    
    // Validación en tiempo real para confirmación
    passwordConfirmInput.addEventListener('input', function() {
        const password = passwordInput.value;
        const confirmacion = this.value;
        
        if (password && confirmacion) {
            this.classList.remove('is-invalid', 'is-valid');
            
            const errores = validarCoincidenciaPassword(password, confirmacion, 'contraseña', 'confirmación', false);
            
            if (errores.length === 0) {
                this.classList.add('is-valid');
            } else {
                this.classList.add('is-invalid');
            }
        } else if (confirmacion.length === 0) {
            // Si está vacío, limpiar clases
            this.classList.remove('is-invalid', 'is-valid');
        }
    });
    
    // También validar la confirmación cuando cambia la contraseña principal
    passwordInput.addEventListener('input', function() {
        if (passwordConfirmInput.value) {
            // Disparar el evento de input en el campo de confirmación
            passwordConfirmInput.dispatchEvent(new Event('input'));
        }
    });
});
