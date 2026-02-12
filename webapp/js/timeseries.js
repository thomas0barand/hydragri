// Time Series Visualization Module

const TimeSeriesViz = {
    svg: null,
    width: 0,
    height: 0,
    margin: { top: 20, right: 30, bottom: 60, left: 60 },
    chartWidth: 0,
    chartHeight: 0,
    xScale: null,
    yScale: null,
    currentData: null,
    currentPoint: null,
    visibleSeries: {
        P: true,
        ETP: true,
        Stock: true,
        Gap: true
    },
    
    // Initialize the time series chart
    init(containerId) {
        const container = d3.select(`#${containerId}`);
        container.selectAll('*').remove();
        
        // Get container dimensions
        const containerNode = container.node();
        this.width = containerNode.clientWidth;
        this.height = containerNode.clientHeight;
        
        // Calculate chart dimensions
        this.chartWidth = this.width - this.margin.left - this.margin.right;
        this.chartHeight = this.height - this.margin.top - this.margin.bottom;
        
        // Create SVG
        this.svg = container.append('svg')
            .attr('width', this.width)
            .attr('height', this.height);
        
        // Create main group
        this.chartGroup = this.svg.append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);
        
        // Show placeholder message
        this.showPlaceholder();
    },
    
    // Show placeholder message
    showPlaceholder() {
        if (this.chartGroup) {
            this.chartGroup.append('text')
                .attr('class', 'placeholder-text')
                .attr('x', this.chartWidth / 2)
                .attr('y', this.chartHeight / 2)
                .attr('text-anchor', 'middle')
                .attr('font-size', '16px')
                .attr('fill', '#999')
                .text('Select a point on the map to view time series');
        }
    },
    
    // Update with new data
    update(point, timeseries) {
        this.currentPoint = point;
        this.currentData = timeseries;
        
        // Clear existing chart
        this.chartGroup.selectAll('*').remove();
        
        if (!timeseries || timeseries.length === 0) {
            this.showPlaceholder();
            return;
        }
        
        // Set up scales
        this.xScale = d3.scaleTime()
            .domain(d3.extent(timeseries, d => d.date))
            .range([0, this.chartWidth]);
        
        // Y scale for all values
        const maxValue = d3.max(timeseries, d => 
            Math.max(d.P, d.ETP, d.Stock, d.Gap)
        );
        
        this.yScale = d3.scaleLinear()
            .domain([0, maxValue * 1.1])
            .range([this.chartHeight, 0])
            .nice();
        
        // Draw axes
        this.drawAxes();
        
        // Draw grid
        this.drawGrid();
        
        // Draw summer highlight bands
        this.drawSeasonalHighlights(timeseries);
        
        // Draw areas and lines
        if (this.visibleSeries.Gap) this.drawGapArea(timeseries);
        if (this.visibleSeries.P) this.drawPrecipitationBars(timeseries);
        if (this.visibleSeries.Stock) this.drawLine(timeseries, 'Stock', '#4575b4', 2.5);
        if (this.visibleSeries.ETP) this.drawLine(timeseries, 'ETP', '#fc8d59', 2);
        
        // Add interaction overlay
        this.addInteractionOverlay(timeseries);
        
        // Update info
        this.updatePointInfo(point);
    },
    
    // Draw axes
    drawAxes() {
        // X axis
        const xAxis = d3.axisBottom(this.xScale)
            .ticks(d3.timeMonth.every(2))
            .tickFormat(d3.timeFormat('%b %Y'));
        
        this.chartGroup.append('g')
            .attr('class', 'x-axis')
            .attr('transform', `translate(0,${this.chartHeight})`)
            .call(xAxis)
            .selectAll('text')
            .attr('transform', 'rotate(-45)')
            .style('text-anchor', 'end');
        
        // Y axis
        const yAxis = d3.axisLeft(this.yScale)
            .ticks(8)
            .tickFormat(d => d + ' mm');
        
        this.chartGroup.append('g')
            .attr('class', 'y-axis')
            .call(yAxis);
        
        // Y axis label
        this.chartGroup.append('text')
            .attr('transform', 'rotate(-90)')
            .attr('y', -this.margin.left + 15)
            .attr('x', -this.chartHeight / 2)
            .attr('text-anchor', 'middle')
            .attr('font-size', '12px')
            .attr('fill', '#666')
            .text('Water Balance (mm)');
    },
    
    // Draw grid
    drawGrid() {
        // Horizontal grid lines
        this.chartGroup.append('g')
            .attr('class', 'grid')
            .call(d3.axisLeft(this.yScale)
                .ticks(8)
                .tickSize(-this.chartWidth)
                .tickFormat('')
            );
    },
    
    // Draw seasonal highlights (summer) and gaps for excluded data
    drawSeasonalHighlights(timeseries) {
        // Only draw summer highlights if no season filter is active
        const currentSeason = window.App?.currentFilters?.season || 'all';
        
        if (currentSeason === 'all') {
            // Draw summer highlights
            const years = [...new Set(timeseries.map(d => d.date.getFullYear()))];
            
            years.forEach(year => {
                const summerStart = new Date(year, 5, 1); // June 1
                const summerEnd = new Date(year, 7, 31);   // August 31
                
                if (summerStart >= this.xScale.domain()[0] && 
                    summerEnd <= this.xScale.domain()[1]) {
                    
                    this.chartGroup.append('rect')
                        .attr('x', this.xScale(summerStart))
                        .attr('y', 0)
                        .attr('width', this.xScale(summerEnd) - this.xScale(summerStart))
                        .attr('height', this.chartHeight)
                        .attr('fill', '#fff3cd')
                        .attr('opacity', 0.2)
                        .attr('pointer-events', 'none');
                    
                    // Add summer label
                    this.chartGroup.append('text')
                        .attr('x', (this.xScale(summerStart) + this.xScale(summerEnd)) / 2)
                        .attr('y', 15)
                        .attr('text-anchor', 'middle')
                        .attr('font-size', '10px')
                        .attr('fill', '#856404')
                        .attr('opacity', 0.5)
                        .text('Summer');
                }
            });
        } else {
            // Draw gaps for excluded data when season filter is active
            this.drawExcludedDataGaps(timeseries, currentSeason);
        }
    },
    
    // Draw hatched rectangles for excluded data periods
    drawExcludedDataGaps(timeseries, selectedSeason) {
        if (!timeseries || timeseries.length === 0) return;
        
        // Get full date range
        const fullStart = this.xScale.domain()[0];
        const fullEnd = this.xScale.domain()[1];
        
        // Create pattern for hatching
        const defs = this.svg.select('defs').empty() 
            ? this.svg.append('defs') 
            : this.svg.select('defs');
        
        // Remove existing pattern
        defs.selectAll('#diagonal-hatch').remove();
        
        const pattern = defs.append('pattern')
            .attr('id', 'diagonal-hatch')
            .attr('patternUnits', 'userSpaceOnUse')
            .attr('width', 8)
            .attr('height', 8);
        
        pattern.append('path')
            .attr('d', 'M-1,1 l2,-2 M0,8 l8,-8 M7,9 l2,-2')
            .attr('stroke', '#999')
            .attr('stroke-width', 1)
            .attr('opacity', 0.3);
        
        // Define season months
        const seasonMonths = {
            'winter': [11, 0, 1], // Dec, Jan, Feb
            'spring': [2, 3, 4],   // Mar, Apr, May
            'summer': [5, 6, 7],   // Jun, Jul, Aug
            'fall': [8, 9, 10]     // Sep, Oct, Nov
        };
        
        const includedMonths = seasonMonths[selectedSeason];
        
        // Find gaps (excluded periods)
        const gaps = [];
        let currentGapStart = null;
        
        // Generate all days in range
        let current = new Date(fullStart);
        const end = new Date(fullEnd);
        
        while (current <= end) {
            const month = current.getMonth();
            const isIncluded = includedMonths.includes(month);
            
            if (!isIncluded && currentGapStart === null) {
                // Start of gap
                currentGapStart = new Date(current);
            } else if (isIncluded && currentGapStart !== null) {
                // End of gap
                gaps.push({
                    start: currentGapStart,
                    end: new Date(current)
                });
                currentGapStart = null;
            }
            
            // Move to next day
            current.setDate(current.getDate() + 1);
        }
        
        // Close last gap if still open
        if (currentGapStart !== null) {
            gaps.push({
                start: currentGapStart,
                end: end
            });
        }
        
        // Draw gap rectangles
        const gapGroup = this.chartGroup.insert('g', ':first-child')
            .attr('class', 'excluded-data-gaps');
        
        gaps.forEach(gap => {
            if (gap.start >= fullStart && gap.end <= fullEnd) {
                gapGroup.append('rect')
                    .attr('x', this.xScale(gap.start))
                    .attr('y', 0)
                    .attr('width', Math.max(1, this.xScale(gap.end) - this.xScale(gap.start)))
                    .attr('height', this.chartHeight)
                    .attr('fill', 'url(#diagonal-hatch)')
                    .attr('stroke', '#ddd')
                    .attr('stroke-width', 1)
                    .attr('pointer-events', 'none');
                
                // Add label for larger gaps
                const gapWidth = this.xScale(gap.end) - this.xScale(gap.start);
                if (gapWidth > 50) {
                    gapGroup.append('text')
                        .attr('x', (this.xScale(gap.start) + this.xScale(gap.end)) / 2)
                        .attr('y', this.chartHeight / 2)
                        .attr('text-anchor', 'middle')
                        .attr('font-size', '11px')
                        .attr('fill', '#666')
                        .attr('opacity', 0.6)
                        .attr('pointer-events', 'none')
                        .text('Excluded');
                }
            }
        });
    },
    
    // Draw Gap area
    drawGapArea(timeseries) {
        const area = d3.area()
            .x(d => this.xScale(d.date))
            .y0(this.chartHeight)
            .y1(d => this.yScale(d.Gap))
            .curve(d3.curveMonotoneX);
        
        this.chartGroup.append('path')
            .datum(timeseries)
            .attr('class', 'gap-area')
            .attr('d', area)
            .attr('fill', '#d73027')
            .attr('opacity', 0.3);
    },
    
    // Draw precipitation bars
    drawPrecipitationBars(timeseries) {
        const barWidth = Math.max(1, this.chartWidth / timeseries.length - 1);
        
        this.chartGroup.selectAll('.p-bar')
            .data(timeseries)
            .join('rect')
            .attr('class', 'p-bar')
            .attr('x', d => this.xScale(d.date) - barWidth / 2)
            .attr('y', d => this.yScale(d.P))
            .attr('width', barWidth)
            .attr('height', d => this.chartHeight - this.yScale(d.P))
            .attr('fill', '#91bfdb')
            .attr('opacity', 0.5);
    },
    
    // Draw line
    drawLine(timeseries, key, color, strokeWidth = 2) {
        const line = d3.line()
            .x(d => this.xScale(d.date))
            .y(d => this.yScale(d[key]))
            .curve(d3.curveMonotoneX);
        
        this.chartGroup.append('path')
            .datum(timeseries)
            .attr('class', `line-${key.toLowerCase()}`)
            .attr('d', line)
            .attr('fill', 'none')
            .attr('stroke', color)
            .attr('stroke-width', strokeWidth);
    },
    
    // Add interaction overlay
    addInteractionOverlay(timeseries) {
        const self = this;
        
        // Create vertical line for hover
        const hoverLine = this.chartGroup.append('line')
            .attr('class', 'hover-line')
            .attr('y1', 0)
            .attr('y2', this.chartHeight)
            .attr('stroke', '#333')
            .attr('stroke-width', 1)
            .attr('stroke-dasharray', '4,4')
            .style('opacity', 0);
        
        // Create overlay for mouse tracking
        const overlay = this.chartGroup.append('rect')
            .attr('class', 'overlay')
            .attr('width', this.chartWidth)
            .attr('height', this.chartHeight)
            .attr('fill', 'none')
            .attr('pointer-events', 'all')
            .on('mousemove', function(event) {
                const [mx] = d3.pointer(event);
                const date = self.xScale.invert(mx);
                
                // Find closest data point
                const bisect = d3.bisector(d => d.date).left;
                const index = bisect(timeseries, date);
                const d0 = timeseries[index - 1];
                const d1 = timeseries[index];
                const d = d1 && (date - d0.date > d1.date - date) ? d1 : d0;
                
                if (d) {
                    // Update hover line
                    hoverLine
                        .attr('x1', self.xScale(d.date))
                        .attr('x2', self.xScale(d.date))
                        .style('opacity', 1);
                    
                    // Show tooltip
                    self.showTimeSeriesTooltip(d, event);
                }
            })
            .on('mouseout', function() {
                hoverLine.style('opacity', 0);
                Utils.hideTooltip();
            });
    },
    
    // Show time series tooltip
    showTimeSeriesTooltip(data, event) {
        const content = `
            <strong>${Utils.formatDateReadable(data.date)}</strong>
            <div style="margin-top: 8px;">
                <div style="color: #91bfdb;">Precipitation: <strong>${Utils.formatNumber(data.P)} mm</strong></div>
                <div style="color: #fc8d59;">ETP: <strong>${Utils.formatNumber(data.ETP)} mm</strong></div>
                <div style="color: #4575b4;">Stock: <strong>${Utils.formatNumber(data.Stock)} mm</strong></div>
                <div style="color: #d73027;">Gap: <strong>${Utils.formatNumber(data.Gap)} mm</strong></div>
                ${Utils.isSummer(data.date) ? '<div style="margin-top: 5px; font-size: 0.85em;">☀️ Summer period</div>' : ''}
            </div>
        `;
        Utils.showTooltip(content, event);
    },
    
    // Update point info
    updatePointInfo(point) {
        d3.select('#selected-point-info')
            .html(`
                Viewing: <strong>${point.id}</strong> 
                (RU: ${Utils.formatNumber(point.ru_max)} mm, 
                Total Gap: ${Utils.formatNumber(point.total_gap)} mm)
            `);
    },
    
    // Toggle series visibility
    toggleSeries(series, visible) {
        this.visibleSeries[series] = visible;
        if (this.currentData) {
            this.update(this.currentPoint, this.currentData);
        }
    },
    
    // Resize chart
    resize() {
        const container = d3.select('#timeseries-container');
        const containerNode = container.node();
        this.width = containerNode.clientWidth;
        this.height = containerNode.clientHeight;
        
        this.chartWidth = this.width - this.margin.left - this.margin.right;
        this.chartHeight = this.height - this.margin.top - this.margin.bottom;
        
        if (this.svg) {
            this.svg.attr('width', this.width).attr('height', this.height);
            if (this.currentData) {
                this.update(this.currentPoint, this.currentData);
            }
        }
    }
};

// Make TimeSeriesViz available globally
window.TimeSeriesViz = TimeSeriesViz;
