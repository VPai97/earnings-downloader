// Earnings Downloader Frontend

const API_BASE = '';

let currentDocuments = [];

// DOM Elements
const searchForm = document.getElementById('search-form');
const resultsSection = document.getElementById('results');
const resultsBody = document.getElementById('results-body');
const loadingEl = document.getElementById('loading');
const noResultsEl = document.getElementById('no-results');
const downloadAllBtn = document.getElementById('download-all-btn');
const downloadStatus = document.getElementById('download-status');
const statusMessage = document.getElementById('status-message');
const searchBtn = document.getElementById('search-btn');
const companyInput = document.getElementById('company');
const regionSelect = document.getElementById('region');
const suggestionsEl = document.getElementById('company-suggestions');

let suggestionItems = [];
let activeSuggestionIndex = -1;
let suggestRequestId = 0;

// Event Listeners
searchForm.addEventListener('submit', handleSearch);
downloadAllBtn.addEventListener('click', handleDownloadAll);
companyInput.addEventListener('input', handleCompanyInput);
companyInput.addEventListener('keydown', handleSuggestionKeys);
companyInput.addEventListener('blur', () => setTimeout(hideSuggestions, 150));
companyInput.addEventListener('focus', handleCompanyInput);
regionSelect.addEventListener('change', () => {
    if (companyInput.value.trim()) {
        handleCompanyInput();
    }
});

async function handleSearch(e) {
    e.preventDefault();

    const company = sanitizeCompanyInput(companyInput.value.trim());
    const region = document.getElementById('region').value;
    const count = document.getElementById('count').value;

    const typeCheckboxes = document.querySelectorAll('input[name="types"]:checked');
    const types = Array.from(typeCheckboxes).map(cb => cb.value).join(',');

    if (!company) {
        alert('Please enter a company name');
        return;
    }

    if (!types) {
        alert('Please select at least one document type');
        return;
    }

    // Show loading state
    resultsSection.classList.remove('hidden');
    loadingEl.classList.remove('hidden');
    noResultsEl.classList.add('hidden');
    resultsBody.innerHTML = '';
    downloadAllBtn.classList.add('hidden');
    downloadStatus.classList.add('hidden');
    searchBtn.disabled = true;
    searchBtn.textContent = 'Searching...';

    try {
        const params = new URLSearchParams({
            company,
            region,
            count,
            types
        });

        const response = await fetch(`${API_BASE}/api/documents?${params}`);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Search failed');
        }

        const documents = await response.json();
        currentDocuments = documents;

        displayResults(documents);

    } catch (error) {
        console.error('Search error:', error);
        noResultsEl.textContent = `Error: ${error.message}`;
        noResultsEl.classList.remove('hidden');
    } finally {
        loadingEl.classList.add('hidden');
        searchBtn.disabled = false;
        searchBtn.textContent = 'Search Documents';
    }
}

function displayResults(documents) {
    resultsBody.innerHTML = '';

    if (documents.length === 0) {
        noResultsEl.textContent = 'No documents found for this company.';
        noResultsEl.classList.remove('hidden');
        downloadAllBtn.classList.add('hidden');
        return;
    }

    noResultsEl.classList.add('hidden');

    documents.forEach(doc => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${escapeHtml(doc.company.substring(0, 30))}</td>
            <td>${escapeHtml(doc.quarter)} ${escapeHtml(doc.year)}</td>
            <td>${formatDocType(doc.doc_type)}</td>
            <td>${escapeHtml(doc.source)}</td>
            <td>
                <a href="${escapeHtml(doc.url)}" target="_blank" class="btn-download" style="display:inline-block;text-decoration:none;color:white;">
                    Download
                </a>
            </td>
        `;
        resultsBody.appendChild(row);
    });

    downloadAllBtn.classList.remove('hidden');
    downloadAllBtn.textContent = `Download All (${documents.length} files)`;
}

async function handleDownloadAll() {
    if (currentDocuments.length === 0) return;

    const company = sanitizeCompanyInput(companyInput.value.trim());
    const region = document.getElementById('region').value;

    const typeCheckboxes = document.querySelectorAll('input[name="types"]:checked');
    const types = Array.from(typeCheckboxes).map(cb => cb.value);

    downloadAllBtn.disabled = true;
    downloadAllBtn.textContent = 'Preparing ZIP...';
    downloadStatus.classList.remove('hidden');
    statusMessage.textContent = 'Fetching documents and creating ZIP file...';

    try {
        const response = await fetch(`${API_BASE}/api/downloads/zip`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                company,
                region,
                count: parseInt(document.getElementById('count').value),
                include_transcripts: types.includes('transcript'),
                include_presentations: types.includes('presentation'),
                include_press_releases: types.includes('press_release')
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            let errorMessage = 'Download failed';
            try {
                const errorJson = JSON.parse(errorText);
                errorMessage = errorJson.detail || errorMessage;
            } catch (e) {
                errorMessage = errorText || errorMessage;
            }
            throw new Error(errorMessage);
        }

        // Get the blob and trigger download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;

        // Get filename from Content-Disposition header or use default
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `${company.replace(/[^a-zA-Z0-9]/g, '_')}_earnings.zip`;
        if (contentDisposition) {
            const match = contentDisposition.match(/filename=(.+)/);
            if (match) {
                filename = match[1].replace(/"/g, '');
            }
        }

        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();

        statusMessage.textContent = `Downloaded ${currentDocuments.length} documents as ZIP!`;

    } catch (error) {
        console.error('Download error:', error);
        statusMessage.textContent = `Error: ${error.message}`;
    } finally {
        downloadAllBtn.disabled = false;
        downloadAllBtn.textContent = `Download All (${currentDocuments.length} files)`;
    }
}

function formatDocType(docType) {
    const labels = {
        'transcript': 'Transcript',
        'presentation': 'Presentation',
        'press_release': 'Press Release'
    };
    return labels[docType] || docType;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function sanitizeCompanyInput(value) {
    if (!value) return value;
    const parts = value.split(',');
    const cleaned = parts.map(part => {
        const trimmed = part.trim();
        return trimmed.replace(/\s*\(([A-Z0-9&.\-]{1,15})\)\s*$/i, '').trim();
    }).filter(Boolean);
    return cleaned.join(', ');
}

function debounce(fn, delay) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}

const debouncedSuggest = debounce(fetchSuggestions, 250);

function handleCompanyInput() {
    debouncedSuggest();
}

function getCurrentToken(value) {
    const parts = value.split(',');
    return parts[parts.length - 1].trim();
}

function replaceCurrentToken(value, replacement) {
    const parts = value.split(',');
    if (parts.length === 1) {
        return replacement;
    }
    const prefix = parts.slice(0, -1).map(part => part.trim()).filter(Boolean).join(', ');
    if (!prefix) {
        return replacement;
    }
    return `${prefix}, ${replacement}`;
}

async function fetchSuggestions() {
    const query = getCurrentToken(companyInput.value);
    if (!query) {
        hideSuggestions();
        return;
    }

    const requestId = ++suggestRequestId;
    const params = new URLSearchParams({
        q: query,
        region: regionSelect.value || 'india',
        limit: '20'
    });

    try {
        const response = await fetch(`${API_BASE}/api/companies/suggest?${params}`);
        if (!response.ok) {
            hideSuggestions();
            return;
        }
        const suggestions = await response.json();
        if (requestId !== suggestRequestId) return;
        renderSuggestions(suggestions);
    } catch (error) {
        console.error('Suggestion error:', error);
        hideSuggestions();
    }
}

function renderSuggestions(suggestions) {
    suggestionsEl.innerHTML = '';
    suggestionItems = Array.isArray(suggestions) ? suggestions : [];
    activeSuggestionIndex = -1;

    if (suggestionItems.length === 0) {
        hideSuggestions();
        return;
    }

    suggestionItems.forEach((item, index) => {
        const option = document.createElement('div');
        option.className = 'autocomplete-item';
        option.setAttribute('role', 'option');
        option.textContent = item.label || item.name || '';
        option.addEventListener('mousedown', (event) => {
            event.preventDefault();
            selectSuggestion(index);
        });
        suggestionsEl.appendChild(option);
    });

    suggestionsEl.classList.remove('hidden');
    companyInput.setAttribute('aria-expanded', 'true');
}

function hideSuggestions() {
    suggestionsEl.classList.add('hidden');
    suggestionsEl.innerHTML = '';
    suggestionItems = [];
    activeSuggestionIndex = -1;
    companyInput.setAttribute('aria-expanded', 'false');
}

function handleSuggestionKeys(event) {
    if (suggestionsEl.classList.contains('hidden')) {
        return;
    }

    if (event.key === 'ArrowDown') {
        event.preventDefault();
        moveActiveSuggestion(1);
    } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        moveActiveSuggestion(-1);
    } else if (event.key === 'Enter') {
        if (activeSuggestionIndex >= 0) {
            event.preventDefault();
            selectSuggestion(activeSuggestionIndex);
        }
    } else if (event.key === 'Escape') {
        hideSuggestions();
    }
}

function moveActiveSuggestion(delta) {
    const items = suggestionsEl.querySelectorAll('.autocomplete-item');
    if (!items.length) return;

    activeSuggestionIndex = (activeSuggestionIndex + delta + items.length) % items.length;
    items.forEach((item, index) => {
        item.classList.toggle('active', index === activeSuggestionIndex);
    });
}

function selectSuggestion(index) {
    const selected = suggestionItems[index];
    if (!selected) return;
    const name = selected.name || selected.label || '';
    if (!name) return;
    companyInput.value = replaceCurrentToken(companyInput.value, name);
    hideSuggestions();
    companyInput.focus();
}

// Load available regions on page load
async function loadRegions() {
    try {
        const response = await fetch(`${API_BASE}/api/companies/regions`);
        if (response.ok) {
            const regions = await response.json();
            const regionSelect = document.getElementById('region');

            // Update options based on available regions
            regionSelect.innerHTML = '';
            regions.forEach(region => {
                const option = document.createElement('option');
                option.value = region.id;
                option.textContent = `${region.name} (${region.fiscal_year} FY)`;
                regionSelect.appendChild(option);
            });

            // If no regions, show default
            if (regions.length === 0) {
                regionSelect.innerHTML = '<option value="india">India</option>';
            }
        }
    } catch (error) {
        console.log('Could not load regions, using defaults');
    }
}

// Initialize
loadRegions();
