class App {
    constructor() {
        this.searcher = null;
        this.initializeElements();
        this.bindEvents();
        this.loadDatabase();
    }

    initializeElements() {
        this.searchInput = document.getElementById('searchInput');
        this.languageFilter = document.getElementById('languageFilter');
        this.searchBtn = document.getElementById('searchBtn');
        this.loadingStatus = document.getElementById('loadingStatus');
        this.searchResults = document.getElementById('searchResults');
        this.stats = document.getElementById('stats');
    }

    bindEvents() {
        this.searchBtn.addEventListener('click', () => this.performSearch());
        this.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });
        this.searchInput.addEventListener('input', () => this.debounceSearch());
    }

    async loadDatabase() {
        try {
            this.loadingStatus.style.display = 'block';
            
            const database = await window.dbLoader.loadDatabase();
            this.searcher = new AnimeSearch(database);
            
            // Populate language filter
            const languages = window.dbLoader.getLanguages();
            languages.forEach(lang => {
                const option = document.createElement('option');
                option.value = lang;
                option.textContent = `${lang.toUpperCase()} (${database.languages[lang].length.toLocaleString()})`;
                this.languageFilter.appendChild(option);
            });

            // Show stats
            const stats = window.dbLoader.getStats();
            this.stats.innerHTML = `
                <div class="stat-item">📺 ${stats.torrent_count.toLocaleString()} torrents</div>
                <div class="stat-item">🌐 ${stats.language_count} languages</div>
                <div class="stat-item">📅 Updated: ${stats.last_updated}</div>
            `;

            this.loadingStatus.style.display = 'none';
            this.searchInput.disabled = false;
            this.searchInput.focus();
            
        } catch (error) {
            this.loadingStatus.innerHTML = `❌ Failed to load database: ${error.message}`;
            this.loadingStatus.className = 'loading error';
        }
    }

    debounceSearch() {
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => this.performSearch(), 300);
    }

    performSearch() {
        if (!this.searcher) return;

        const query = this.searchInput.value.trim();
        const language = this.languageFilter.value;

        if (!query) {
            this.searchResults.innerHTML = '';
            return;
        }

        const results = this.searcher.search(query, language, 100);
        this.displayResults(results);
    }

    displayResults(results) {
        if (results.results.length === 0) {
            this.searchResults.innerHTML = `
                <div class="no-results">
                    <h3>No results found</h3>
                    <p>Try different keywords or check spelling</p>
                </div>
            `;
            return;
        }

        const html = `
            <div class="results-header">
                <h3>Found ${results.total} results in ${results.search_time_ms.toFixed(1)}ms</h3>
            </div>
            <div class="results-list">
                ${results.results.map(result => this.renderResult(result)).join('')}
            </div>
        `;

        this.searchResults.innerHTML = html;
    }

    renderResult(result) {
        const badges = [
            result.episode ? `<span class="badge episode">EP ${result.episode}</span>` : '',
            result.quality ? `<span class="badge quality">${result.quality}</span>` : '',
            result.group ? `<span class="badge group">${result.group}</span>` : ''
        ].filter(Boolean).join('');

        const languages = result.languages.map(lang => 
            `<span class="lang-tag">${lang.toUpperCase()}</span>`
        ).join('');

        const downloads = result.download_urls.slice(0, 3).map(dl => 
            `<a href="${dl.url}" class="download-btn" target="_blank" title="${dl.filename}">
                📥 ${dl.language.toUpperCase()}
            </a>`
        ).join('');

        return `
            <div class="result-item">
                <div class="result-header">
                    <h4 class="result-title">${this.escapeHtml(result.name)}</h4>
                    <div class="result-badges">${badges}</div>
                </div>
                <div class="result-meta">
                    <div class="languages">${languages}</div>
                    <div class="file-count">${result.subtitle_files} subtitle files</div>
                </div>
                <div class="result-downloads">${downloads}</div>
            </div>
        `;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new App();
});

