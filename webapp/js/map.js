// Map Visualization Module

const MapViz = {
    svg: null,
    width: 0,
    height: 0,
    projection: null,
    colorScale: null,
    sizeScale: null,
    pointsData: null,
    selectedPoint: null,
    onPointClick: null,
    
    // Initialize the map
    init(containerId, points, onClickCallback) {
        const container = d3.select(`#${containerId}`);
        container.selectAll('*').remove();
        
        this.onPointClick = onClickCallback;
        this.pointsData = points;
        
        // Get container dimensions
        const containerNode = container.node();
        this.width = containerNode.clientWidth;
        this.height = containerNode.clientHeight;
        
        // Create SVG
        this.svg = container.append('svg')
            .attr('width', this.width)
            .attr('height', this.height);
        
        // Set up projection for France (Lambert II étendu approximation)
        // Using Conic Conformal projection centered on France
        this.projection = d3.geoConicConformal()
            .center([2.5, 46.5])
            .scale(3000)
            .translate([this.width / 2, this.height / 2]);
        
        // Set up color scale (inverted so blue = low gap, red = high gap)
        const maxGap = d3.max(points, d => d.total_gap);
        this.colorScale = d3.scaleSequential()
            .domain([0, maxGap])
            .interpolator(d3.interpolateRdYlBu)
            .clamp(true);
        
        // Reverse the color scale (blue for low, red for high)
        const originalScale = this.colorScale;
        this.colorScale = (value) => originalScale(maxGap - value);
        
        // Set up size scale for RU
        const ruExtent = d3.extent(points, d => d.ru_max);
        this.sizeScale = d3.scaleSqrt()
            .domain(ruExtent)
            .range([6, 15]);
        
        // Draw France outline (simplified rectangle)
        this.drawFranceOutline();
        
        // Draw points
        this.drawPoints();
        
        // Update legend
        this.updateLegend(maxGap);
    },
    
    // Draw simplified France outline
    drawFranceOutline() {
        // Draw a background rectangle representing France's approximate extent
        const coords = [
            [Utils.getLambertCoordinates(600, 24010)],
            [Utils.getLambertCoordinates(1200, 24010)],
            [Utils.getLambertCoordinates(1200, 16170)],
            [Utils.getLambertCoordinates(600, 16170)]
        ];
        
        this.svg.append('rect')
            .attr('x', 50)
            .attr('y', 50)
            .attr('width', this.width - 100)
            .attr('height', this.height - 100)
            .attr('fill', '#f0f0f0')
            .attr('stroke', '#999')
            .attr('stroke-width', 2)
            .attr('rx', 5);
        
        // Add title
        this.svg.append('text')
            .attr('x', this.width / 2)
            .attr('y', 30)
            .attr('text-anchor', 'middle')
            .attr('font-size', '14px')
            .attr('font-weight', 'bold')
            .attr('fill', '#333')
            .text('SAFRAN Grid Points');
    },
    
    // Draw SAFRAN points
    drawPoints() {
        const self = this;
        
        // Create a group for points
        const pointsGroup = this.svg.append('g')
            .attr('class', 'points-group');
        
        // Calculate positions manually based on coordinate ranges
        const xScale = d3.scaleLinear()
            .domain([600, 1200])
            .range([100, this.width - 100]);
        
        const yScale = d3.scaleLinear()
            .domain([16170, 26810])
            .range([this.height - 100, 100]);
        
        // Draw points
        const circles = pointsGroup.selectAll('circle')
            .data(this.pointsData)
            .join('circle')
            .attr('class', 'point-circle')
            .attr('cx', d => xScale(d.lambx))
            .attr('cy', d => yScale(d.lamby))
            .attr('r', d => this.sizeScale(d.ru_max))
            .attr('fill', d => this.colorScale(d.total_gap))
            .attr('opacity', 0.8)
            .on('mouseover', function(event, d) {
                d3.select(this)
                    .attr('opacity', 1)
                    .attr('r', self.sizeScale(d.ru_max) * 1.3);
                
                self.showTooltip(d, event);
            })
            .on('mouseout', function(event, d) {
                if (self.selectedPoint?.id !== d.id) {
                    d3.select(this)
                        .attr('opacity', 0.8)
                        .attr('r', self.sizeScale(d.ru_max));
                }
                Utils.hideTooltip();
            })
            .on('click', function(event, d) {
                self.selectPoint(d);
                if (self.onPointClick) {
                    self.onPointClick(d);
                }
            });
        
        // Add labels for points
        pointsGroup.selectAll('text')
            .data(this.pointsData)
            .join('text')
            .attr('x', d => xScale(d.lambx))
            .attr('y', d => yScale(d.lamby) - this.sizeScale(d.ru_max) - 5)
            .attr('text-anchor', 'middle')
            .attr('font-size', '10px')
            .attr('fill', '#333')
            .attr('pointer-events', 'none')
            .text(d => `(${d.lambx}, ${d.lamby})`);
    },
    
    // Show tooltip
    showTooltip(point, event) {
        const content = `
            <strong>${point.id}</strong>
            <div style="margin-top: 8px;">
                <div>Total Gap: <strong>${Utils.formatNumber(point.total_gap)} mm</strong></div>
                <div>Days with Gap: <strong>${point.days_with_gap}</strong></div>
                <div>Max Gap: <strong>${Utils.formatNumber(point.max_gap)} mm</strong></div>
                <div>RU (Soil Reserve): <strong>${Utils.formatNumber(point.ru_max)} mm</strong></div>
                <div>Mean Stock: <strong>${Utils.formatNumber(point.mean_stock)} mm</strong></div>
            </div>
            <div style="margin-top: 8px; font-size: 0.85em; opacity: 0.8;">
                Click to view time series
            </div>
        `;
        Utils.showTooltip(content, event);
    },
    
    // Select a point
    selectPoint(point) {
        this.selectedPoint = point;
        
        // Update visual selection
        this.svg.selectAll('.point-circle')
            .classed('selected', d => d.id === point.id)
            .attr('opacity', d => d.id === point.id ? 1 : 0.6);
    },
    
    // Clear selection
    clearSelection() {
        this.selectedPoint = null;
        this.svg.selectAll('.point-circle')
            .classed('selected', false)
            .attr('opacity', 0.8);
    },
    
    // Update legend
    updateLegend(maxGap) {
        const legendScale = d3.select('#legend-scale');
        
        // Update gradient
        legendScale.style('background', 
            'linear-gradient(to right, #4575b4, #91bfdb, #fee090, #fc8d59, #d73027)');
        
        // Update labels
        d3.select('.legend-label-min').text(`0 mm`);
        d3.select('.legend-label-max').text(`${Utils.formatNumber(maxGap, 0)} mm`);
    },
    
    // Resize map
    resize() {
        const container = d3.select('#map-container');
        const containerNode = container.node();
        this.width = containerNode.clientWidth;
        this.height = containerNode.clientHeight;
        
        if (this.svg) {
            this.svg.attr('width', this.width).attr('height', this.height);
            // Redraw everything
            this.svg.selectAll('*').remove();
            this.drawFranceOutline();
            this.drawPoints();
        }
    }
};

// Make MapViz available globally
window.MapViz = MapViz;
