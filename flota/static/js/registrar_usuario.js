document.addEventListener('DOMContentLoaded', function() {
    const rutInput = document.getElementById('{{ form.rut.id_for_label }}');
    
    rutInput.addEventListener('input', function(e) {
        let value = e.target.value.replace(/[^0-9kK]/g, '');
        
        if (value.length > 1) {
            value = value.slice(0, -1) + '-' + value.slice(-1);
        }
        
        if (value.length > 2) {
            value = value.slice(0, -2) + '.' + value.slice(-2);
        }
        
        e.target.value = value;
    });
});

