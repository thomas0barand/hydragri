// Utils Module - Data loading and helper functions

const Utils = {
    
    // Load JSON data (metadata only for initial map)
    async loadData() {
        try {
            // Only load metadata initially (much smaller file)
            const metadata = await d3.json('data/points_metadata.json');
            
            console.log(`Loaded metadata for ${metadata.points.length} points`);
            
            return { fullData: null, metadata };
        } catch (error) {
            console.error('Error loading data:', error);
            throw error;
        }
    },
    
    // Load full data for a specific point (on-demand loading)
    async loadPointData(pointId) {
        try {
            // In a real production app, you would have individual point files
            // or a server endpoint that returns data for a specific point
            // For now, we load the full data file (but cache it)
            if (!window._cachedFullData) {
                console.log('Loading full dataset (this may take a moment)...');
                const fullData = await d3.json('data/gap_data.json');
                
                // Parse dates
                fullData.points.forEach(point => {
                    point.timeseries.forEach(d => {
                        d.date = new Date(d.date);
                    });
                });
                
                window._cachedFullData = fullData;
                console.log('Full dataset cached');
            }
            
            // Find and return the specific point
            const point = window._cachedFullData.points.find(p => p.id === pointId);
            return point;
        } catch (error) {
            console.error('Error loading point data:', error);
            throw error;
        }
    },
    
    // Parse date string
    parseDate(dateString) {
        return new Date(dateString);
    },
    
    // Format date for display
    formatDate(date) {
        return d3.timeFormat('%Y-%m-%d')(date);
    },
    
    // Format date for readable display
    formatDateReadable(date) {
        return d3.timeFormat('%b %d, %Y')(date);
    },
    
    // Get color scale for Gap values
    getColorScale(domain) {
        return d3.scaleSequential()
            .domain(domain)
            .interpolator(d3.interpolateRdYlBu)
            .clamp(true);
    },
    
    // Get size scale for RU values
    getSizeScale(domain, range = [5, 20]) {
        return d3.scaleSqrt()
            .domain(domain)
            .range(range);
    },
    
    // Filter data by year
    filterByYear(timeseries, year) {
        if (year === 'all') return timeseries;
        return timeseries.filter(d => d.date.getFullYear() === parseInt(year));
    },
    
    // Filter data by season
    filterBySeason(timeseries, season) {
        if (season === 'all') return timeseries;
        
        const seasonMonths = {
            'winter': [11, 0, 1], // Dec, Jan, Feb
            'spring': [2, 3, 4],   // Mar, Apr, May
            'summer': [5, 6, 7],   // Jun, Jul, Aug
            'fall': [8, 9, 10]     // Sep, Oct, Nov
        };
        
        const months = seasonMonths[season];
        return timeseries.filter(d => months.includes(d.date.getMonth()));
    },
    
    // Aggregate data by month
    aggregateByMonth(timeseries) {
        const grouped = d3.group(timeseries, d => 
            d3.timeFormat('%Y-%m')(d.date)
        );
        
        return Array.from(grouped, ([key, values]) => {
            const date = new Date(key + '-01');
            return {
                date: date,
                P: d3.sum(values, v => v.P),
                ETP: d3.sum(values, v => v.ETP),
                Stock: d3.mean(values, v => v.Stock),
                Gap: d3.sum(values, v => v.Gap)
            };
        });
    },
    
    // Calculate summary statistics
    calculateStats(timeseries) {
        const gaps = timeseries.filter(d => d.Gap > 0);
        
        return {
            totalP: d3.sum(timeseries, d => d.P),
            totalETP: d3.sum(timeseries, d => d.ETP),
            totalGap: d3.sum(timeseries, d => d.Gap),
            daysWithGap: gaps.length,
            maxGap: d3.max(timeseries, d => d.Gap) || 0,
            minStock: d3.min(timeseries, d => d.Stock),
            meanStock: d3.mean(timeseries, d => d.Stock)
        };
    },
    
    // Format number with fixed decimals
    formatNumber(num, decimals = 2) {
        return num.toFixed(decimals);
    },
    
    // Get Lambert II coordinates (for mapping)
    getLambertCoordinates(lambx, lamby) {
        // SAFRAN coordinates are in hectometers, convert to meters
        return [lambx * 100, lamby * 100];
    },
    
    // Get point by ID
    getPointById(points, id) {
        return points.find(p => p.id === id);
    },
    
    // Debounce function for performance
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // Show tooltip
    showTooltip(content, event) {
        const tooltip = d3.select('#tooltip');
        tooltip
            .html(content)
            .classed('visible', true)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 10) + 'px');
    },
    
    // Hide tooltip
    hideTooltip() {
        d3.select('#tooltip').classed('visible', false);
    },
    
    // Get season name
    getSeasonName(month) {
        if ([11, 0, 1].includes(month)) return 'Winter';
        if ([2, 3, 4].includes(month)) return 'Spring';
        if ([5, 6, 7].includes(month)) return 'Summer';
        return 'Fall';
    },
    
    // Check if date is in summer (high water demand)
    isSummer(date) {
        const month = date.getMonth();
        return month >= 5 && month <= 7; // Jun, Jul, Aug
    },
    
    // Create point label
    createPointLabel(point) {
        return `Point (${point.lambx}, ${point.lamby})`;
    }
};

// Make Utils available globally
window.Utils = Utils;
