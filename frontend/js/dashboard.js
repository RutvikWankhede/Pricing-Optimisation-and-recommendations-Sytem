// dashboard.js - Page controller and state management for PriceSense dashboard

// Global States
window.activeInterval = 'daily';      // 'daily' | 'weekly' | 'monthly'
window.activeMetric = 'revenue';       // 'revenue' | 'profit' | 'quantity_sold'
window.activeCategory = '';            // empty string means 'All Categories'
window.rawDailyData = [];              // Stores raw daily data from backend
window.currentTrendData = [];          // Stores aggregated data currently rendered in the chart

// Local aggregation helpers
function parseLocalDate(dateStr) {
    const parts = dateStr.split('-');
    return new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
}

function aggregateDaily(data) {
    return data.map(item => ({
        date: item.date,
        revenue: item.revenue,
        profit: item.profit,
        quantity_sold: item.quantity_sold,
        avg_order_value: item.avg_order_value,
        top_category: item.top_category,
        rolling_avg_3: item.rolling_avg_3,
        rolling_avg_7: item.rolling_avg_7
    })).sort((a, b) => a.date.localeCompare(b.date));
}

function aggregateWeekly(data) {
    if (data.length === 0) return [];
    
    const dates = data.map(item => item.date);
    const maxDateStr = dates.reduce((a, b) => a > b ? a : b);
    const maxDate = parseLocalDate(maxDateStr);
    
    const weeklyGroups = {};
    
    data.forEach(item => {
        const d = parseLocalDate(item.date);
        const day = d.getDay();
        const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Monday as start of week
        const monday = new Date(d.setDate(diff));
        const weekKey = monday.getFullYear() + '-' + 
            String(monday.getMonth() + 1).padStart(2, '0') + '-' + 
            String(monday.getDate()).padStart(2, '0');
        
        if (!weeklyGroups[weekKey]) {
            weeklyGroups[weekKey] = {
                date: weekKey,
                revenue: 0,
                profit: 0,
                quantity_sold: 0,
                maxRev: item.revenue,
                top_category: item.top_category
            };
        }
        
        weeklyGroups[weekKey].revenue += item.revenue;
        weeklyGroups[weekKey].profit += item.profit;
        weeklyGroups[weekKey].quantity_sold += item.quantity_sold;
        if (item.revenue > weeklyGroups[weekKey].maxRev) {
            weeklyGroups[weekKey].maxRev = item.revenue;
            weeklyGroups[weekKey].top_category = item.top_category;
        }
    });

    const weeklyList = Object.values(weeklyGroups)
        .filter(w => {
            const monday = parseLocalDate(w.date);
            const sunday = new Date(monday);
            sunday.setDate(monday.getDate() + 6);
            return sunday <= maxDate;
        })
        .sort((a, b) => a.date.localeCompare(b.date));
    
    // Compute moving averages on the aggregated weekly points
    weeklyList.forEach((w, idx) => {
        w.avg_order_value = w.quantity_sold > 0 ? (w.revenue / w.quantity_sold) : 0.0;
        
        // 3-week rolling average
        let sum3 = 0, count3 = 0;
        for (let i = Math.max(0, idx - 2); i <= idx; i++) {
            sum3 += weeklyList[i][window.activeMetric];
            count3++;
        }
        w.rolling_avg_3 = count3 > 0 ? (sum3 / count3) : 0;

        // 7-week rolling average
        let sum7 = 0, count7 = 0;
        for (let i = Math.max(0, idx - 6); i <= idx; i++) {
            sum7 += weeklyList[i][window.activeMetric];
            count7++;
        }
        w.rolling_avg_7 = count7 > 0 ? (sum7 / count7) : 0;
    });

    return weeklyList;
}

function aggregateMonthly(data) {
    if (data.length === 0) return [];
    
    const dates = data.map(item => item.date);
    const maxDateStr = dates.reduce((a, b) => a > b ? a : b);
    const maxDate = parseLocalDate(maxDateStr);

    const monthlyGroups = {};
    
    data.forEach(item => {
        const monthKey = item.date.substring(0, 7) + "-01"; // Group by YYYY-MM-01
        
        if (!monthlyGroups[monthKey]) {
            monthlyGroups[monthKey] = {
                date: monthKey,
                revenue: 0,
                profit: 0,
                quantity_sold: 0,
                maxRev: item.revenue,
                top_category: item.top_category
            };
        }
        
        monthlyGroups[monthKey].revenue += item.revenue;
        monthlyGroups[monthKey].profit += item.profit;
        monthlyGroups[monthKey].quantity_sold += item.quantity_sold;
        if (item.revenue > monthlyGroups[monthKey].maxRev) {
            monthlyGroups[monthKey].maxRev = item.revenue;
            monthlyGroups[monthKey].top_category = item.top_category;
        }
    });

    const monthlyList = Object.values(monthlyGroups)
        .filter(m => {
            const firstDay = parseLocalDate(m.date);
            const lastDay = new Date(firstDay.getFullYear(), firstDay.getMonth() + 1, 0);
            return lastDay <= maxDate;
        })
        .sort((a, b) => a.date.localeCompare(b.date));
    
    // Compute moving averages on the aggregated monthly points
    monthlyList.forEach((m, idx) => {
        m.avg_order_value = m.quantity_sold > 0 ? (m.revenue / m.quantity_sold) : 0.0;
        
        // 3-month rolling average
        let sum3 = 0, count3 = 0;
        for (let i = Math.max(0, idx - 2); i <= idx; i++) {
            sum3 += monthlyList[i][window.activeMetric];
            count3++;
        }
        m.rolling_avg_3 = count3 > 0 ? (sum3 / count3) : 0;

        // 7-month rolling average
        let sum7 = 0, count7 = 0;
        for (let i = Math.max(0, idx - 6); i <= idx; i++) {
            sum7 += monthlyList[i][window.activeMetric];
            count7++;
        }
        m.rolling_avg_7 = count7 > 0 ? (sum7 / count7) : 0;
    });

    return monthlyList;
}

// Format date label for the chart based on interval
function formatChartDate(dateStr, interval) {
    const d = new Date(dateStr);
    if (interval === 'monthly') {
        return d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    } else if (interval === 'weekly') {
        return 'Wk of ' + d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } else {
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
}

// Fetch raw daily trends from server and update local state
async function fetchTrendData() {
    try {
        const categoryParam = window.activeCategory ? `&category=${encodeURIComponent(window.activeCategory)}` : '';
        const endpoint = `/dashboard/trends?metric=${window.activeMetric}${categoryParam}`;
        
        const data = await apiRequest(endpoint);
        if (data) {
            window.rawDailyData = data;
            renderActiveChart();
        }
    } catch (e) {
        console.error("Failed to fetch trends dataset:", e);
    }
}

// Locally aggregate and draw the Chart
function renderActiveChart() {
    let aggregated = [];
    if (window.activeInterval === 'weekly') {
        aggregated = aggregateWeekly(window.rawDailyData);
    } else if (window.activeInterval === 'monthly') {
        aggregated = aggregateMonthly(window.rawDailyData);
    } else {
        aggregated = aggregateDaily(window.rawDailyData);
    }
    
    // Store current state for hover callbacks
    window.currentTrendData = aggregated;
    
    const labels = aggregated.map(item => formatChartDate(item.date, window.activeInterval));
    const rawValues = aggregated.map(item => item[window.activeMetric]);
    const avg7 = aggregated.map(item => item.rolling_avg_7);
    
    if (window.trendChartInstance) {
        window.trendChartInstance.destroy();
    }
    
    window.trendChartInstance = createTrendChart(
        'trend-chart',
        labels,
        rawValues,
        avg7,
        window.activeMetric
    );
}

// UI state update for pills
function updatePillActiveStates() {
    // Intervals
    document.querySelectorAll('.interval-pill').forEach(btn => {
        if (btn.id === `btn-interval-${window.activeInterval}`) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Metrics
    document.querySelectorAll('.metric-pill').forEach(btn => {
        if (btn.id === `btn-metric-${window.activeMetric}`) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// DOM setup and initializations
document.addEventListener('DOMContentLoaded', async () => {
    // 1. Populate top profile bar
    const user = getCurrentUser();
    if (user) {
        document.getElementById('user-name-placeholder').innerText = user.full_name;
        document.getElementById('user-role-placeholder').innerText = user.role === 'analyst' ? 'Pricing Analyst' : 'Senior Executive';
        document.getElementById('user-avatar-placeholder').innerText = user.full_name.charAt(0).toUpperCase();
    }

    try {
        // 2. Fetch Dashboard summary to populate KPIs and tables
        const data = await apiRequest('/dashboard/summary');
        if (!data) return;

        if (data.sales_trends.length === 0) {
            document.getElementById('dashboard-data-container').classList.add('hidden');
            document.getElementById('dashboard-empty-state').classList.remove('hidden');
            return;
        }

        // Render KPIs
        const kpis = data.kpis;
        const kpiGrid = document.getElementById('kpi-grid');
        kpiGrid.className = "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 w-full";
        kpiGrid.innerHTML = `
            <!-- Card 1: Revenue -->
            <div class="dashboard-card card-glow-blue p-6 flex flex-col justify-between relative overflow-hidden group">
                <div class="absolute -right-8 -top-8 w-24 h-24 bg-blue-500/10 rounded-full blur-xl group-hover:bg-blue-500/20 transition-all duration-300"></div>
                <div class="flex items-center justify-between z-10">
                    <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">${kpis.total_revenue.title}</span>
                    <div class="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                        <span class="material-symbols-outlined text-[18px]">payments</span>
                    </div>
                </div>
                <div class="mt-4 z-10">
                    <div class="text-2xl lg:text-3xl font-bold text-slate-50 tracking-tight font-sans truncate" title="${kpis.total_revenue.value}">${kpis.total_revenue.value}</div>
                    <div class="flex items-center gap-2 mt-2">
                        <span class="${kpis.total_revenue.trend === 'up' ? 'badge-trend-up' : 'badge-trend-down'}">${kpis.total_revenue.change}</span>
                        <span class="text-[10px] text-slate-500">vs last period</span>
                    </div>
                </div>
                <div class="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 to-cyan-400 opacity-50"></div>
            </div>
            
            <!-- Card 2: Profit -->
            <div class="dashboard-card card-glow-emerald p-6 flex flex-col justify-between relative overflow-hidden group">
                <div class="absolute -right-8 -top-8 w-24 h-24 bg-emerald-500/10 rounded-full blur-xl group-hover:bg-emerald-500/20 transition-all duration-300"></div>
                <div class="flex items-center justify-between z-10">
                    <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">${kpis.total_profit.title}</span>
                    <div class="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                        <span class="material-symbols-outlined text-[18px]">trending_up</span>
                    </div>
                </div>
                <div class="mt-4 z-10">
                    <div class="text-2xl lg:text-3xl font-bold text-slate-50 tracking-tight font-sans truncate" title="${kpis.total_profit.value}">${kpis.total_profit.value}</div>
                    <div class="flex items-center gap-2 mt-2">
                        <span class="${kpis.total_profit.trend === 'up' ? 'badge-trend-up' : 'badge-trend-down'}">${kpis.total_profit.change}</span>
                        <span class="text-[10px] text-slate-500">vs last period</span>
                    </div>
                </div>
                <div class="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-500 to-teal-400 opacity-50"></div>
            </div>
            
            <!-- Card 3: Margin -->
            <div class="dashboard-card card-glow-purple p-6 flex flex-col justify-between relative overflow-hidden group">
                <div class="absolute -right-8 -top-8 w-24 h-24 bg-purple-500/10 rounded-full blur-xl group-hover:bg-purple-500/20 transition-all duration-300"></div>
                <div class="flex items-center justify-between z-10">
                    <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">${kpis.avg_margin.title}</span>
                    <div class="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                        <span class="material-symbols-outlined text-[18px]">percent</span>
                    </div>
                </div>
                <div class="mt-4 z-10">
                    <div class="text-2xl lg:text-3xl font-bold text-slate-50 tracking-tight font-sans truncate" title="${kpis.avg_margin.value}">${kpis.avg_margin.value}</div>
                    <div class="flex items-center gap-2 mt-2">
                        <span class="${kpis.avg_margin.trend === 'up' ? 'badge-trend-up' : 'badge-trend-down'}">${kpis.avg_margin.change}</span>
                        <span class="text-[10px] text-slate-500">vs last period</span>
                    </div>
                </div>
                <div class="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-purple-500 to-pink-500 opacity-50"></div>
            </div>
            
            <!-- Card 4: Products -->
            <div class="dashboard-card card-glow-orange p-6 flex flex-col justify-between relative overflow-hidden group">
                <div class="absolute -right-8 -top-8 w-24 h-24 bg-orange-500/10 rounded-full blur-xl group-hover:bg-orange-500/20 transition-all duration-300"></div>
                <div class="flex items-center justify-between z-10">
                    <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">${kpis.active_products.title}</span>
                    <div class="w-8 h-8 rounded-lg bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-400">
                        <span class="material-symbols-outlined text-[18px]">inventory_2</span>
                    </div>
                </div>
                <div class="mt-4 z-10">
                    <div class="text-2xl lg:text-3xl font-bold text-slate-50 tracking-tight font-sans truncate" title="${kpis.active_products.value}">${kpis.active_products.value}</div>
                    <div class="flex items-center gap-2 mt-2">
                        <span class="${kpis.active_products.trend === 'up' ? 'badge-trend-up' : 'badge-trend-down'}">${kpis.active_products.change}</span>
                        <span class="text-[10px] text-slate-500">vs last period</span>
                    </div>
                </div>
                <div class="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-orange-500 to-amber-500 opacity-50"></div>
            </div>
        `;

        // Render Category Mix Doughnut Chart
        const catCtx = document.getElementById('category-chart').getContext('2d');
        const sortedCategoryShare = [...data.category_share].sort((a, b) => safeNum(b.revenue) - safeNum(a.revenue));
        const catColors = {};
        sortedCategoryShare.forEach((c, idx) => {
            catColors[c.category] = PREMIUM_PALETTE[idx % PREMIUM_PALETTE.length];
        });
        const totalRevenue = sortedCategoryShare.reduce((acc, c) => acc + safeNum(c.revenue), 0);

        new Chart(catCtx, {
            type: 'doughnut',
            data: {
                labels: sortedCategoryShare.map(c => c.category),
                datasets: [{
                    data: sortedCategoryShare.map(c => c.revenue),
                    backgroundColor: sortedCategoryShare.map(c => catColors[c.category]),
                    hoverBackgroundColor: sortedCategoryShare.map(c => brightenColor(catColors[c.category], 12)),
                    borderWidth: 2,
                    borderColor: '#060913',
                    hoverBorderColor: '#ffffff',
                    hoverBorderWidth: 2,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '68%',
                onClick: (event, activeElements) => {
                    if (activeElements.length > 0) {
                        const index = activeElements[0].index;
                        const categoryName = sortedCategoryShare[index].category;
                        document.getElementById('category-filter-dropdown').value = categoryName;
                        window.activeCategory = categoryName;
                        fetchTrendData();
                        filterByCategory(categoryName);
                    }
                },
                onHover: (event, chartElements, chart) => {
                    const activeChart = chart || event.chart;
                    activeChart.canvas.style.cursor = chartElements.length ? 'pointer' : 'default';
                },
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart',
                    animateRotate: true,
                    animateScale: true
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#94A3B8',
                            boxWidth: 8,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            font: { family: 'Inter', size: 11, weight: 500 },
                            padding: 20
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(11, 15, 25, 0.95)',
                        titleColor: '#F8FAFC',
                        bodyColor: '#94A3B8',
                        borderColor: 'rgba(255, 255, 255, 0.08)',
                        borderWidth: 1,
                        padding: 10,
                        cornerRadius: 6,
                        titleFont: { family: 'Inter', size: 11, weight: 'bold' },
                        bodyFont: { family: 'Inter', size: 11, weight: 500 },
                        boxPadding: 6,
                        usePointStyle: true,
                        callbacks: {
                            label: function(context) {
                                let label = context.label || '';
                                if (label) label += ': ';
                                if (context.parsed !== null) {
                                    const pct = totalRevenue > 0 ? ((context.parsed / totalRevenue) * 100).toFixed(1) : '0';
                                    label += `${formatCurrency(context.parsed)} (${pct}%)`;
                                }
                                return label;
                            }
                        }
                    }
                }
            }
        });

        // 3. Build Category Dropdown list
        const dropdown = document.getElementById('category-filter-dropdown');
        if (dropdown) {
            dropdown.innerHTML = '<option value="">All Categories</option>';
            data.category_share.forEach(c => {
                dropdown.innerHTML += `<option value="${c.category}">${c.category}</option>`;
            });
            
            // Listen for dropdown changes
            dropdown.addEventListener('change', (e) => {
                window.activeCategory = e.target.value;
                fetchTrendData();
                if (window.activeCategory) {
                    filterByCategory(window.activeCategory);
                } else {
                    clearCategoryFilter();
                }
            });
        }

        // Render Products table
        const allTopProducts = data.top_products;
        function renderProductsTable(productsList) {
            const tbody = document.getElementById('top-products-body');
            if (productsList.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" class="px-4 py-8 text-center text-slate-500 font-medium">No products match this category.</td></tr>`;
                return;
            }
            
            let rows = '';
            productsList.forEach(p => {
                const colorHex = catColors[p.category] || '#64748B';
                rows += `
                    <tr class="hover-highlight border-b border-white/5 transition-colors group">
                        <td class="px-4 py-4 text-sm font-semibold text-slate-100">${p.product_name}</td>
                        <td class="px-4 py-4 text-xs font-medium text-slate-400">
                            <div class="flex items-center gap-2">
                                <span class="category-dot" style="background-color: ${colorHex}"></span>
                                <span>${p.category}</span>
                            </div>
                        </td>
                        <td class="px-4 py-4 text-xs text-right font-mono text-slate-300">${p.quantity_sold.toLocaleString()}</td>
                        <td class="px-4 py-4 text-xs text-right font-mono font-medium text-slate-100">${formatCurrency(p.revenue)}</td>
                        <td class="px-4 py-4 text-xs text-right font-mono font-semibold text-emerald-400">${formatCurrency(p.profit)}</td>
                    </tr>
                `;
            });
            tbody.innerHTML = rows;
        }

        window.filterByCategory = (categoryName) => {
            const filtered = allTopProducts.filter(p => p.category === categoryName);
            renderProductsTable(filtered);
            
            const filterBadge = document.getElementById('active-category-filter');
            const categorySpan = document.getElementById('filter-category-name');
            if (categorySpan) categorySpan.innerText = categoryName;
            if (filterBadge) filterBadge.classList.remove('hidden');
        };

        window.clearCategoryFilter = () => {
            renderProductsTable(allTopProducts);
            const filterBadge = document.getElementById('active-category-filter');
            if (filterBadge) filterBadge.classList.add('hidden');
            if (dropdown) dropdown.value = "";
            window.activeCategory = "";
            fetchTrendData();
        };

        renderProductsTable(allTopProducts);

    } catch (error) {
        console.error(error);
        let errorHtml = '';
        if (error.message && error.message.includes('waking up')) {
            errorHtml = `
                <div class="flex flex-col items-center justify-center p-12 text-center col-span-1 sm:col-span-2 lg:col-span-4 bg-[#0B0F19]/50 rounded-2xl border border-blue-500/20 backdrop-blur-md">
                    <div class="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                    <h3 class="text-xl font-bold text-slate-100 mb-2">Backend Waking Up</h3>
                    <p class="text-slate-400">The free Render instance is spinning up. This usually takes about 30-50 seconds.</p>
                    <button onclick="window.location.reload()" class="mt-6 px-6 py-2 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded-xl hover:bg-blue-500/30 transition-colors">Retry Now</button>
                </div>
            `;
        } else {
            errorHtml = `<div class="bg-error/10 border border-error/20 text-error p-6 rounded-2xl col-span-1 sm:col-span-2 lg:col-span-4 text-sm shadow-lg">Failed to load analytics: ${error.message}</div>`;
        }
        const kpiGrid = document.getElementById('kpi-grid');
        if (kpiGrid) {
            kpiGrid.className = "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 w-full";
            kpiGrid.innerHTML = errorHtml;
        }
        // Also hide the chart containers if there's an error
        const mainContent = document.getElementById('dashboard-data-container');
        if (mainContent) {
            mainContent.classList.add('hidden');
        }
    }

    // 4. Set up Event Listeners for Pill selectors
    // Intervals
    document.getElementById('btn-interval-daily').addEventListener('click', () => {
        window.activeInterval = 'daily';
        updatePillActiveStates();
        renderActiveChart();
    });
    document.getElementById('btn-interval-weekly').addEventListener('click', () => {
        window.activeInterval = 'weekly';
        updatePillActiveStates();
        renderActiveChart();
    });
    document.getElementById('btn-interval-monthly').addEventListener('click', () => {
        window.activeInterval = 'monthly';
        updatePillActiveStates();
        renderActiveChart();
    });

    // Metrics
    document.getElementById('btn-metric-revenue').addEventListener('click', () => {
        window.activeMetric = 'revenue';
        updatePillActiveStates();
        fetchTrendData(); // Refetch to recalculate rolling averages for profit on server
    });
    document.getElementById('btn-metric-profit').addEventListener('click', () => {
        window.activeMetric = 'profit';
        updatePillActiveStates();
        fetchTrendData();
    });
    document.getElementById('btn-metric-orders').addEventListener('click', () => {
        window.activeMetric = 'quantity_sold';
        updatePillActiveStates();
        fetchTrendData();
    });

    // Zoom Reset
    document.getElementById('reset-zoom-btn').addEventListener('click', () => {
        if (window.trendChartInstance) {
            window.trendChartInstance.resetZoom();
        }
    });

    // CSV export route link
    document.getElementById('export-csv-btn').addEventListener('click', () => {
        window.location.href = '/pages/reports.html';
    });

    // Load initial trend data
    updatePillActiveStates();
    fetchTrendData();
});
