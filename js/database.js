class DatabaseLoader {
    constructor() {
        this.database = null;
        this.isLoaded = false;
        this.isLoading = false;
    }

    async loadDatabase() {
        if (this.isLoaded) return this.database;
        if (this.isLoading) return this.waitForLoad();
        
        this.isLoading = true;
        
        try {
            console.log('📥 Loading AnimeTosho database...');
            const startTime = performance.now();
            
            // Add cache busting for updates
            const timestamp = Math.floor(Date.now() / (1000 * 60 * 60)); // Update hourly
            const response = await fetch(`data/optimized_db.json.gz?v=${timestamp}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const compressed = await response.arrayBuffer();
            console.log(`📦 Downloaded ${(compressed.byteLength / 1024 / 1024).toFixed(1)} MB`);
            
            const decompressed = pako.ungzip(compressed, { to: 'string' });
            this.database = JSON.parse(decompressed);
            
            const loadTime = performance.now() - startTime;
            console.log(`✅ Database loaded in ${(loadTime / 1000).toFixed(2)}s`);
            console.log(`📊 ${Object.keys(this.database.torrents).length.toLocaleString()} torrents with subtitles`);
            
            this.isLoaded = true;
            this.isLoading = false;
            
            return this.database;
            
        } catch (error) {
            this.isLoading = false;
            console.error('❌ Database load failed:', error);
            throw error;
        }
    }

    async waitForLoad() {
        while (this.isLoading) {
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        return this.database;
    }

    getStats() {
        if (!this.isLoaded) return null;
        return this.database.stats;
    }

    getLanguages() {
        if (!this.isLoaded) return [];
        return Object.keys(this.database.languages).sort();
    }
}

// Global instance
window.dbLoader = new DatabaseLoader();
