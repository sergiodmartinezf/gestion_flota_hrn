function marcarComoRevisadas() {
    if (confirm('¿Está seguro de marcar todas las alertas como revisadas?')) {
        // Crear un formulario temporal para enviar POST
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '{% url "alertas_mantenimiento" %}';

        // Agregar token CSRF
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfToken) {
            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrfmiddlewaretoken';
            csrfInput.value = csrfToken.value;
            form.appendChild(csrfInput);
        }

        // Agregar action
        const actionInput = document.createElement('input');
        actionInput.type = 'hidden';
        actionInput.name = 'action';
        actionInput.value = 'marcar_revisadas';
        form.appendChild(actionInput);

        document.body.appendChild(form);
        form.submit();
    }
}