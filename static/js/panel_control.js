function getJSON(elementId, defaultValue = null) {
    const el = document.getElementById(elementId);
    if (!el) {
        console.warn(`Elemento ${elementId} no encontrado`);
        return defaultValue;
    }
    try {
        return JSON.parse(el.textContent);
    } catch (e) {
        console.error(`Error parseando JSON en ${elementId}:`, e);
        return defaultValue;
    }
}

// Variables para los gráficos del modal Tiempo
let ambulanciasChart = null;
let camionetaChart = null;
let promediosChart = null;

function destroyTimeCharts() {
    // Destruir gráficos principales
    if (ambulanciasChart) ambulanciasChart.destroy();
    if (camionetaChart) camionetaChart.destroy();
    if (promediosChart) promediosChart.destroy();

    // Destruir gráficos individuales por patente
    const canvases = document.querySelectorAll('[id^="chartPatente"]');
    canvases.forEach(canvas => {
        if (canvas.chart) {
            canvas.chart.destroy();
            canvas.chart = null;
        }
    });
}

function initTimeCharts() {
    const disponibilidadData = getJSON('data-disponibilidad', {
        por_vehiculo: [],
        ambulancias: { operativos: 0, preventivo: 0, correctivo: 0 },
        camioneta: null,
        promedios: { operativo: 0, preventivo: 0, correctivo: 0 }
    });

    const diasPorVehiculo = disponibilidadData.por_vehiculo || [];

    // --- Gráfico de Ambulancias ---
    const ctxDispAmb = document.getElementById('chartDisponibilidadAmbulancias');
    if (ctxDispAmb) {
        const ambData = disponibilidadData.ambulancias;
        ambulanciasChart = new Chart(ctxDispAmb, {
            type: 'doughnut',
            data: {
                labels: ['Operativo', 'Preventivo', 'Correctivo'],
                datasets: [{
                    data: [ambData.operativos, ambData.preventivo, ambData.correctivo],
                    backgroundColor: ['#198754', '#0d6efd', '#dc3545'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = context.raw;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ${value} días / ${percentage}%`;
                            }
                        }
                    }
                }
            }
        });
    }

    // --- Gráfico de Camioneta (si existe) ---
    const ctxDispCam = document.getElementById('chartDisponibilidadCamioneta');
    if (ctxDispCam) {
        const camData = disponibilidadData.camioneta;
        if (camData && camData.operativo !== undefined) {
            camionetaChart = new Chart(ctxDispCam, {
                type: 'doughnut',
                data: {
                    labels: ['Operativo', 'Preventivo', 'Correctivo'],
                    datasets: [{
                        data: [camData.operativo, camData.preventivo, camData.correctivo],
                        backgroundColor: ['#198754', '#0d6efd', '#dc3545'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { position: 'bottom' },
                        tooltip: {
                            callbacks: {
                                label: (context) => {
                                    const label = context.label || '';
                                    const value = context.raw;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${label}: ${value} días / ${percentage}%`;
                                }
                            }
                        }
                    }
                }
            });
        } else {
            ctxDispCam.parentNode.innerHTML = '<p class="text-muted">Sin datos de camioneta</p>';
        }
    }

    // --- Textos numéricos debajo de los gráficos generales ---
    const ambText = document.getElementById('ambulancias-text');
    if (ambText && ambulanciasChart) {
        const data = ambulanciasChart.data.datasets[0].data;
        const totalDiasAmb = data[0] + data[1] + data[2];
        ambText.innerHTML = `
            Operativo: ${data[0]} días (${((data[0]/totalDiasAmb)*100).toFixed(1)}%) |
            Preventivo: ${data[1]} días (${((data[1]/totalDiasAmb)*100).toFixed(1)}%) |
            Correctivo: ${data[2]} días (${((data[2]/totalDiasAmb)*100).toFixed(1)}%)
        `;
    }

    const camText = document.getElementById('camioneta-text');
    if (camText && camionetaChart) {
        const data = camionetaChart.data.datasets[0].data;
        const totalDiasCam = data[0] + data[1] + data[2];
        camText.innerHTML = `
            Operativo: ${data[0]} días (${((data[0]/totalDiasCam)*100).toFixed(1)}%) |
            Preventivo: ${data[1]} días (${((data[1]/totalDiasCam)*100).toFixed(1)}%) |
            Correctivo: ${data[2]} días (${((data[2]/totalDiasCam)*100).toFixed(1)}%)
        `;
    }

    // --- Gráficos individuales por patente (solo ambulancias) ---
    if (diasPorVehiculo.length) {
        diasPorVehiculo.forEach((item, index) => {
            const canvasId = `chartPatente${index + 1}`;
            const ctx = document.getElementById(canvasId);
            if (ctx) {
                // Asegurar dimensiones
                ctx.style.width = '100px';
                ctx.style.height = '100px';

                // Destruir gráfico previo si existe
                if (ctx.chart) {
                    ctx.chart.destroy();
                }

                try {
                    ctx.chart = new Chart(ctx, {
                        type: 'doughnut',
                        data: {
                            labels: ['Operativo', 'Preventivo', 'Correctivo'],
                            datasets: [{
                                data: [
                                    parseInt(item.operativo) || 0,
                                    parseInt(item.preventivo) || 0,
                                    parseInt(item.correctivo) || 0
                                ],
                                backgroundColor: ['#198754', '#0d6efd', '#dc3545'],
                                borderWidth: 0
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: true,
                            plugins: {
                                legend: { display: false },
                                tooltip: {
                                    callbacks: {
                                        label: (context) => {
                                            try {
                                                const label = context.label || '';
                                                const value = context.raw;
                                                const total = typeof DIAS_DEL_PERIODO !== 'undefined' ? DIAS_DEL_PERIODO : context.dataset.data.reduce((a, b) => a + b, 0);
                                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : '0.0';
                                                // Una sola línea con el formato deseado
                                                return `${label}: ${value} días / ${percentage}%`;
                                            } catch (e) {
                                                console.error('Error en tooltip:', e);
                                                return `${context.label}: ${context.raw}`;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    });
                } catch (chartError) {
                    console.error(`Error al crear gráfico para ${item.patente}:`, chartError);
                }
            }
        });
    }

    // --- Gráfico de promedios ---
    const ctxProm = document.getElementById('chartPromedios');
    if (ctxProm) {
        const promedios = disponibilidadData.promedios;
        promediosChart = new Chart(ctxProm, {
            type: 'bar',
            data: {
                labels: ['Promedio por vehículo'],
                datasets: [
                    {
                        label: 'Operativo',
                        data: [promedios.operativo],
                        backgroundColor: '#198754'
                    },
                    {
                        label: 'Preventivo',
                        data: [promedios.preventivo],
                        backgroundColor: '#0d6efd'
                    },
                    {
                        label: 'Correctivo',
                        data: [promedios.correctivo],
                        backgroundColor: '#dc3545'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const label = context.dataset.label || '';
                                const value = context.raw;
                                return `${label}: ${value} días`;
                            }
                        }
                    }
                },
                scales: { y: { beginAtZero: true } }
            }
        });
    }
}

// Evento para el modal de tiempo
const modalTiempo = document.getElementById('modalTiempo');
if (modalTiempo) {
    modalTiempo.addEventListener('shown.bs.modal', function() {
        destroyTimeCharts();
        initTimeCharts();
    });
}

// ------------------------------------------------------------------
// Inicio de la aplicación: cuando el DOM está listo
// ------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', function() {
    // Registrar plugin de anotaciones si está disponible
    if (typeof Annotation !== 'undefined') {
        Chart.register(Annotation);
    }

    // ------------------------------------------------------------------
    // Variables para almacenar instancias de gráficos financieros
    // ------------------------------------------------------------------
    let financeMainChart = null;
    let detailChart = null;
    let comparativaChart = null;
    let vehicleChart = null;

    // ------------------------------------------------------------------
    // Función para actualizar el detalle mensual (llamada desde el gráfico)
    // ------------------------------------------------------------------
    function updateFinanceDetail(mes, data) {
        const ctxDetail = document.getElementById('chartFinanceDetail');
        const detailTitle = document.getElementById('financeDetailTitle');
        const detailContent = document.getElementById('financeDetailContent');

        if (!ctxDetail || !detailTitle || !detailContent) return;

        detailTitle.innerText = `2. Gasto en ${mes}`;
        detailContent.classList.add('d-none');
        ctxDetail.classList.remove('d-none');

        const labels = data.map(d => d.patente);
        const prevData = data.map(d => d.preventivo || 0);
        const corrData = data.map(d => d.correctivo || 0);

        // Destruir gráfico anterior si existe
        if (detailChart) detailChart.destroy();

        if (labels.length) {
            detailChart = new Chart(ctxDetail, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Preventivo ($)',
                            data: prevData,
                            backgroundColor: '#0d6efd',
                            borderRadius: 5
                        },
                        {
                            label: 'Correctivo ($)',
                            data: corrData,
                            backgroundColor: '#dc3545',
                            borderRadius: 5
                        }
                    ]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: (context) => {
                                    return context.dataset.label + ': $' + context.raw.toLocaleString('es-CL');
                                }
                            }
                        }
                    },
                    scales: {
                        x: { stacked: false, beginAtZero: true },
                        y: { stacked: false }
                    }
                }
            });
        } else {
            // Sin datos, mostrar mensaje
            ctxDetail.getContext('2d').clearRect(0, 0, ctxDetail.width, ctxDetail.height);
            ctxDetail.classList.add('d-none');
            detailContent.classList.remove('d-none');
            detailContent.innerHTML = '<p>Sin datos para este mes</p>';
        }
    }

    // ------------------------------------------------------------------
    // Función para inicializar los gráficos financieros (modal)
    // ------------------------------------------------------------------
    function initFinanceCharts() {
        const financeData = getJSON('data-finance', { labels: [], monthly_totals: [], drilldown: [] });
        const comparativaData = getJSON('data-comparativa', null);
        const vehicleData = getJSON('data-vehicle', []);

        const ctxMain = document.getElementById('chartFinanceMain');
        const ctxBarras = document.getElementById('chartPlataBarras');
        const ctxVehicle = document.getElementById('chartVehicleSplit');

        // Destruir gráficos anteriores
        if (financeMainChart) financeMainChart.destroy();
        if (comparativaChart) comparativaChart.destroy();
        if (vehicleChart) vehicleChart.destroy();

        // 1. Gráfico principal de gasto mensual (línea)
        if (ctxMain && financeData && financeData.labels && financeData.labels.length) {
            financeMainChart = new Chart(ctxMain, {
                type: 'line',
                data: {
                    labels: financeData.labels,
                    datasets: [{
                        label: 'Gasto Total ($)',
                        data: (financeData.monthly_totals || []).map(v => v || 0),
                        borderColor: '#0d6efd',
                        backgroundColor: 'rgba(13, 110, 253, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 6,
                        pointHoverRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: (c) => '$' + new Intl.NumberFormat('es-CL').format(c.raw || 0)
                            }
                        }
                    },
                    onClick: (e, activeElements) => {
                        if (activeElements.length > 0) {
                            const index = activeElements[0].index;
                            const mesNombre = financeData.labels[index];
                            const breakdown = (financeData.drilldown && financeData.drilldown[index]) || [];
                            updateFinanceDetail(mesNombre, breakdown);
                        }
                    }
                }
            });
        } else if (ctxMain) {
            ctxMain.getContext('2d').clearRect(0, 0, ctxMain.width, ctxMain.height);
            console.warn('No se pudo crear el gráfico de gasto mensual: datos incompletos', financeData);
        }

        // 2. Comparativa global (Preventivo vs Correctivo)
        if (ctxBarras && comparativaData && comparativaData.labels && comparativaData.programado && comparativaData.ejecutado) {
            comparativaChart = new Chart(ctxBarras, {
                type: 'bar',
                data: {
                    labels: comparativaData.labels,
                    datasets: [
                        {
                            label: 'Programado ($)',
                            data: comparativaData.programado.map(v => v || 0),
                            backgroundColor: 'rgba(201, 203, 207, 0.8)',
                            borderRadius: 5
                        },
                        {
                            label: 'Ejecutado ($)',
                            data: comparativaData.ejecutado.map(v => v || 0),
                            backgroundColor: '#0d6efd',
                            borderRadius: 5
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { position: 'top' },
                        tooltip: {
                            callbacks: {
                                label: (context) => context.dataset.label + ': $' + (context.raw || 0).toLocaleString('es-CL')
                            }
                        }
                    }
                }
            });
        } else if (ctxBarras) {
            ctxBarras.getContext('2d').clearRect(0, 0, ctxBarras.width, ctxBarras.height);
            console.warn('No se pudo crear el gráfico de comparativa: datos incompletos', comparativaData);
        }

        // 3. Gasto acumulado por vehículo (desglosado)
        if (ctxVehicle && vehicleData && Array.isArray(vehicleData) && vehicleData.length > 0) {
            vehicleChart = new Chart(ctxVehicle, {
                type: 'bar',
                data: {
                    labels: vehicleData.map(d => d.patente || 'Sin patente'),
                    datasets: [
                        {
                            label: 'Preventivo',
                            data: vehicleData.map(d => (d.preventivo || 0)),
                            backgroundColor: '#0d6efd',
                            borderRadius: 5
                        },
                        {
                            label: 'Correctivo',
                            data: vehicleData.map(d => (d.correctivo || 0)),
                            backgroundColor: '#dc3545',
                            borderRadius: 5
                        }
                    ]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: (context) => {
                                    return context.dataset.label + ': $' + (context.raw || 0).toLocaleString('es-CL');
                                }
                            }
                        }
                    },
                    scales: {
                        x: { stacked: true, beginAtZero: true },
                        y: { stacked: true }
                    }
                }
            });
        } else if (ctxVehicle) {
            ctxVehicle.getContext('2d').clearRect(0, 0, ctxVehicle.width, ctxVehicle.height);
            console.warn('No se pudo crear el gráfico de gasto por vehículo: datos incompletos', vehicleData);
        }
    }

    // ------------------------------------------------------------------
    // Inicializar gráficos de finanzas cuando se abre el modal
    // ------------------------------------------------------------------
    const modalFinanzas = document.getElementById('modalFinanzas');
    if (modalFinanzas) {
        modalFinanzas.addEventListener('shown.bs.modal', function() {
            try {
                initFinanceCharts();
            } catch (error) {
                console.error('Error al inicializar gráficos de finanzas:', error);
            }
        });
    }

    // ------------------------------------------------------------------
    // Gráfico de KILÓMETROS (siempre visible, se crea una sola vez)
    // ------------------------------------------------------------------
    const kmData = getJSON('data-km', []);
    const ctxKm = document.getElementById('chartKmBarras');
    if (ctxKm && kmData && kmData.length) {
        new Chart(ctxKm, {
            type: 'bar',
            data: {
                labels: kmData.map(d => d.patente),
                datasets: [{
                    label: 'Kilómetros desde última mantención',
                    data: kmData.map(d => d.valor_grafico),
                    backgroundColor: kmData.map(d => d.color),
                    borderRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    annotation: {
                        annotations: {
                            line8000: {
                                type: 'line',
                                yMin: 8000,
                                yMax: 8000,
                                borderColor: 'orange',
                                borderWidth: 2,
                                borderDash: [6, 6]/*,
                                label: {
                                    content: '8.000 km (umbral preventivo)',
                                    enabled: true,
                                    position: 'end',
                                    xAdjust: 60
                                }*/
                            },
                            line10000: {
                                type: 'line',
                                yMin: 10000,
                                yMax: 10000,
                                borderColor: 'red',
                                borderWidth: 2,
                                borderDash: [6, 6]/*,
                                label: {
                                    content: '10.000 km (límite mantención)',
                                    enabled: true,
                                    position: 'end',
                                    xAdjust: 60
                                }*/
                            },
                            line12000: {
                                type: 'line',
                                yMin: 12000,
                                yMax: 12000,
                                borderColor: 'darkred',
                                borderWidth: 2,
                                borderDash: [6, 6]/*,
                                label: {
                                    content: '12.000 km (bloqueo)',
                                    enabled: true,
                                    position: 'end',
                                    xAdjust: 60
                                }*/
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const item = kmData[context.dataIndex];
                                let msg = `Recorrido: ${item.recorrido} km (último mant: ${item.km_ultimo} km)`;
                                if (item.recorrido >= 12000) {
                                    msg += ' - BLOQUEADO';
                                } else if (item.recorrido >= 8000) {
                                    msg += ' - Próximo a mantenimiento';
                                }
                                return msg;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        suggestedMax: 13000,  // Para asegurar visibilidad de las líneas
                        title: { display: true, text: 'Kilómetros' }
                    }
                }
            }
        });
    } else if (ctxKm) {
        ctxKm.getContext('2d').clearRect(0, 0, ctxKm.width, ctxKm.height);
        console.warn('No hay datos para el gráfico de kilómetros');
    }

});
