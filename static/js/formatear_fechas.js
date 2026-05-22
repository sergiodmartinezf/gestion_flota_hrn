// Formatear fechas en inputs type="date" al cargar formularios de edición
document.addEventListener('DOMContentLoaded', function() {
    // Buscar todos los inputs de tipo fecha
    document.querySelectorAll('input[type="date"]').forEach(function(input) {
        // Si el input tiene un valor pero no está en formato YYYY-MM-DD
        if (input.value && !/^\d{4}-\d{2}-\d{2}$/.test(input.value)) {
            // Intentar convertir desde formato DD/MM/YYYY o DD-MM-YYYY
            let fechaStr = input.value.trim();
            
            // Detectar formato DD/MM/YYYY o DD-MM-YYYY
            let partes = fechaStr.split(/[\/\-]/);
            if (partes.length === 3) {
                let dia = partes[0].padStart(2, '0');
                let mes = partes[1].padStart(2, '0');
                let anio = partes[2];
                
                // Si el año tiene 2 dígitos, asumir 20XX
                if (anio.length === 2) {
                    anio = '20' + anio;
                }
                
                // Validar que sea una fecha válida
                let fecha = new Date(anio + '-' + mes + '-' + dia);
                if (!isNaN(fecha.getTime())) {
                    // Formato correcto: YYYY-MM-DD
                    input.value = anio + '-' + mes + '-' + dia;
                }
            }
        }
        
        // También corregir valores iniciales establecidos por Django
        // Django puede renderizar fechas en formato del locale, necesitamos forzar el formato
        if (input.hasAttribute('data-initial-value')) {
            let initialValue = input.getAttribute('data-initial-value');
            if (initialValue && /^\d{4}-\d{2}-\d{2}$/.test(initialValue)) {
                input.value = initialValue;
            }
        }
    });
});
