Chart.register(ChartDataLabels);

document.addEventListener('DOMContentLoaded', function() {
    console.log('=== Inicialización de gráficos de reportes ===');

    // --- Funciones auxiliares de formato ---
    const formatCurrency = (value) => {
        if (value === null || value === undefined) return '$0';
        return '$' + Math.round(value).toLocaleString('es-CL');
    };

    const formatKmPerLiter = (value) => {
        if (value === null || value === undefined) return '—';
        return value.toFixed(1) + ' km/l';
    };

    const formatDecimal2 = (value) => {
        if (value === null || value === undefined) return '—';
        return value.toFixed(2);
    };

    const formatDecimal1 = (value) => {
        if (value === null || value === undefined) return '—';
        return value.toFixed(1);
    };

    const formatInteger = (value) => {
        if (value === null || value === undefined) return '—';
        return Math.round(value).toString();
    };

    // --- Datos desde el template (variables globales) ---
    const datosGraficos = window.datosGraficos;
    const patentesList = window.patentesList || [];
    const rendimientosList = window.rendimientosList || [];
    const costoPreventivoKmList = window.costoPreventivoKmList || [];
    const costoCorrectivoKmList = window.costoCorrectivoKmList || [];

    // --- Validación de datos para gráficos de costos ---
    if (!datosGraficos || !datosGraficos.patentes || datosGraficos.patentes.length === 0) {
        console.warn('No hay datos para gráficos de costos');
    } else {
        console.log('Datos de costos cargados:', datosGraficos.patentes.length, 'vehículos');
        // 1. Gráfico de Costos por Vehículo (barras apiladas)
        const ctxCostos = document.getElementById('chartCostosPorVehiculo');
        if (ctxCostos) {
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
                            borderWidth: 1 }
                    ]
                },
                options: {
                    responsive: true,
                    scales: { 
                        x: { 
                            stacked: true 
                        }, 
                        y: { 
                            stacked: true, 
                            beginAtZero: true, 
                            title: { 
                                display: true, 
                                text: 'Costo ($)' 
                            }, 
                            ticks: { 
                                callback: (v) => formatCurrency(v) 
                            } 
                        } 
                    },
                    plugins: {
                        legend: { position: 'bottom' },
                        tooltip: { 
                            callbacks: { 
                                label: (ctx) => `${ctx.dataset.label}: ${formatCurrency(ctx.parsed.y)}` 
                            } 
                        },
                        datalabels: {
                            formatter: (value) => formatCurrency(value),
                            anchor: 'end',
                            align: 'top'
                        }
                    },
                    onClick: (evt, elements) => { if (elements.length) actualizarDesgloseCostos(elements[0].index); }
                }
            });
        }

        // 2. Gráfico de desglose (dona) – se actualiza al hacer clic en una barra
        let chartDesglose = null;
        function actualizarDesgloseCostos(indexVehiculo) {
            const canvas = document.getElementById('chartDesgloseCostos');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            const datos = [
                datosGraficos.costos_mantenimiento[indexVehiculo] || 0,
                datosGraficos.costos_combustible[indexVehiculo] || 0,
                datosGraficos.costos_arriendo[indexVehiculo] || 0
            ];
            const total = datos.reduce((a, b) => a + b, 0);
            if (chartDesglose) chartDesglose.destroy();
            if (total === 0) {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.fillStyle = '#f5f5f5'; ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.fillStyle = '#999'; ctx.font = '14px Arial'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
                ctx.fillText('No hay datos de costos', canvas.width/2, canvas.height/2 - 10);
                ctx.fillText('para este vehículo', canvas.width/2, canvas.height/2 + 10);
                return;
            }
            chartDesglose = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: [
                        'Mantenimiento', 
                        'Combustible', 
                        'Arriendo'
                    ],
                    datasets: [
                        { 
                            data: datos, 
                            backgroundColor: [
                                'rgba(255,99,132,0.8)', 
                                'rgba(54,162,235,0.8)', 
                                'rgba(255,206,86,0.8)'
                            ] 
                        }
                    ]
                },
                options: {
                    responsive: true, 
                    cutout: '60%',
                    plugins: {
                        legend: { position: 'bottom' },
                        title: { 
                            display: true, 
                            text: `Desglose: ${datosGraficos.patentes[indexVehiculo]}`, 
                            font: { 
                                size: 14 
                            } 
                        },
                        tooltip: { 
                            callbacks: { 
                                label: (ctx) => `${ctx.label}: ${formatCurrency(ctx.raw)} (${Math.round((ctx.raw/total)*100)}%)` 
                            } 
                        },
                        datalabels: {
                            formatter: (value) => formatCurrency(value),
                            anchor: 'end',
                            align: 'start'
                        }
                    }
                }
            });
        }
        // Inicializar con el primer vehículo que tenga costo > 0
        let indiceInicial = datosGraficos.patentes.findIndex((_, i) => 
            (datosGraficos.costos_mantenimiento[i]||0)+(datosGraficos.costos_combustible[i]||0)+(datosGraficos.costos_arriendo[i]||0) > 0);
        if (indiceInicial === -1) indiceInicial = 0;
        actualizarDesgloseCostos(indiceInicial);

        // 3. Gráfico de Rendimiento (km/l)
        if (patentesList.length && rendimientosList.length) {
            const canvasRend = document.getElementById('chartRendimiento');
            if (canvasRend) {
                new Chart(canvasRend, {
                    type: 'bar',
                    data: { 
                        labels: patentesList, 
                        datasets: [
                            { 
                                label: 'km/l', 
                                data: rendimientosList, 
                                backgroundColor: 'rgba(75,192,192,0.7)', 
                                borderColor: 'rgba(75,192,192,1)', 
                                borderWidth: 1 
                            }
                        ] 
                    },
                    options: { 
                        responsive: true, 
                        scales: { 
                            y: { 
                                beginAtZero: true, 
                                title: { 
                                    display: true, 
                                    text: 'km/litro' 
                                },
                                ticks: {
                                    callback: (v) => v.toFixed(1)
                                }
                            } 
                        }, 
                        plugins: {
                            legend: { position: 'bottom' },
                            tooltip: {
                                callbacks: {
                                    label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)}`
                                }
                            },
                            datalabels: { 
                                anchor: 'end', 
                                align: 'top',
                                formatter: (value) => value.toFixed(1)
                            } 
                        } 
                    }
                });
            }
        }

        // 4. Gráfico de Costo por km (Preventivo vs Correctivo vs Total mantenimiento)
        if (patentesList.length && costoPreventivoKmList.length && costoCorrectivoKmList.length && window.costoMantenimientoTotalKmList) {
            const canvasKm = document.getElementById('chartCostoKmDesagregado');
            if (canvasKm) {
                new Chart(canvasKm, {
                    type: 'bar',
                    data: {
                        labels: patentesList,
                        datasets: [
                            { 
                                label: 'Preventivo $/km', 
                                data: costoPreventivoKmList, 
                                backgroundColor: 'rgba(54,162,235,0.7)', 
                                borderColor: 'rgba(54,162,235,1)', 
                                borderWidth: 1 
                            },
                            { 
                                label: 'Correctivo $/km', 
                                data: costoCorrectivoKmList, 
                                backgroundColor: 'rgba(255,99,132,0.7)', 
                                borderColor: 'rgba(255,99,132,1)', 
                                borderWidth: 1 
                            },
                            { 
                                label: 'Total mantenimiento $/km', 
                                data: window.costoMantenimientoTotalKmList, 
                                backgroundColor: 'rgba(255,159,64,0.7)', 
                                borderColor: 'rgba(255,159,64,1)', 
                                borderWidth: 1 
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: { 
                                    display: true, 
                                    text: '$ / km' 
                                },
                                ticks: { 
                                    callback: (v) => formatCurrency(v)
                                }
                            }
                        },
                        plugins: {
                            legend: { position: 'bottom' },
                            tooltip: {
                                callbacks: {
                                    label: (ctx) => `${ctx.dataset.label}: ${formatCurrency(ctx.parsed.y)}`
                                }
                            },
                            datalabels: { 
                                anchor: 'end', 
                                align: 'top',
                                formatter: (value) => formatCurrency(value)
                            } 
                        }
                    }
                });
            }
        }
    }

    // --- Gráficos de Disponibilidad ---
    if (window.disponibilidadGlobal && window.patentesDisp && window.diasFueraDisp) {
        // Disponibilidad global (torta)
        const ctxGlobal = document.getElementById('chartDisponibilidadGlobal');
        if (ctxGlobal) {
            new Chart(ctxGlobal, {
                type: 'doughnut',
                data: {
                    labels: [
                        'Días disponibles', 
                        'Días fuera de servicio'
                    ],
                    datasets: [
                        { 
                            data: [
                                window.disponibilidadGlobal.dias_disponibles, 
                                window.disponibilidadGlobal.total_dias_fuera
                            ], 
                            backgroundColor: [
                                '#28a745', 
                                '#dc3545'
                            ], 
                            borderWidth: 0 
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
                                label: (ctx) => `${ctx.label}: ${formatInteger(ctx.raw)} días (${((ctx.raw / window.disponibilidadGlobal.total_dias_posibles) * 100).toFixed(1)}%)` 
                            } 
                        },
                        datalabels: { 
                            anchor: 'end', 
                            align: 'top',
                            formatter: (value) => formatInteger(value)
                        } 
                    }
                }
            });
        }

        // Días fuera de servicio por vehículo (barras horizontales)
        const ctxDias = document.getElementById('chartDiasFueraServicio');
        if (ctxDias && window.patentesDisp.length) {
            new Chart(ctxDias, {
                type: 'bar',
                data: { 
                    labels: window.patentesDisp, 
                    datasets: [
                        { 
                            label: 'Días fuera de servicio', 
                            data: window.diasFueraDisp, 
                            backgroundColor: 'rgba(153,102,255,0.8)', 
                            borderColor: 'rgba(153,102,255,1)', 
                            borderWidth: 1 
                        }
                    ] 
                },
                options: {
                    indexAxis: 'y', 
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom' }, 
                        tooltip: { 
                            callbacks: { 
                                label: (ctx) => `${formatInteger(ctx.raw)} días (${((ctx.raw / window.diasPeriodoDisp) * 100).toFixed(1)}% del período)` 
                            } 
                        },
                        datalabels: { 
                            anchor: 'end', 
                            align: 'top',
                            formatter: (value) => formatInteger(value)
                        } 
                    },
                    scales: { 
                        x: { 
                            beginAtZero: true, 
                            title: { 
                                display: true, 
                                text: 'Días' 
                            },
                            ticks: {
                                callback: (v) => formatInteger(v)
                            }
                        } 
                    }
                }
            });
        }

        // Evolución mensual de días fuera de servicio
        if (window.diasFueraMensual) {
            const ctxMensual = document.getElementById('chartDiasFueraMensual');
            if (ctxMensual) {
                const meses = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
                new Chart(ctxMensual, {
                    type: 'line',
                    data: { 
                        labels: meses, 
                        datasets: [
                            { 
                                label: 'Días fuera de servicio', 
                                data: window.diasFueraMensual, 
                                borderColor: '#17a2b8', 
                                backgroundColor: 'rgba(23,162,184,0.1)', 
                                fill: true, 
                                tension: 0.3 
                            }
                        ] 
                    },
                    options: { 
                        responsive: true, 
                        scales: { 
                            y: { 
                                beginAtZero: true, 
                                title: { 
                                    display: true, 
                                    text: 'Días' 
                                },
                                ticks: {
                                    callback: (v) => formatInteger(v)
                                }
                            } 
                        },
                        plugins: {
                            legend: { position: 'bottom' },
                            tooltip: {
                                callbacks: {
                                    label: (ctx) => `${ctx.dataset.label}: ${formatInteger(ctx.raw)}`
                                }
                            },
                            datalabels: { 
                                anchor: 'end', 
                                align: 'top',
                                formatter: (value) => formatInteger(value)
                            } 
                        }
                    }
                });
            }
        }
    }

    // --- Mantener scroll al cambiar de pestaña (opcional) ---
    const tabs = document.querySelectorAll('[data-bs-toggle="tab"]');
    tabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', () => {
            localStorage.setItem('reporte_scroll_pos', window.scrollY);
        });
    });
    const savedScroll = localStorage.getItem('reporte_scroll_pos');
    if (savedScroll) {
        window.scrollTo(0, parseInt(savedScroll));
        localStorage.removeItem('reporte_scroll_pos');
    }

    // Gráfico: Costo combustible por km
    const ctxCombKm = document.getElementById('chartCostoCombustibleKm');
    if (ctxCombKm && window.patentesList && window.costoCombustibleKmList) {
        new Chart(ctxCombKm, {
            type: 'bar',
            data: {
                labels: window.patentesList,
                datasets: [
                    {
                        label: 'Costo combustible ($/km)',
                        data: window.costoCombustibleKmList.map(v => v !== null ? v : 0),
                        backgroundColor: 'rgba(54, 162, 235, 0.7)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { 
                            display: true, 
                            text: '$ / km' 
                        },
                        ticks: { 
                            callback: (v) => formatCurrency(v)
                        }
                    }
                },
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: { 
                        callbacks: { 
                            label: (ctx) => `${ctx.dataset.label}: ${formatCurrency(ctx.raw)}` 
                        } 
                    },
                    datalabels: { 
                        anchor: 'end', 
                        align: 'top',
                        formatter: (value) => formatCurrency(value)
                    } 
                }
            }
        });
    }

    // Gráfico: Costo total por km (sin arriendos)
    const ctxTotalKm = document.getElementById('chartCostoTotalKm');
    if (ctxTotalKm && window.patentesList && window.costoTotalKmList) {
        new Chart(ctxTotalKm, {
            type: 'bar',
            data: {
                labels: window.patentesList,
                datasets: [
                    {
                        label: 'Costo total $/km',
                        data: window.costoTotalKmList.map(v => v !== null ? v : 0),
                        backgroundColor: 'rgba(75, 192, 192, 0.7)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { 
                            display: true, 
                            text: '$ / km' 
                        },
                        ticks: { 
                            callback: (v) => formatCurrency(v)
                        }
                    }
                },
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: { 
                        callbacks: { 
                            label: (ctx) => `${ctx.dataset.label}: ${formatCurrency(ctx.raw)}` 
                        } 
                    },
                    datalabels: { 
                        anchor: 'end', 
                        align: 'top',
                        formatter: (value) => formatCurrency(value)
                    } 
                }
            }
        });
    }

    // Gráfico: Costo total con arriendos por km
    const ctxTotalArriendoKm = document.getElementById('chartCostoTotalConArriendoKm');
    if (ctxTotalArriendoKm && window.patentesList && window.costoTotalConArriendoKmList) {
        new Chart(ctxTotalArriendoKm, {
            type: 'bar',
            data: {
                labels: window.patentesList,
                datasets: [
                    {
                        label: 'Costo total (con arriendos) $/km',
                        data: window.costoTotalConArriendoKmList.map(v => v !== null ? v : 0),
                        backgroundColor: 'rgba(255, 159, 64, 0.7)',
                        borderColor: 'rgba(255, 159, 64, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { 
                            display: true, 
                            text: '$ / km' 
                        },
                        ticks: { 
                            callback: (v) => formatCurrency(v)
                        }
                    }
                },
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: { 
                        callbacks: { 
                            label: (ctx) => `${ctx.dataset.label}: ${formatCurrency(ctx.raw)}` 
                        } 
                    },
                    datalabels: { 
                        anchor: 'end', 
                        align: 'top',
                        formatter: (value) => formatCurrency(value)
                    } 
                }
            }
        });
    }

    // Gráfico Frecuencia de fallas
    const ctxFrec = document.getElementById('chartFrecuenciaFallas');
    if (ctxFrec && window.patentesDispList && window.frecuenciasList) {
        new Chart(ctxFrec, {
            type: 'bar',
            data: {
                labels: window.patentesDispList,
                datasets: [
                    {
                        label: 'Mant. correctivos cada 10.000 km',
                        data: window.frecuenciasList.map(v => v !== null ? v : 0),
                        backgroundColor: 'rgba(255, 99, 132, 0.7)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { 
                            display: true, 
                            text: 'Frecuencia' 
                        },
                        ticks: {
                            callback: (v) => v.toFixed(2)
                        }
                    }
                },
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${ctx.raw.toFixed(2)}`
                        }
                    },
                    datalabels: { 
                        anchor: 'end', 
                        align: 'top',
                        formatter: (value) => value.toFixed(2)
                    } 
                }
            }
        });
    }

    // Gráfico Promedio de días de indisponibilidad
    const ctxProm = document.getElementById('chartPromedioIndisponibilidad');
    if (ctxProm && window.patentesDispList && window.promediosList) {
        new Chart(ctxProm, {
            type: 'bar',
            data: {
                labels: window.patentesDispList,
                datasets: [
                    {
                        label: 'Días promedio fuera de servicio',
                        data: window.promediosList.map(v => v !== null ? v : 0),
                        backgroundColor: 'rgba(54, 162, 235, 0.7)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { 
                            display: true, 
                            text: 'Días' 
                        },
                        ticks: {
                            callback: (v) => v.toFixed(1)
                        }
                    }
                },
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${ctx.raw.toFixed(1)} días`
                        }
                    },
                    datalabels: { 
                        anchor: 'end', 
                        align: 'top',
                        formatter: (value) => value.toFixed(1)
                    } 
                }
            }
        });
    }

    // Gráfico Tiempo retención HBO
    const ctxHBO = document.getElementById('chartTiempoHBO');
    if (ctxHBO && window.patentesDispList && window.tiemposHBOList) {
        new Chart(ctxHBO, {
            type: 'bar',
            data: {
                labels: window.patentesDispList,
                datasets: [
                    {
                        label: 'Minutos en HBO',
                        data: window.tiemposHBOList.map(v => v !== null ? v : 0),
                        backgroundColor: 'rgba(75, 192, 192, 0.7)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { 
                            display: true, 
                            text: 'Minutos' 
                        },
                        ticks: {
                            callback: (v) => formatInteger(v)
                        }
                    }
                },
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${formatInteger(ctx.raw)} minutos`
                        }
                    },
                    datalabels: { 
                        anchor: 'end', 
                        align: 'top',
                        formatter: (value) => formatInteger(value)
                    } 
                }
            }
        });
    }
});
