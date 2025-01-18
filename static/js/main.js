// Utility Functions
const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
};

const formatDate = (date) => {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    }).format(new Date(date));
};

// Form Validation Functions
const validateForm = (form) => {
    let isValid = true;
    const inputs = form.querySelectorAll('input[required], select[required]');
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            showError(input, 'This field is required');
        } else {
            clearError(input);
        }
    });

    return isValid;
};

const showError = (input, message) => {
    const formGroup = input.closest('.mb-3');
    const errorDiv = formGroup.querySelector('.invalid-feedback') || document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;
    input.classList.add('is-invalid');
    if (!formGroup.querySelector('.invalid-feedback')) {
        formGroup.appendChild(errorDiv);
    }
};

const clearError = (input) => {
    input.classList.remove('is-invalid');
    const formGroup = input.closest('.mb-3');
    const errorDiv = formGroup.querySelector('.invalid-feedback');
    if (errorDiv) {
        errorDiv.remove();
    }
};

// Transaction Form Handlers
const initTransactionForm = () => {
    const form = document.getElementById('addTransactionForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!validateForm(form)) return;

        const formData = new FormData(form);
        try {
            const response = await fetch('/api/transactions', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                window.location.reload();
            } else {
                const data = await response.json();
                showError(form.querySelector('#amount'), data.message || 'Failed to add transaction');
            }
        } catch (error) {
            console.error('Error:', error);
        }
    });

    // Category filtering based on transaction type
    const typeSelect = form.querySelector('select[name="type"]');
    const categorySelect = form.querySelector('select[name="category_id"]');
    
    if (typeSelect && categorySelect) {
        typeSelect.addEventListener('change', () => filterCategories(typeSelect, categorySelect));
        // Initial filtering
        filterCategories(typeSelect, categorySelect);
    }
};

const filterCategories = (typeSelect, categorySelect) => {
    const selectedType = typeSelect.value;
    const options = categorySelect.querySelectorAll('option');
    
    options.forEach(option => {
        const categoryType = option.dataset.type;
        if (categoryType) {
            option.style.display = categoryType === selectedType ? '' : 'none';
        }
    });
    
    // Reset selection if current selection is not valid for type
    const currentOption = categorySelect.selectedOptions[0];
    if (currentOption && currentOption.dataset.type !== selectedType) {
        categorySelect.value = '';
    }
};

// Budget Management
const initBudgetForms = () => {
    const form = document.getElementById('addBudgetForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!validateForm(form)) return;

        const formData = new FormData(form);
        try {
            const response = await fetch('/api/budgets', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                window.location.reload();
            } else {
                const data = await response.json();
                showError(form.querySelector('#amount'), data.message || 'Failed to set budget');
            }
        } catch (error) {
            console.error('Error:', error);
        }
    });

    // Date validation
    const startDate = form.querySelector('input[name="start_date"]');
    const endDate = form.querySelector('input[name="end_date"]');
    
    if (startDate && endDate) {
        endDate.addEventListener('change', () => validateDateRange(startDate, endDate));
        startDate.addEventListener('change', () => validateDateRange(startDate, endDate));
    }
};

const validateDateRange = (startDate, endDate) => {
    const start = new Date(startDate.value);
    const end = new Date(endDate.value);
    
    if (start > end) {
        showError(endDate, 'End date must be after start date');
        return false;
    }
    clearError(endDate);
    return true;
};

// Chart Updates
const updateCharts = () => {
    // Update transaction chart if it exists
    const transactionChart = document.getElementById('transactionChart');
    if (transactionChart) {
        updateTransactionChart();
    }

    // Update budget chart if it exists
    const budgetChart = document.getElementById('budgetChart');
    if (budgetChart) {
        updateBudgetChart();
    }
};

const updateTransactionChart = async () => {
    try {
        const response = await fetch('/api/transactions/chart-data');
        const data = await response.json();
        
        const chart = Chart.getChart('transactionChart');
        if (chart) {
            chart.data = data;
            chart.update();
        }
    } catch (error) {
        console.error('Error updating transaction chart:', error);
    }
};

const updateBudgetChart = async () => {
    try {
        const response = await fetch('/api/budgets/chart-data');
        const data = await response.json();
        
        const chart = Chart.getChart('budgetChart');
        if (chart) {
            chart.data = data;
            chart.update();
        }
    } catch (error) {
        console.error('Error updating budget chart:', error);
    }
};

// Account Management
const initAccountForms = () => {
    const form = document.getElementById('addAccountForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!validateForm(form)) return;

        const formData = new FormData(form);
        try {
            const response = await fetch('/api/accounts', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                window.location.reload();
            } else {
                const data = await response.json();
                showError(form.querySelector('#name'), data.message || 'Failed to add account');
            }
        } catch (error) {
            console.error('Error:', error);
        }
    });
};

// Search and Filter Functions
const initSearchFilters = () => {
    const searchInput = document.getElementById('searchTransactions');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(handleSearch, 300));
    }

    const filterSelects = document.querySelectorAll('.filter-select');
    filterSelects.forEach(select => {
        select.addEventListener('change', handleFilters);
    });
};

const debounce = (func, wait) => {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

const handleSearch = async (e) => {
    const searchTerm = e.target.value.trim();
    const tableBody = document.querySelector('.transaction-table tbody');
    
    if (!tableBody) return;

    try {
        const response = await fetch(`/api/transactions/search?term=${encodeURIComponent(searchTerm)}`);
        const data = await response.json();
        updateTransactionTable(data);
    } catch (error) {
        console.error('Error searching transactions:', error);
    }
};

const handleFilters = () => {
    const filters = {};
    document.querySelectorAll('.filter-select').forEach(select => {
        if (select.value) {
            filters[select.name] = select.value;
        }
    });

    applyFilters(filters);
};

const applyFilters = async (filters) => {
    try {
        const queryString = new URLSearchParams(filters).toString();
        const response = await fetch(`/api/transactions/filter?${queryString}`);
        const data = await response.json();
        updateTransactionTable(data);
    } catch (error) {
        console.error('Error applying filters:', error);
    }
};

const updateTransactionTable = (transactions) => {
    const tableBody = document.querySelector('.transaction-table tbody');
    if (!tableBody) return;

    tableBody.innerHTML = transactions.map(t => `
        <tr>
            <td>${formatDate(t.date)}</td>
            <td>${t.description}</td>
            <td>
                <span class="badge bg-light text-dark">${t.category.name}</span>
            </td>
            <td class="${t.type === 'income' ? 'text-success' : 'text-danger'}">
                ${t.type === 'income' ? '+' : '-'}${formatCurrency(t.amount)}
            </td>
            <td>${t.account.name}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary me-1" onclick="editTransaction(${t.id})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteTransaction(${t.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
};

// Export Functions
const exportToExcel = async () => {
    try {
        const response = await fetch('/api/transactions/export/excel');
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'transactions.xlsx';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Error exporting to Excel:', error);
    }
};

// Initialize everything when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

    // Initialize all forms
    initTransactionForm();
    initBudgetForms();
    initAccountForms();
    initSearchFilters();

    // Set up periodic updates
    setInterval(updateCharts, 60000); // Update charts every minute
});