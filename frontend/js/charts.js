// charts.js - Chart.js Creation and Interaction Utilities

const PREMIUM_PALETTE = [
    "#3B82F6",
    "#8B5CF6",
    "#EC4899",
    "#14B8A6",
    "#F59E0B",
    "#EF4444",
    "#22C55E",
    "#06B6D4",
    "#F97316",
    "#A855F7"
];

const dynamicCategoryColors = {};
let colorCounter = 0;

function getCategoryColor(category) {
    if (!category) return '#64748B';
    if (dynamicCategoryColors[category]) {
        return dynamicCategoryColors[category];
    }
    const color = PREMIUM_PALETTE[colorCounter % PREMIUM_PALETTE.length];
    dynamicCategoryColors[category] = color;
    colorCounter++;
    return color;
}

function hexToRgba(hex, opacity) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${opacity})`;
}

function brightenColor(hex, percent) {
    hex = hex.replace(/^\s*#|\s*$/g, '');
    if (hex.length === 3) {
        hex = hex.replace(/(.)/g, '$1$1');
    }
    let r = parseInt(hex.substr(0, 2), 16),
        g = parseInt(hex.substr(2, 2), 16),
        b = parseInt(hex.substr(4, 2), 16);
    
    const amt = Math.round(2.55 * percent);
    r = Math.min(255, Math.max(0, r + amt));
    g = Math.min(255, Math.max(0, g + amt));
    b = Math.min(255, Math.max(0, b + amt));
    
    const rHex = r.toString(16).padStart(2, '0');
    const gHex = g.toString(16).padStart(2, '0');
    const bHex = b.toString(16).padStart(2, '0');
    return `#${rHex}${gHex}${bHex}`;
}


function getMetricConfig(metric) {
    const configs = {
        "revenue": {
            label: "Revenue",
            color: "#3B82F6", // Blue
            gradStart: "rgba(59, 130, 246, 0.06)",
            gradEnd: "rgba(59, 130, 246, 0.00)",
            format: (v) => formatCurrency(v)
        },
        "profit": {
            label: "Profit",
            color: "#14B8A6", // Teal
            gradStart: "rgba(20, 184, 166, 0.06)",
            gradEnd: "rgba(20, 184, 166, 0.00)",
            format: (v) => formatCurrency(v)
        },
        "quantity_sold": {
            label: "Orders",
            color: "#8B5CF6", // Purple
            gradStart: "rgba(139, 92, 246, 0.06)",
            gradEnd: "rgba(139, 92, 246, 0.00)",
            format: (v) => v.toLocaleString()
        }
    };
    return configs[metric] || configs["revenue"];
}

/**
 * Creates the main trends line chart.
 * Configured with tension 0.35, hover effects, zoom/pan and double-axes support.
 */
function createTrendChart(canvasId, labels, rawValues, trendValues, metricName) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;
    const ctx = canvas.getContext('2d');
    
    const config = getMetricConfig(metricName);
    
    // Create elegant area fill gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, 320);
    gradient.addColorStop(0, config.gradStart);
    gradient.addColorStop(1, config.gradEnd);
    
    const datasets = [
        {
            label: config.label,
            data: rawValues,
            borderColor: config.color,
            backgroundColor: gradient,
            fill: true,
            tension: 0.35,
            borderWidth: 3,
            pointRadius: 0,
            pointHoverRadius: 6,
            pointBackgroundColor: config.color,
            pointBorderColor: '#060913',
            pointBorderWidth: 2,
            yAxisID: 'y'
        },
        {
            label: `${config.label} Trendline`,
            data: trendValues,
            borderColor: '#64748B', // Neutral gray
            borderDash: [6, 4],
            borderWidth: 1.5,
            fill: false,
            tension: 0.35,
            pointRadius: 0,
            pointHoverRadius: 0,
            opacity: 0.6,
            yAxisID: 'y'
        }
    ];

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'nearest' // Mode nearest for quick selection
            },
            plugins: {
                legend: {
                    position: 'top',
                    align: 'end',
                    labels: {
                        color: '#94A3B8',
                        boxWidth: 8,
                        usePointStyle: true,
                        pointStyle: 'circle',
                        font: { family: 'Inter', size: 11, weight: 500 }
                    }
                },
                tooltip: {
                    enabled: false, // We render a customized HTML tooltip in dashboard.js for premium styling
                    external: externalTooltipHandler
                },
                zoom: {
                    zoom: {
                        wheel: { enabled: true, speed: 0.05 },
                        pinch: { enabled: true },
                        mode: 'x'
                    },
                    pan: {
                        enabled: true,
                        mode: 'x',
                        threshold: 10
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: {
                        color: '#64748B',
                        maxTicksLimit: 12,
                        font: { family: 'Inter', size: 10, weight: 500 }
                    }
                },
                y: {
                    position: 'left',
                    grid: {
                        color: 'rgba(255, 255, 255, 0.02)',
                        borderDash: [5, 5]
                    },
                    ticks: {
                        color: '#64748B',
                        font: { family: 'Inter', size: 10 },
                        callback: function(value) {
                            if (metricName === 'quantity_sold') return value.toLocaleString();
                            if (value >= 1000000) return '₹' + (value / 1000000).toFixed(1) + 'M';
                            if (value >= 1000) return '₹' + (value / 1000).toFixed(0) + 'k';
                            return '₹' + value;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Custom HTML Tooltip Renderer.
 * Stripe/Bloomberg-styled floating overlay.
 */
function externalTooltipHandler(context) {
    // Tooltip Element
    let tooltipEl = document.getElementById('chartjs-tooltip');

    // Create element on first render
    if (!tooltipEl) {
        tooltipEl = document.createElement('div');
        tooltipEl.id = 'chartjs-tooltip';
        tooltipEl.className = 'absolute bg-[#0B1020]/95 border border-white/10 rounded-xl p-md shadow-2xl pointer-events-none transition-all duration-150 z-50 text-slate-100 font-sans backdrop-blur-md min-w-[200px]';
        document.body.appendChild(tooltipEl);
    }

    // Hide if no tooltip
    const tooltipModel = context.tooltip;
    if (tooltipModel.opacity === 0) {
        tooltipEl.style.opacity = 0;
        return;
    }

    // Set caret Position
    tooltipEl.classList.remove('above', 'below', 'no-transform');
    if (tooltipModel.yAlign) {
        tooltipEl.classList.add(tooltipModel.yAlign);
    } else {
        tooltipEl.classList.add('no-transform');
    }

    // Set Text Content
    if (tooltipModel.body) {
        const titleLines = tooltipModel.title || [];
        const labelIndex = tooltipModel.dataPoints[0].dataIndex;
        
        // Fetch raw data references from state
        const rawRecord = window.currentTrendData[labelIndex];
        if (rawRecord) {
            const dateStr = rawRecord.date;
            const rev = rawRecord.revenue;
            const prof = rawRecord.profit;
            const orders = rawRecord.quantity_sold;
            const topCat = rawRecord.top_category || 'N/A';
            
            // Calculate growth compared to previous day/point
            let growthStr = '0.0%';
            let growthClass = 'text-slate-400';
            if (labelIndex > 0) {
                const prevRecord = window.currentTrendData[labelIndex - 1];
                const activeMetric = window.activeMetric;
                const currentVal = rawRecord[activeMetric];
                const prevVal = prevRecord[activeMetric];
                if (prevVal > 0) {
                    const diff = ((currentVal - prevVal) / prevVal * 100);
                    growthStr = `${diff >= 0 ? '+' : ''}${diff.toFixed(1)}%`;
                    growthClass = diff >= 0 ? 'text-emerald-400' : 'text-red-400';
                }
            }

            let html = `
                <div class="space-y-2">
                    <div class="flex justify-between items-center border-b border-white/5 pb-1 gap-4">
                        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Details</span>
                        <span class="text-xs font-semibold text-white font-mono">${dateStr}</span>
                    </div>
                    <div class="space-y-1 font-mono">
                        <div class="flex justify-between items-center text-xs gap-4">
                            <span class="text-slate-400 text-[10px]">Revenue:</span>
                            <span class="font-semibold text-slate-200">${formatCurrency(rev)}</span>
                        </div>
                        <div class="flex justify-between items-center text-xs gap-4">
                            <span class="text-slate-400 text-[10px]">Profit:</span>
                            <span class="font-semibold text-emerald-400">${formatCurrency(prof)}</span>
                        </div>
                        <div class="flex justify-between items-center text-xs gap-4">
                            <span class="text-slate-400 text-[10px]">Orders:</span>
                            <span class="font-semibold text-slate-200">${orders.toLocaleString()}</span>
                        </div>
                        <div class="flex justify-between items-center text-xs gap-4">
                            <span class="text-slate-400 text-[10px]">Growth:</span>
                            <span class="font-bold ${growthClass}">${growthStr}</span>
                        </div>
                        <div class="flex justify-between items-center text-xs border-t border-white/5 pt-1.5 gap-4">
                            <span class="text-slate-400 text-[10px]">Top Category:</span>
                            <span class="font-bold px-1.5 py-0.5 rounded text-[9px] bg-blue-500/10 text-blue-400 border border-blue-500/20">${topCat}</span>
                        </div>
                    </div>
                </div>
            `;
            tooltipEl.innerHTML = html;
        }
    }

    const position = context.chart.canvas.getBoundingClientRect();
    
    // Display, position, and set styles
    tooltipEl.style.opacity = 1;
    tooltipEl.style.left = position.left + window.pageXOffset + tooltipModel.caretX + 15 + 'px';
    tooltipEl.style.top = position.top + window.pageYOffset + tooltipModel.caretY - 50 + 'px';
}
