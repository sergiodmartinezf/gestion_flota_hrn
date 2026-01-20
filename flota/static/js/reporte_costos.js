document.addEventListener('DOMContentLoaded', function() {
    console.log('Reporte cargado - tabs gestionadas por Django');
    
    document.querySelectorAll('.nav-tabs .nav-link').forEach(link => {
        link.addEventListener('click', function() {
            document.querySelectorAll('.nav-tabs .nav-link').forEach(l => {
                l.classList.remove('active');
            });
            this.classList.add('active');
        });
    });

    const tabs = document.querySelectorAll('[data-bs-toggle="tab"]');
    tabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function() {
            // Guardar posición de scroll en localStorage
            localStorage.setItem('reporte_scroll_pos', window.scrollY);
        });
    });
    
    const savedScroll = localStorage.getItem('reporte_scroll_pos');
    if (savedScroll) {
        window.scrollTo(0, parseInt(savedScroll));
        localStorage.removeItem('reporte_scroll_pos');
    }
});
