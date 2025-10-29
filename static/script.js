/**
 * SQL-Agent Frontend JavaScript
 * Handles user interactions and API communication
 */

// DOM Elements
const nlInput = document.getElementById('nl-input');
const submitBtn = document.getElementById('submit-btn');
const clearBtn = document.getElementById('clear-btn');
const loading = document.getElementById('loading');
const errorBox = document.getElementById('error-msg');
const errorText = document.getElementById('error-text');
const sqlSection = document.getElementById('sql-section');
const sqlDisplay = document.getElementById('sql-display');
const copySqlBtn = document.getElementById('copy-sql-btn');
const resultsSection = document.getElementById('results-section');
const resultsContainer = document.getElementById('results-container');
const rowCount = document.getElementById('row-count');
const exportCsvBtn = document.getElementById('export-csv-btn');
const exampleButtons = document.querySelectorAll('.example-btn');

// State
let currentResults = null;

/**
 * Initialize event listeners
 */
function init() {
    submitBtn.addEventListener('click', handleSubmit);
    clearBtn.addEventListener('click', handleClear);
    copySqlBtn.addEventListener('click', handleCopySQL);
    exportCsvBtn.addEventListener('click', handleExportCSV);

    // Example query buttons
    exampleButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            nlInput.value = btn.dataset.query;
            nlInput.focus();
        });
    });

    // Submit on Ctrl+Enter
    nlInput.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
            handleSubmit();
        }
    });
}

/**
 * Handle query submission
 */
async function handleSubmit() {
    const query = nlInput.value.trim();

    if (!query) {
        showError('請輸入查詢內容');
        return;
    }

    // Reset UI
    hideError();
    hideResults();
    showLoading();

    try {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ nl_query: query })
        });

        hideLoading();

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '查詢失敗');
        }

        const result = await response.json();
        currentResults = result;

        displaySQL(result.query_generated);
        displayResults(result.columns, result.data, result.row_count);

    } catch (error) {
        hideLoading();
        showError(error.message);
        console.error('Query error:', error);
    }
}

/**
 * Handle clear button
 */
function handleClear() {
    nlInput.value = '';
    hideError();
    hideResults();
    currentResults = null;
    nlInput.focus();
}

/**
 * Handle copy SQL button
 */
async function handleCopySQL() {
    const sql = sqlDisplay.textContent;

    try {
        await navigator.clipboard.writeText(sql);

        // Visual feedback
        const originalText = copySqlBtn.textContent;
        copySqlBtn.textContent = '✅ 已複製';
        copySqlBtn.style.background = 'rgba(16, 185, 129, 0.2)';

        setTimeout(() => {
            copySqlBtn.textContent = originalText;
            copySqlBtn.style.background = '';
        }, 2000);
    } catch (error) {
        console.error('Copy failed:', error);
        alert('複製失敗，請手動複製');
    }
}

/**
 * Handle export to CSV
 */
function handleExportCSV() {
    if (!currentResults || !currentResults.data.length) {
        alert('沒有資料可以匯出');
        return;
    }

    const { columns, data } = currentResults;

    // Build CSV content
    let csvContent = '';

    // Add headers
    csvContent += columns.map(col => `"${col}"`).join(',') + '\n';

    // Add data rows
    data.forEach(row => {
        const csvRow = row.map(cell => {
            // Handle null/undefined
            if (cell === null || cell === undefined) {
                return '""';
            }
            // Escape quotes and wrap in quotes
            const cellStr = String(cell).replace(/"/g, '""');
            return `"${cellStr}"`;
        }).join(',');
        csvContent += csvRow + '\n';
    });

    // Create blob and download
    const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', `query_results_${Date.now()}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Display SQL query
 */
function displaySQL(sql) {
    sqlDisplay.textContent = sql;
    sqlSection.style.display = 'block';
}

/**
 * Display query results in table
 */
function displayResults(columns, data, count) {
    // Clear previous results
    resultsContainer.innerHTML = '';

    // Update row count badge
    rowCount.textContent = `${count} 筆資料`;

    if (!data || data.length === 0) {
        resultsContainer.innerHTML = '<p class="text-center" style="padding: 2rem; color: var(--text-secondary);">查無資料</p>';
        resultsSection.style.display = 'block';
        return;
    }

    // Create table
    const table = document.createElement('table');

    // Create header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    columns.forEach(colName => {
        const th = document.createElement('th');
        th.textContent = colName;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Create body
    const tbody = document.createElement('tbody');
    data.forEach(rowData => {
        const row = document.createElement('tr');
        rowData.forEach(cellData => {
            const cell = document.createElement('td');
            // Handle null/undefined
            if (cellData === null || cellData === undefined) {
                cell.textContent = 'NULL';
                cell.style.color = 'var(--text-secondary)';
                cell.style.fontStyle = 'italic';
            } else {
                cell.textContent = cellData;
            }
            row.appendChild(cell);
        });
        tbody.appendChild(row);
    });
    table.appendChild(tbody);

    resultsContainer.appendChild(table);
    resultsSection.style.display = 'block';

    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Show loading indicator
 */
function showLoading() {
    loading.style.display = 'block';
}

/**
 * Hide loading indicator
 */
function hideLoading() {
    loading.style.display = 'none';
}

/**
 * Show error message
 */
function showError(message) {
    errorText.textContent = message;
    errorBox.style.display = 'flex';
    errorBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Hide error message
 */
function hideError() {
    errorBox.style.display = 'none';
    errorText.textContent = '';
}

/**
 * Hide all results
 */
function hideResults() {
    sqlSection.style.display = 'none';
    resultsSection.style.display = 'none';
}

/**
 * Check API health on load
 */
async function checkHealth() {
    try {
        const response = await fetch('/health');
        const health = await response.json();

        if (health.status !== 'healthy') {
            console.warn('API health check:', health);
        }
    } catch (error) {
        console.error('Health check failed:', error);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    init();
    checkHealth();
});
