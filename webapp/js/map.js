// Map Visualization Module with Spatial Interpolation

const MapViz = {
    svg: null,
    width: 0,
    height: 0,
    projection: null,
    colorScale: null,
    pointsData: null,
    selectedPoint: null,
    onPointClick: null,
    currentMetric: 'mean_stock', // Default metric to visualize
    gridData: null,
    
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
        
        // Create defs for gradients
        const defs = this.svg.append('defs');
        
        // Add blur filter for smooth interpolation
        const filter = defs.append('filter')
            .attr('id', 'blur')
            .attr('x', '-50%')
            .attr('y', '-50%')
            .attr('width', '200%')
            .attr('height', '200%');
        
        filter.append('feGaussianBlur')
            .attr('in', 'SourceGraphic')
            .attr('stdDeviation', '30');
        
        // Set up color scale for stock (blue gradient with better contrast)
        const stockExtent = d3.extent(points, d => d.mean_stock);
        this.colorScale = d3.scaleSequential()
            .domain(stockExtent)
            .interpolator(t => d3.interpolateBlues(0.3 + t * 0.7)); // Use 30-100% of the color range for better contrast
        
        // Create main group
        this.mainGroup = this.svg.append('g');
        
        // Draw France outline
        this.drawFranceOutline();
        
        // Draw interpolated heatmap
        this.drawHeatmap();
        
        // Draw invisible points for interaction
        this.drawInteractionLayer();
        
        // Update legend
        this.updateLegend(stockExtent);
        
        // Add title
        this.addTitle();
    },
    
    // Draw France outline (will be updated after heatmap calculates bounds)
    drawFranceOutline() {
        // This will be drawn after heatmap to use correct bounds
    },
    
    // Draw interpolated heatmap
    drawHeatmap() {
        // Calculate position scales
        const xExtent = d3.extent(this.pointsData, d => d.lambx);
        const yExtent = d3.extent(this.pointsData, d => d.lamby);
        
        // Calculate aspect ratio of the data
        const dataWidth = xExtent[1] - xExtent[0];
        const dataHeight = yExtent[1] - yExtent[0];
        const dataAspectRatio = dataWidth / dataHeight;
        
        // Calculate available space
        const padding = 80;
        const availableWidth = this.width - 2 * padding;
        const availableHeight = this.height - 2 * padding;
        const containerAspectRatio = availableWidth / availableHeight;
        
        // Determine scaling to fit the map properly
        let mapWidth, mapHeight, offsetX, offsetY;
        if (dataAspectRatio > containerAspectRatio) {
            // Data is wider - fit to width
            mapWidth = availableWidth;
            mapHeight = availableWidth / dataAspectRatio;
            offsetX = padding;
            offsetY = (this.height - mapHeight) / 2;
        } else {
            // Data is taller - fit to height
            mapHeight = availableHeight;
            mapWidth = availableHeight * dataAspectRatio;
            offsetX = (this.width - mapWidth) / 2;
            offsetY = padding;
        }
        
        const xScale = d3.scaleLinear()
            .domain(xExtent)
            .range([offsetX, offsetX + mapWidth]);
        
        const yScale = d3.scaleLinear()
            .domain(yExtent)
            .range([offsetY + mapHeight, offsetY]);
        
        // Store scales for reuse
        this.xScale = xScale;
        this.yScale = yScale;
        this.mapBounds = { offsetX, offsetY, mapWidth, mapHeight };
        
        // Create grid for interpolation
        const gridSize = 50; // Resolution of the interpolation grid
        const gridWidth = Math.ceil(mapWidth / gridSize);
        const gridHeight = Math.ceil(mapHeight / gridSize);
        
        // Create contour data using Voronoi-based interpolation
        const contourData = [];
        
        // Generate grid points and interpolate values
        for (let i = 0; i < gridWidth; i++) {
            for (let j = 0; j < gridHeight; j++) {
                const x = offsetX + i * gridSize;
                const y = offsetY + j * gridSize;
                
                // Find nearest data point (inverse distance weighting)
                let value = this.interpolateValue(x, y, xScale, yScale);
                
                if (value !== null) {
                    contourData.push({
                        x: x,
                        y: y,
                        value: value
                    });
                }
            }
        }
        
        // Draw map boundary
        this.mainGroup.append('rect')
            .attr('class', 'map-boundary')
            .attr('x', offsetX - 10)
            .attr('y', offsetY - 10)
            .attr('width', mapWidth + 20)
            .attr('height', mapHeight + 20)
            .attr('fill', 'none')
            .attr('stroke', '#2c3e50')
            .attr('stroke-width', 3)
            .attr('rx', 8);
        
        // Draw heatmap cells
        const heatmapGroup = this.mainGroup.append('g')
            .attr('class', 'heatmap-layer')
            .attr('opacity', 0.85);
        
        heatmapGroup.selectAll('rect')
            .data(contourData)
            .join('rect')
            .attr('x', d => d.x)
            .attr('y', d => d.y)
            .attr('width', gridSize)
            .attr('height', gridSize)
            .attr('fill', d => this.colorScale(d.value))
            .attr('stroke', 'none')
            .style('filter', 'url(#blur)');
    },
    
    // Interpolate value at position using inverse distance weighting
    interpolateValue(x, y, xScale, yScale) {
        const k = 8; // Number of nearest neighbors (increased for smoother interpolation)
        const power = 2.5; // IDW power parameter (increased for more localized influence)
        
        // Calculate distances to all points
        const distances = this.pointsData.map(point => {
            const px = xScale(point.lambx);
            const py = yScale(point.lamby);
            const dist = Math.sqrt(Math.pow(x - px, 2) + Math.pow(y - py, 2));
            return {
                point: point,
                distance: dist
            };
        });
        
        // Sort by distance and take k nearest
        distances.sort((a, b) => a.distance - b.distance);
        const nearest = distances.slice(0, k);
        
        // If closest point is very close, use its value directly
        if (nearest[0].distance < 1) {
            return nearest[0].point[this.currentMetric];
        }
        
        // Inverse distance weighting
        let weightSum = 0;
        let valueSum = 0;
        
        for (let item of nearest) {
            if (item.distance === 0) continue;
            const weight = 1 / Math.pow(item.distance, power);
            weightSum += weight;
            valueSum += weight * item.point[this.currentMetric];
        }
        
        return weightSum > 0 ? valueSum / weightSum : null;
    },
    
    // Draw invisible interaction layer
    drawInteractionLayer() {
        const self = this;
        
        // Use stored scales from heatmap
        const xScale = this.xScale;
        const yScale = this.yScale;
        
        // Create interaction points
        const interactionGroup = this.mainGroup.append('g')
            .attr('class', 'interaction-layer');
        
        interactionGroup.selectAll('circle')
            .data(this.pointsData)
            .join('circle')
            .attr('cx', d => xScale(d.lambx))
            .attr('cy', d => yScale(d.lamby))
            .attr('r', 8)
            .attr('fill', 'transparent')
            .attr('stroke', 'transparent')
            .attr('stroke-width', 2)
            .style('cursor', 'pointer')
            .on('mouseover', function(event, d) {
                d3.select(this)
                    .attr('stroke', '#fff')
                    .attr('stroke-width', 3)
                    .attr('fill', 'rgba(255, 255, 255, 0.2)');
                
                self.showTooltip(d, event);
            })
            .on('mouseout', function(event, d) {
                if (self.selectedPoint?.id !== d.id) {
                    d3.select(this)
                        .attr('stroke', 'transparent')
                        .attr('fill', 'transparent');
                }
                Utils.hideTooltip();
            })
            .on('click', function(event, d) {
                self.selectPoint(d);
                if (self.onPointClick) {
                    self.onPointClick(d);
                }
            });
    },
    
    // Show tooltip
    showTooltip(point, event) {
        const content = `
            <strong>Point (${point.lambx}, ${point.lamby})</strong>
            <div style="margin-top: 8px;">
                <div>Mean Stock: <strong>${Utils.formatNumber(point.mean_stock, 1)} mm</strong></div>
                <div>Total Gap: <strong>${Utils.formatNumber(point.total_gap, 1)} mm</strong></div>
                <div>Days with Gap: <strong>${point.days_with_gap}</strong></div>
                <div>RU (Soil Reserve): <strong>${Utils.formatNumber(point.ru_max, 0)} mm</strong></div>
            </div>
            <div style="margin-top: 8px; font-size: 0.85em; opacity: 0.8;">
                Click to view time series
            </div>
        `;
        Utils.showTooltip(content, event);
    },
    
    // Select a point
    selectPoint(point, xScale, yScale) {
        this.selectedPoint = point;
        
        // Use stored scales if not provided
        const xScaleToUse = xScale || this.xScale;
        const yScaleToUse = yScale || this.yScale;
        
        // Update visual selection
        this.mainGroup.selectAll('.interaction-layer circle')
            .attr('stroke', d => d.id === point.id ? '#fff' : 'transparent')
            .attr('stroke-width', d => d.id === point.id ? 3 : 2)
            .attr('fill', d => d.id === point.id ? 'rgba(255, 255, 255, 0.3)' : 'transparent')
            .attr('r', d => d.id === point.id ? 12 : 8);
        
        // Add selection marker
        this.mainGroup.selectAll('.selection-marker').remove();
        this.mainGroup.append('circle')
            .attr('class', 'selection-marker')
            .attr('cx', xScaleToUse(point.lambx))
            .attr('cy', yScaleToUse(point.lamby))
            .attr('r', 20)
            .attr('fill', 'none')
            .attr('stroke', '#fff')
            .attr('stroke-width', 3)
            .attr('stroke-dasharray', '5,5')
            .style('pointer-events', 'none')
            .style('animation', 'pulse 2s ease-in-out infinite');
    },
    
    // Clear selection
    clearSelection() {
        this.selectedPoint = null;
        this.mainGroup.selectAll('.interaction-layer circle')
            .attr('stroke', 'transparent')
            .attr('fill', 'transparent')
            .attr('r', 8);
        this.mainGroup.selectAll('.selection-marker').remove();
    },
    
    // Update metric being displayed
    updateMetric(metric) {
        this.currentMetric = metric;
        
        // Update color scale with adjusted range for better contrast
        const extent = d3.extent(this.pointsData, d => d[metric]);
        const baseInterpolator = metric === 'total_gap' ? d3.interpolateReds : d3.interpolateBlues;
        const adjustedInterpolator = t => baseInterpolator(0.3 + t * 0.7);
        this.colorScale.domain(extent).interpolator(adjustedInterpolator);
        
        // Redraw heatmap (remove both heatmap and boundary)
        this.mainGroup.select('.heatmap-layer').remove();
        this.mainGroup.select('.map-boundary').remove();
        this.drawHeatmap();
        
        // Update legend
        this.updateLegend(extent);
    },
    
    // Add title
    addTitle() {
        this.svg.append('text')
            .attr('class', 'map-title')
            .attr('x', this.width / 2)
            .attr('y', 30)
            .attr('text-anchor', 'middle')
            .attr('font-size', '20px')
            .attr('font-weight', '600')
            .attr('fill', '#2c3e50')
            .text('Water Balance across France - SAFRAN Grid');
    },
    
    // Update legend
    updateLegend(extent) {
        const legendId = '#map-legend';
        const legend = d3.select(legendId);
        
        if (legend.empty()) return;
        
        // Update text labels
        const metricName = this.currentMetric === 'total_gap' ? 'Water Deficit' : 'Soil Water Stock';
        const unit = 'mm';
        
        legend.select('h3').text(`${metricName} (${unit})`);
        legend.select('.legend-label-min').text(`${Utils.formatNumber(extent[0], 0)} ${unit}`);
        legend.select('.legend-label-max').text(`${Utils.formatNumber(extent[1], 0)} ${unit}`);
        
        // Update gradient (matching the adjusted color ranges)
        const gradientColors = this.currentMetric === 'total_gap' 
            ? 'linear-gradient(to right, #fee5d9, #fcae91, #fb6a4a, #de2d26, #a50f15)'
            : 'linear-gradient(to right, #c6dbef, #9ecae1, #6baed6, #4292c6, #2171b5, #08519c, #08306b)';
        
        legend.select('.legend-scale').style('background', gradientColors);
    },
    
    // Resize map
    resize() {
        const container = d3.select('#map-container');
        const containerNode = container.node();
        this.width = containerNode.clientWidth;
        this.height = containerNode.clientHeight;
        
        if (this.svg && this.pointsData) {
            // Reinitialize with current data
            const callback = this.onPointClick;
            const points = this.pointsData;
            this.init('map-container', points, callback);
            
            // Restore selection if exists
            if (this.selectedPoint) {
                this.selectPoint(this.selectedPoint);
            }
        }
    }
};

// Make MapViz available globally
window.MapViz = MapViz;
