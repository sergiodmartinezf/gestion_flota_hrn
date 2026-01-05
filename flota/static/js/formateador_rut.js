/**
 * Formateador automático de RUT chileno
 * Formato: 12.345.678-9
 */
document.addEventListener('DOMContentLoaded', function() {
    // Función para formatear RUT
    function formatearRUT(input) {
        // Remover todo excepto números y k/K
        let valor = input.value.replace(/[^0-9kK]/g, '');
        
        // Limitar a 9 caracteres (8 dígitos + 1 dígito verificador)
        if (valor.length > 9) {
            valor = valor.substring(0, 9);
        }
        
        // Si tiene más de 1 carácter, separar el dígito verificador
        if (valor.length > 1) {
            const cuerpo = valor.slice(0, -1);
            const dv = valor.slice(-1).toUpperCase();
            
            // Agregar puntos cada 3 dígitos desde la derecha
            let cuerpoFormateado = cuerpo.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
            
            // Unir cuerpo y dígito verificador con guión
            input.value = cuerpoFormateado + '-' + dv;
        } else if (valor.length === 1) {
            input.value = valor.toUpperCase();
        } else {
            input.value = valor;
        }
    }
    
    // Aplicar a todos los campos con id que contenga 'rut' o 'RUT'
    const rutInputs = document.querySelectorAll('input[id*="rut"], input[id*="RUT"], input[name*="rut"], input[name*="RUT"]');
    
    rutInputs.forEach(function(input) {
        // Aplicar formateo en tiempo real
        input.addEventListener('input', function() {
            formatearRUT(this);
        });
        
        // Aplicar formateo al perder el foco (por si acaso)
        input.addEventListener('blur', function() {
            if (this.value) {
                formatearRUT(this);
            }
        });
        
        // Prevenir entrada de caracteres no válidos
        input.addEventListener('keypress', function(e) {
            const char = String.fromCharCode(e.which);
            // Permitir números, k, K, y teclas de control
            if (!/[0-9kK]/.test(char) && !/[0-9]/.test(e.key)) {
                // Permitir teclas especiales (backspace, delete, tab, etc.)
                if (![8, 9, 13, 27, 37, 38, 39, 40, 46].includes(e.keyCode)) {
                    e.preventDefault();
                }
            }
        });
    });
});

