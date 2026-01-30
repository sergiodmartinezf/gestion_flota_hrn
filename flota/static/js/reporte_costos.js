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

// 1. Obtener datos desde Django
const datosGraficos = {{ graficos_json|safe }};

console.log('=== DIAGNÓSTICO DE DATOS ===');
console.log('Patentes:', datosGraficos.patentes);
console.log('Costos Mantenimiento:', datosGraficos.costos_mantenimiento);
console.log('Costos Combustible:', datosGraficos.costos_combustible);
console.log('Costos Arriendo:', datosGraficos.costos_arriendo);

// Esperar a que el DOM esté completamente cargado
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM cargado, creando gráficos...');
    
    // 2. Gráfico de Costos por Vehículo (Barras Apiladas)
    const ctxCostos = document.getElementById('chartCostosPorVehiculo');
    if (ctxCostos) {
        console.log('Creando gráfico de costos...');
        const chartCostos = new Chart(ctxCostos, {
            type: 'bar',
            data: {
                labels: datosGraficos.patentes,
                datasets: [
                    {
                        label: 'Mantenimiento',
                        data: datosGraficos.costos_mantenimiento,
                        backgroundColor: 'rgba(255, 99, 132, 0.8)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Combustible',
                        data: datosGraficos.costos_combustible,
                        backgroundColor: 'rgba(54, 162, 235, 0.8)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Arriendo',
                        data: datosGraficos.costos_arriendo,
                        backgroundColor: 'rgba(255, 206, 86, 0.8)',
                        borderColor: 'rgba(255, 206, 86, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    title: { 
                        display: true, 
                        text: 'Costos Totales por Vehículo',
                        font: { size: 16 }
                    },
                    tooltip: { 
                        mode: 'index', 
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += '$' + context.parsed.y.toLocaleString('es-CL');
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: { 
                        stacked: true,
                        title: {
                            display: true,
                            text: 'Vehículos'
                        }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        title: { 
                            display: true, 
                            text: 'Costo ($)'
                        },
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toLocaleString('es-CL');
                            }
                        }
                    }
                },
                // Interactividad: Al hacer clic en una barra
                onClick: (evt, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        console.log('Clic en vehículo:', datosGraficos.patentes[index]);
                        actualizarDesgloseCostos(index);
                    }
                }
            }
        });
    } else {
        console.error('No se encontró el canvas para gráfico de costos');
    }

    // 3. Gráfico de Días Fuera de Servicio
    const ctxDias = document.getElementById('chartDiasFueraServicio');
    if (ctxDias) {
        console.log('Creando gráfico de días fuera de servicio...');
        const chartDias = new Chart(ctxDias, {
            type: 'bar',
            data: {
                labels: datosGraficos.patentes,
                datasets: [{
                    label: 'Días fuera de servicio',
                    data: datosGraficos.dias_fuera_servicio,
                    backgroundColor: 'rgba(153, 102, 255, 0.8)',
                    borderColor: 'rgba(153, 102, 255, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'y', // Barras horizontales
                responsive: true,
                plugins: {
                    title: { 
                        display: true, 
                        text: 'Días Fuera de Servicio por Vehículo',
                        font: { size: 16 }
                    }
                },
                scales: {
                    x: { 
                        beginAtZero: true, 
                        title: { 
                            display: true, 
                            text: 'Días' 
                        }
                    }
                }
            }
        });
    }

    // 4. Gráfico de Desglose (Dona)
    let chartDesglose = null;
    
    function actualizarDesgloseCostos(indexVehiculo) {
        console.log('Actualizando desglose para índice:', indexVehiculo);
        
        const canvas = document.getElementById('chartDesgloseCostos');
        if (!canvas) {
            console.error('No se encontró el canvas para desglose');
            return;
        }
        
        const ctx = canvas.getContext('2d');
        
        // Datos para este vehículo específico
        const datos = [
            datosGraficos.costos_mantenimiento[indexVehiculo] || 0,
            datosGraficos.costos_combustible[indexVehiculo] || 0,
            datosGraficos.costos_arriendo[indexVehiculo] || 0
        ];
        
        console.log('Datos para desglose:', datos);
        
        // Verificar si hay datos
        const total = datos.reduce((a, b) => a + b, 0);
        console.log('Total de costos:', total);
        
        // Destruir gráfico anterior si existe
        if (chartDesglose) {
            chartDesglose.destroy();
        }
        
        if (total === 0) {
            // Mostrar mensaje de "sin datos"
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#f5f5f5';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            ctx.fillStyle = '#999';
            ctx.font = '14px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText('No hay datos de costos', canvas.width / 2, canvas.height / 2 - 10);
            ctx.fillText('para este vehículo', canvas.width / 2, canvas.height / 2 + 10);
            return;
        }
        
        // Crear el gráfico de desglose
        chartDesglose = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Mantenimiento', 'Combustible', 'Arriendo'],
                datasets: [{
                    data: datos,
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(54, 162, 235, 0.8)', 
                        'rgba(255, 206, 86, 0.8)'
                    ],
                    borderColor: [
                        'rgba(255, 99, 132, 1)',
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 206, 86, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                cutout: '60%', // Hace el "agujero" más grande
                plugins: {
                    title: {
                        display: true,
                        text: `Desglose: ${datosGraficos.patentes[indexVehiculo]}`,
                        font: { size: 14 }
                    },
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${context.label}: $${value.toLocaleString('es-CL')} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
        
        console.log('Gráfico de desglose creado');
    }
    
    // Inicializar con el primer vehículo que tenga datos
    let indiceInicial = 0;
    for (let i = 0; i < datosGraficos.patentes.length; i++) {
        const total = (datosGraficos.costos_mantenimiento[i] || 0) + 
                        (datosGraficos.costos_combustible[i] || 0) + 
                        (datosGraficos.costos_arriendo[i] || 0);
        if (total > 0) {
            indiceInicial = i;
            break;
        }
    }
    
    console.log('Inicializando desglose con índice:', indiceInicial);
    actualizarDesgloseCostos(indiceInicial);
});
