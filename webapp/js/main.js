// Main Application Module

const App = {
    data: null,
    metadata: null,
    currentFilters: {
        year: 'all',
        season: 'all',
        selectedPoint: null
    },
    
    // Initialize the application
    async init() {
        console.log('Initializing Hydric Gap Visualization...');
        
        try {
            // Load data
            await this.loadData();
            
            // Initialize visualizations
            this.initVisualizations();
            
            // Set up controls
            this.setupControls();
            
            // Set up window resize handler
            this.setupResizeHandler();
            
            console.log('Application initialized successfully');
        } catch (error) {
            console.error('Error initializing application:', error);
            this.showError('Failed to load data. Please refresh the page.');
        }
    },
    
    // Load data
    async loadData() {
        console.log('Loading data...');
        const { fullData, metadata } = await Utils.loadData();
        this.data = fullData;  // Will be null initially
        this.metadata = metadata;
        console.log(`Loaded metadata for ${this.metadata.points.length} points`);
    },
    
    // Initialize visualizations
    initVisualizations() {
        console.log('Initializing visualizations...');
        
        // Initialize map with metadata
        MapViz.init('map-container', this.metadata.points, (point) => {
            this.onPointSelected(point);
        });
        
        // Initialize time series (but keep it hidden initially)
        TimeSeriesViz.init('timeseries-container');
        
        // Don't select any point by default - let user click on map
        console.log('Map ready. Click on a point to view time series.');
    },
    
    // Populate point selector (removed - not needed in new design)
    populatePointSelector() {
        // Point selection is now done by clicking on map
        // No dropdown selector needed
    },
    
    // Set up controls
    setupControls() {
        const self = this;
        
        // Metric selector (for map visualization)
        d3.select('#metric-selector').on('change', function() {
            MapViz.updateMetric(this.value);
        });
        
        // Year selector
        d3.select('#year-selector').on('change', function() {
            self.currentFilters.year = this.value;
            self.updateVisualization();
        });
        
        // Season selector
        d3.select('#season-selector').on('change', function() {
            self.currentFilters.season = this.value;
            self.updateVisualization();
        });
        
        // Close time series button
        d3.select('#close-timeseries').on('click', () => {
            this.hideTimeSeries();
        });
        
        // Series toggle checkboxes
        d3.select('#toggle-p').on('change', function() {
            TimeSeriesViz.toggleSeries('P', this.checked);
        });
        
        d3.select('#toggle-etp').on('change', function() {
            TimeSeriesViz.toggleSeries('ETP', this.checked);
        });
        
        d3.select('#toggle-stock').on('change', function() {
            TimeSeriesViz.toggleSeries('Stock', this.checked);
        });
        
        d3.select('#toggle-gap').on('change', function() {
            TimeSeriesViz.toggleSeries('Gap', this.checked);
        });
    },
    
    // Set up resize handler
    setupResizeHandler() {
        const debouncedResize = Utils.debounce(() => {
            MapViz.resize();
            TimeSeriesViz.resize();
        }, 250);
        
        window.addEventListener('resize', debouncedResize);
    },
    
    // Select a point
    async selectPoint(pointId) {
        try {
            // Show loading state
            d3.select('#timeseries-container .loading').style('display', 'flex');
            d3.select('#stats-content').html('<p>Loading data...</p>');
            
            // Load point data on-demand
            const point = await Utils.loadPointData(pointId);
            if (!point) {
                console.error('Point not found:', pointId);
                return;
            }
            
            this.currentFilters.selectedPoint = point;
            
            // Update map selection
            const metadataPoint = this.metadata.points.find(p => p.id === pointId);
            if (metadataPoint) {
                MapViz.selectPoint(metadataPoint);
            }
            
            // Hide loading state
            d3.select('#timeseries-container .loading').style('display', 'none');
            
            // Update visualization
            this.updateVisualization();
            
            // Update statistics
            this.updateStatistics(point);
        } catch (error) {
            console.error('Error selecting point:', error);
            d3.select('#timeseries-container').html('<div class="loading" style="color: red;">Error loading data</div>');
        }
    },
    
    // Point selected from map
    onPointSelected(metadataPoint) {
        // Just show the panel and load the point data
        this.showTimeSeries();
        this.selectPoint(metadataPoint.id);  // Use the metadata point's id directly
    },
    
    // Show time series panel
    showTimeSeries() {
        const timeseriesSection = d3.select('#timeseries-section');
        const closeButton = d3.select('#close-timeseries');
        
        timeseriesSection.style('display', 'flex');
        closeButton.style('display', 'inline-block');
        
        // Initialize time series if not already done
        if (!TimeSeriesViz.svg) {
            TimeSeriesViz.init('timeseries-container');
        }
    },
    
    // Hide time series panel
    hideTimeSeries() {
        const timeseriesSection = d3.select('#timeseries-section');
        const closeButton = d3.select('#close-timeseries');
        
        timeseriesSection.style('display', 'none');
        closeButton.style('display', 'none');
        
        // Clear map selection
        MapViz.clearSelection();
        this.currentFilters.selectedPoint = null;
    },
    
    // Update visualization with current filters
    updateVisualization() {
        if (!this.currentFilters.selectedPoint) return;
        
        const point = this.currentFilters.selectedPoint;
        let timeseries = [...point.timeseries];
        
        // Apply year filter
        if (this.currentFilters.year !== 'all') {
            timeseries = Utils.filterByYear(timeseries, this.currentFilters.year);
        }
        
        // Apply season filter
        if (this.currentFilters.season !== 'all') {
            timeseries = Utils.filterBySeason(timeseries, this.currentFilters.season);
        }
        
        // Update time series
        TimeSeriesViz.update(point, timeseries);
        
        // Update statistics with filtered data
        this.updateStatistics(point, timeseries);
    },
    
    // Update statistics panel
    updateStatistics(point, timeseries = null) {
        const data = timeseries || point.timeseries;
        const stats = Utils.calculateStats(data);
        
        const statsHtml = `
            <div class="stat-card">
                <div class="stat-label">Total Precipitation</div>
                <div class="stat-value">${Utils.formatNumber(stats.totalP, 1)} <span class="stat-unit">mm</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total ETP</div>
                <div class="stat-value">${Utils.formatNumber(stats.totalETP, 1)} <span class="stat-unit">mm</span></div>
            </div>
            <div class="stat-card" style="border-left-color: #d73027;">
                <div class="stat-label">Total Gap (Deficit)</div>
                <div class="stat-value">${Utils.formatNumber(stats.totalGap, 1)} <span class="stat-unit">mm</span></div>
            </div>
            <div class="stat-card" style="border-left-color: #d73027;">
                <div class="stat-label">Days with Deficit</div>
                <div class="stat-value">${stats.daysWithGap} <span class="stat-unit">days</span></div>
            </div>
            <div class="stat-card" style="border-left-color: #d73027;">
                <div class="stat-label">Max Daily Gap</div>
                <div class="stat-value">${Utils.formatNumber(stats.maxGap, 2)} <span class="stat-unit">mm</span></div>
            </div>
            <div class="stat-card" style="border-left-color: #4575b4;">
                <div class="stat-label">Min Stock</div>
                <div class="stat-value">${Utils.formatNumber(stats.minStock, 2)} <span class="stat-unit">mm</span></div>
            </div>
            <div class="stat-card" style="border-left-color: #4575b4;">
                <div class="stat-label">Mean Stock</div>
                <div class="stat-value">${Utils.formatNumber(stats.meanStock, 2)} <span class="stat-unit">mm</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Soil Reserve (RU)</div>
                <div class="stat-value">${Utils.formatNumber(point.ru_max, 0)} <span class="stat-unit">mm</span></div>
            </div>
        `;
        
        d3.select('#stats-content').html(statsHtml);
    },
    
    // Clear statistics
    clearStats() {
        d3.select('#stats-content').html('<p>Select a point to view statistics</p>');
    },
    
    // Reset all filters
    resetFilters() {
        this.currentFilters = {
            year: 'all',
            season: 'all',
            selectedPoint: this.currentFilters.selectedPoint
        };
        
        // Reset selectors
        d3.select('#year-selector').property('value', 'all');
        d3.select('#season-selector').property('value', 'all');
        
        // Reset toggles
        d3.select('#toggle-p').property('checked', true);
        d3.select('#toggle-etp').property('checked', true);
        d3.select('#toggle-stock').property('checked', true);
        d3.select('#toggle-gap').property('checked', true);
        
        // Reset series visibility
        TimeSeriesViz.visibleSeries = {
            P: true,
            ETP: true,
            Stock: true,
            Gap: true
        };
        
        // Update visualization
        this.updateVisualization();
    },
    
    // Show error message
    showError(message) {
        const container = d3.select('.main-content .container');
        container.insert('div', ':first-child')
            .attr('class', 'error-message')
            .style('background', '#f8d7da')
            .style('color', '#721c24')
            .style('padding', '15px')
            .style('border-radius', '4px')
            .style('margin-bottom', '20px')
            .html(`<strong>Error:</strong> ${message}`);
    }
};

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

// Make App available globally for debugging
window.App = App;
