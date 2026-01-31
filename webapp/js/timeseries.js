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
    
    // Draw seasonal highlights (summer)
    drawSeasonalHighlights(timeseries) {
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
