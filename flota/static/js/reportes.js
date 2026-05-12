document.addEventListener('DOMContentLoaded', function() {
    console.log('=== INICIO reporte_costos.js ===');
    
    // Obtener datos directamente desde la variable global asignada en el template
    let datosGraficos = window.datosGraficos;
    
    if (!datosGraficos) {
        console.error('No se encontró window.datosGraficos');
        const container = document.querySelector('#dashboard .card-body');
        if (container) {
            container.innerHTML = '<div class="alert alert-warning">No hay datos disponibles para mostrar los gráficos.</div>';
        }
        return;
    }
    
    if (!datosGraficos.patentes || !Array.isArray(datosGraficos.patentes) || datosGraficos.patentes.length === 0) {
        console.error('window.datosGraficos no tiene el formato esperado', datosGraficos);
        mostrarMensajeError();
        return;
    }
    
    console.log('Validación exitosa. Continuando con gráficos...');
    
    function mostrarMensajeError() {
        const container = document.querySelector('#dashboard .card-body');
        if (container) {
            container.innerHTML = '<div class="alert alert-warning">No hay datos disponibles para mostrar los gráficos.</div>';
        }
    }
    
    console.log('Reporte cargado - tabs gestionadas por Django');
    
    // Manejo de pestañas
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
            localStorage.setItem('reporte_scroll_pos', window.scrollY);
        });
    });
    
    const savedScroll = localStorage.getItem('reporte_scroll_pos');
    if (savedScroll) {
        window.scrollTo(0, parseInt(savedScroll));
        localStorage.removeItem('reporte_scroll_pos');
    }

    console.log('=== DIAGNÓSTICO DE DATOS ===');
    console.log('Patentes:', datosGraficos.patentes);
    console.log('Costos Mantenimiento:', datosGraficos.costos_mantenimiento);
    console.log('Costos Combustible:', datosGraficos.costos_combustible);
    console.log('Costos Arriendo:', datosGraficos.costos_arriendo);

    // Gráfico de Costos por Vehículo (Barras Apiladas)
    const ctxCostos = document.getElementById('chartCostosPorVehiculo');
    if (ctxCostos) {
        console.log('Creando gráfico de costos...');
        new Chart(ctxCostos, {
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
                                if (label) label += ': ';
                                label += '$' + context.parsed.y.toLocaleString('es-CL');
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: { 
                        stacked: true,
                        title: { display: true, text: 'Vehículos' }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        title: { display: true, text: 'Costo ($)' },
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toLocaleString('es-CL');
                            }
                        }
                    }
                },
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

    // Gráfico de Días Fuera de Servicio
    const ctxDias = document.getElementById('chartDiasFueraServicio');
    if (ctxDias && window.patentesDisp && window.patentesDisp.length) {
        new Chart(ctxDias, {
            type: 'bar',
            data: {
                labels: window.patentesDisp,
                datasets: [{
                    label: 'Días fuera de servicio',
                    data: window.diasFueraDisp,
                    backgroundColor: 'rgba(153, 102, 255, 0.8)',
                    borderColor: 'rgba(153, 102, 255, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Días Fuera de Servicio por Vehículo (período seleccionado)',
                        font: { size: 14 }
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.raw} días (${((ctx.raw / window.diasPeriodoDisp) * 100).toFixed(1)}% del período)`
                        }
                    }
                },
                scales: {
                    x: { beginAtZero: true, title: { display: true, text: 'Días' } }
                }
            }
        });
    }

    // Gráfico de Desglose (Dona)
    let chartDesglose = null;
    
    function actualizarDesgloseCostos(indexVehiculo) {
        console.log('Actualizando desglose para índice:', indexVehiculo);
        const canvas = document.getElementById('chartDesgloseCostos');
        if (!canvas) {
            console.error('No se encontró el canvas para desglose');
            return;
        }
        const ctx = canvas.getContext('2d');
        const datos = [
            datosGraficos.costos_mantenimiento[indexVehiculo] || 0,
            datosGraficos.costos_combustible[indexVehiculo] || 0,
            datosGraficos.costos_arriendo[indexVehiculo] || 0
        ];
        console.log('Datos para desglose:', datos);
        const total = datos.reduce((a, b) => a + b, 0);
        console.log('Total de costos:', total);
        if (chartDesglose) chartDesglose.destroy();
        if (total === 0) {
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
                cutout: '60%',
                plugins: {
                    title: {
                        display: true,
                        text: `Desglose: ${datosGraficos.patentes[indexVehiculo]}`,
                        font: { size: 14 }
                    },
                    legend: { position: 'bottom', labels: { padding: 20, usePointStyle: true } },
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
    const patentes = window.patentesList || [];
    const rendimientos = window.rendimientosList || [];
    const costoPorLitro = window.costoPorLitroList || [];
    const costoPreventivoKm = window.costoPreventivoKmList || [];
    const costoCorrectivoKm = window.costoCorrectivoKmList || [];

    // Gráfico 1: Barras de rendimiento (km/l)
    const chartRendimientoCanvas = document.getElementById('chartRendimiento');
    if (chartRendimientoCanvas && patentes.length) {
        new Chart(chartRendimientoCanvas, {
            type: 'bar',
            data: {
                labels: patentes,
                datasets: [{
                    label: 'km/l',
                    data: rendimientos,
                    backgroundColor: 'rgba(75, 192, 192, 0.7)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: ${context.raw.toFixed(2)} km/l`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'km/litro' }
                    }
                }
            }
        });
    }

    // Gráfico 2: Barras de costo por litro
    const chartCostoLitroCanvas = document.getElementById('chartCostoPorLitro');
    if (chartCostoLitroCanvas && patentes.length) {
        new Chart(chartCostoLitroCanvas, {
            type: 'bar',
            data: {
                labels: patentes,
                datasets: [{
                    label: '$ / litro',
                    data: costoPorLitro,
                    backgroundColor: 'rgba(255, 159, 64, 0.7)',
                    borderColor: 'rgba(255, 159, 64, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `$${context.raw.toLocaleString('es-CL')} / litro`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Precio por litro ($)' },
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toLocaleString('es-CL');
                            }
                        }
                    }
                }
            }
        });
    }

    // Gráfico 3: Barras agrupadas de costo por km (preventivo vs correctivo)
    const chartCostoKmCanvas = document.getElementById('chartCostoKmDesagregado');
    if (chartCostoKmCanvas && patentes.length) {
        new Chart(chartCostoKmCanvas, {
            type: 'bar',
            data: {
                labels: patentes,
                datasets: [
                    {
                        label: 'Preventivo $/km',
                        data: costoPreventivoKm,
                        backgroundColor: 'rgba(54, 162, 235, 0.7)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Correctivo $/km',
                        data: costoCorrectivoKm,
                        backgroundColor: 'rgba(255, 99, 132, 0.7)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                let value = context.raw;
                                return `${label}: $${value.toLocaleString('es-CL')} / km`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: '$ / km' },
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toLocaleString('es-CL');
                            }
                        }
                    }
                }
            }
        });
    }
    // Gráfico de disponibilidad global (torta)
    const ctxGlobal = document.getElementById('chartDisponibilidadGlobal');
    if (ctxGlobal && window.disponibilidadGlobal) {
        new Chart(ctxGlobal, {
            type: 'doughnut',
            data: {
                labels: ['Días disponibles', 'Días fuera de servicio'],
                datasets: [{
                    data: [window.disponibilidadGlobal.dias_disponibles, window.disponibilidadGlobal.total_dias_fuera],
                    backgroundColor: ['#28a745', '#dc3545'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${ctx.raw} días (${((ctx.raw / window.disponibilidadGlobal.total_dias_posibles) * 100).toFixed(1)}%)` } }
                }
            }
        });
    }

    // Gráfico evolución mensual (línea)
    const ctxMensual = document.getElementById('chartDiasFueraMensual');
    if (ctxMensual && window.diasFueraMensual) {
        const meses = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
        new Chart(ctxMensual, {
            type: 'line',
            data: { labels: meses, datasets: [{ label: 'Días fuera de servicio', data: window.diasFueraMensual, borderColor: '#17a2b8', backgroundColor: 'rgba(23,162,184,0.1)', fill: true, tension: 0.3 }] },
            options: { responsive: true, scales: { y: { beginAtZero: true, title: { display: true, text: 'Días' } } } }
        });
    }
});
