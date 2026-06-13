// API_BASE_URL is now imported from config.js

// 1. Session and Token Helpers
function getAuthToken() {
    return localStorage.getItem('token');
}

function setAuthToken(token) {
    localStorage.setItem('token', token);
}

function removeAuthToken() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
}

function getCurrentUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
}

function setCurrentUser(user) {
    localStorage.setItem('user', JSON.stringify(user));
}

// 2. Route Protection Guard
function checkAuthentication() {
    const token = getAuthToken();
    const isLoginPage = window.location.pathname === '/' || window.location.pathname.endsWith('index.html');
    
    if (!token && !isLoginPage) {
        window.location.href = '/index.html';
    } else if (token && isLoginPage) {
        window.location.href = '/pages/dashboard.html';
    }
}

// 3. Centralized API Caller Wrapper
async function apiRequest(endpoint, options = {}) {
    const token = getAuthToken();
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {})
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const fetchOptions = {
        ...options,
        headers
    };
    
    // Add cache buster query parameter to bypass browser caching
    const separator = endpoint.includes('?') ? '&' : '?';
    const bustedEndpoint = `${endpoint}${separator}_cb=${Date.now()}`;
    
    try {
        const response = await fetch(`${API_BASE_URL}${bustedEndpoint}`, fetchOptions);
        
        if (response.status === 401) {
            // Token expired or invalid, redirect to login
            removeAuthToken();
            window.location.href = '/index.html';
            return null;
        }
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        
        // Handle file responses (PDF / Excel streaming)
        const contentType = response.headers.get('content-type');
        if (contentType && (contentType.includes('application/pdf') || contentType.includes('sheet'))) {
            return response.blob();
        }
        
        return await response.json();
    } catch (error) {
        console.error(`API Error on ${endpoint}:`, error);
        throw error;
    }
}

// 4. Inject Reusable Left Navigation Sidebar Component
// 4. Inject Reusable Left Navigation Sidebar Component
function toggleMobileSidebar(isOpen) {
    const sidebar = document.getElementById('sidebar-placeholder');
    if (!sidebar) return;
    
    let backdrop = document.getElementById('sidebar-backdrop');
    
    if (isOpen) {
        sidebar.classList.remove('hidden');
        sidebar.classList.add('fixed', 'inset-y-0', 'left-0', 'shadow-2xl', 'z-50', 'flex');
        sidebar.classList.remove('md:flex', 'my-4', 'ml-4', 'h-[calc(100vh-2rem)]', 'rounded-2xl'); // remove desktop float
        sidebar.classList.add('h-screen', 'w-64');
        sidebar.style.display = 'flex';
        
        // Add backdrop if it doesn't exist
        if (!backdrop) {
            backdrop = document.createElement('div');
            backdrop.id = 'sidebar-backdrop';
            backdrop.className = 'fixed inset-0 bg-black/60 z-40 md:hidden transition-opacity duration-300 opacity-0';
            document.body.appendChild(backdrop);
            // Trigger reflow for transition
            setTimeout(() => backdrop.classList.remove('opacity-0'), 10);
            
            backdrop.addEventListener('click', () => toggleMobileSidebar(false));
        }
    } else {
        sidebar.classList.add('hidden');
        sidebar.classList.remove('fixed', 'inset-y-0', 'left-0', 'shadow-2xl', 'z-50', 'flex', 'h-screen');
        sidebar.classList.add('md:flex', 'my-4', 'ml-4', 'h-[calc(100vh-2rem)]', 'rounded-2xl'); // restore desktop float
        sidebar.style.display = '';
        
        if (backdrop) {
            backdrop.classList.add('opacity-0');
            setTimeout(() => {
                if (backdrop.parentNode) {
                    backdrop.parentNode.removeChild(backdrop);
                }
            }, 300);
        }
    }
}

function injectSidebar() {
    const sidebarPlaceholder = document.getElementById('sidebar-placeholder');
    if (!sidebarPlaceholder) return;
    
    // Set premium dark floating sidebar layout class on desktop
    sidebarPlaceholder.className = "hidden md:flex h-[calc(100vh-2rem)] w-64 flex-col bg-[#0B0F19]/90 border border-white/5 my-4 ml-4 rounded-2xl p-md gap-xs flex-shrink-0 sticky top-4 z-50 shadow-2xl shadow-black/45 backdrop-blur-lg";
    
    const user = getCurrentUser();
    const name = user ? user.full_name : 'Analyst';
    const role = user ? user.role : 'Senior Analyst';
    const currentPath = window.location.pathname;
    
    const menuItems = [
        { name: 'Pricing Overview', path: '/pages/dashboard.html', icon: 'dashboard' },
        { name: 'Transaction Ingestion', path: '/pages/upload.html', icon: 'upload_file' },
        { name: 'Forecast Engine', path: '/pages/forecasting.html', icon: 'trending_up' },
        { name: 'Elasticity Profiles', path: '/pages/elasticity.html', icon: 'insights' },
        { name: 'Price Optimizer', path: '/pages/recommendations.html', icon: 'calculate' },
        { name: 'Scenario Simulator', path: '/pages/simulation.html', icon: 'science' },
        { name: 'Operational Ledger', path: '/pages/reports.html', icon: 'analytics' }
    ];
    
    let menuHtml = '';
    menuItems.forEach(item => {
        const isActive = currentPath.includes(item.path);
        const activeClass = isActive ? 'active' : '';
        
        menuHtml += `
            <a class="sidebar-nav-item ${activeClass}" href="${item.path}">
                <span class="material-symbols-outlined text-[20px]">${item.icon}</span>
                <span class="font-label-md text-label-md">${item.name}</span>
            </a>
        `;
    });
    
    sidebarPlaceholder.innerHTML = `
        <div class="px-md py-lg mb-md flex items-center justify-between gap-sm border-b border-white/5">
            <div class="flex items-center gap-sm">
                <div class="w-8 h-8 bg-primary rounded-xl flex items-center justify-center shadow-lg shadow-primary/20">
                    <span class="material-symbols-outlined text-on-surface text-[18px]" style="font-variation-settings: 'FILL' 1;">analytics</span>
                </div>
                <div>
                    <h1 class="font-headline-md text-[16px] font-bold text-primary tracking-tight">PriceSense</h1>
                    <p class="font-label-sm text-[10px] text-tertiary opacity-70">ML Analytics</p>
                </div>
            </div>
            <button id="close-sidebar-btn" class="md:hidden p-xs text-tertiary hover:text-on-surface">
                <span class="material-symbols-outlined">close</span>
            </button>
        </div>
        <nav class="flex-1 flex flex-col gap-xs">
            ${menuHtml}
        </nav>
        <div class="mt-auto flex flex-col gap-xs pt-md border-t border-white/5">
            <div class="px-md py-sm flex items-center gap-sm mb-xs bg-[#0B1020]/60 border border-white/5 rounded-xl mx-xs shadow-inner">
                <div class="w-8 h-8 rounded-full bg-primary text-on-surface flex items-center justify-center font-bold text-xs shadow-md">
                    ${name.charAt(0).toUpperCase()}
                </div>
                <div class="overflow-hidden">
                    <p class="font-label-md text-label-md text-on-surface leading-none truncate">${name}</p>
                    <p class="font-label-sm text-label-sm text-tertiary opacity-70 mt-1 truncate capitalize">${role}</p>
                </div>
            </div>
            <button id="logout-btn" class="flex items-center gap-md px-md py-sm text-tertiary hover:text-error hover:bg-white/5 rounded-xl transition-all duration-200 w-full text-left mb-xs">
                <span class="material-symbols-outlined">logout</span>
                <span class="font-label-md text-label-md">Logout</span>
            </button>
        </div>
    `;
    
    // Bind logout button click
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            removeAuthToken();
            window.location.href = '/index.html';
        });
    }

    // Bind close button
    const closeBtn = document.getElementById('close-sidebar-btn');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => toggleMobileSidebar(false));
    }
}

// 5. Utility Data Format Helpers
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 2
    }).format(amount);
}

function formatPercent(value) {
    const prefix = value >= 0 ? '+' : '';
    return `${prefix}${(value * 100).toFixed(1)}%`;
}

function safeNum(val, fallback = 0.0) {
    const parsed = parseFloat(val);
    if (val === null || val === undefined || isNaN(parsed) || !isFinite(parsed)) {
        return fallback;
    }
    return parsed;
}

// 6. Global Setup Trigger
document.addEventListener('DOMContentLoaded', () => {
    checkAuthentication();
    injectSidebar();
    
    // Bind mobile menu toggle dynamically in case sidebar is injected later or header is loaded
    const toggleBtn = document.getElementById('mobile-menu-toggle');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => toggleMobileSidebar(true));
    }
});

// 7. Centralized State Store
const StateStore = {
    getSelectedProduct() {
        return localStorage.getItem('selected_product_id');
    },
    setSelectedProduct(productId) {
        if (productId) {
            localStorage.setItem('selected_product_id', productId);
        } else {
            localStorage.removeItem('selected_product_id');
        }
    },
    getActiveDataset() {
        return localStorage.getItem('active_dataset_id');
    },
    setActiveDataset(datasetId) {
        const prev = localStorage.getItem('active_dataset_id');
        if (datasetId) {
            if (prev !== datasetId) {
                localStorage.setItem('active_dataset_id', datasetId);
                localStorage.removeItem('selected_product_id'); // Reset selected product on dataset change
            }
        } else {
            localStorage.removeItem('active_dataset_id');
        }
    }
};

// Listen for dataset changes across tabs
window.addEventListener('storage', (e) => {
    if (e.key === 'active_dataset_id') {
        // Trigger a reload to automatically re-fetch calculations
        window.location.reload();
    }
});

window.StateStore = StateStore;
window.safeNum = safeNum;

// 8. Reusable Dynamic Category Color Palette Generator
function getCategoryPalette(categoriesList) {
    // 12 professional SaaS hues
    const baseHues = [
        190, // cyan
        215, // blue
        155, // emerald
        265, // violet
        40,  // amber
        175, // teal
        240, // indigo
        335, // rose
        200, // sky
        25,  // orange
        75,  // lime
        310  // pink
    ];
    const colors = {};
    const uniqueCategories = [...new Set(categoriesList)];
    uniqueCategories.forEach((cat, index) => {
        if (index < baseHues.length) {
            colors[cat] = `hsla(${baseHues[index]}, 80%, 55%, 0.85)`;
        } else {
            // Golden ratio distribution to space out unlimited categories evenly
            const extraHue = Math.round((index * 137.5) % 360);
            colors[cat] = `hsla(${extraHue}, 75%, 55%, 0.85)`;
        }
    });
    return colors;
}

window.getCategoryPalette = getCategoryPalette;
