# Hydric Gap Visualization - Interactive Web Application

An interactive visualization of agricultural water deficits across France, built with D3.js.

![Preview](../data/gap_visualization.png)

## Quick Start

### 1. Prepare the Data

```bash
# From the project root
cd /Users/thomas/study/visu/hydragri
source .venv/bin/activate
python scripts/prepare_data.py
```

This will generate the JSON files needed by the web application.

### 2. Start a Local Server

```bash
cd webapp
python -m http.server 8000
```

Or use any other local server (Node.js http-server, VS Code Live Server, etc.)

### 3. Open in Browser

Navigate to: `http://localhost:8000`

## Features

### Interactive Map
- **Click** on SAFRAN points to view their time series
- **Hover** for detailed statistics
- **Color coding** shows total water deficit (blue = low, red = high)
- **Circle size** represents soil water reserve capacity

### Time Series Charts
- **Multiple variables** displayed simultaneously:
  - Precipitation (P) - Blue bars
  - Evapotranspiration (ETP) - Orange line
  - Soil water stock - Dark blue line
  - Water deficit (Gap) - Red area
- **Hover** over chart to see exact values for any date
- **Summer periods** highlighted in yellow
- **Toggle** individual series on/off

### Filters and Controls
- **Point selector**: Choose specific SAFRAN points
- **Year filter**: View data for specific years (2020-2025)
- **Season filter**: Focus on Winter, Spring, Summer, or Fall
- **Series toggles**: Show/hide individual variables
- **Reset button**: Clear all filters

### Statistics Panel
Real-time statistics for the selected point and filters:
- Total precipitation and ETP
- Total water deficit
- Days with deficit
- Maximum daily deficit
- Soil stock levels

## Project Structure

```
webapp/
├── index.html              # Main page
├── css/
│   └── styles.css         # All styling
├── js/
│   ├── main.js            # Application controller
│   ├── utils.js           # Data utilities
│   ├── map.js             # Map visualization
│   └── timeseries.js      # Time series charts
├── data/
│   ├── gap_data.json      # Time series data
│   └── points_metadata.json  # Point summaries
└── README.md              # This file
```

## Technologies

- **HTML5/CSS3**: Page structure and styling
- **JavaScript ES6+**: Application logic
- **D3.js v7**: Data visualization library

## Understanding the Data

### What is Hydric Gap?

The **Hydric Gap** (water deficit) represents the amount of water crops need but cannot get from rainfall and soil reserves. It indicates irrigation requirements.

**Formula:** `Gap = Besoin - (P + Stock)`

Where:
- **Besoin** (Crop water need) = ETP × Kc
- **P** (Precipitation): Rainfall in mm
- **Stock**: Available water in soil
- **ETP**: Evapotranspiration (atmospheric water demand)
- **Kc**: Crop coefficient (currently 0.9 universal)

### Data Sources

- **SAFRAN Grid**: Météo-France meteorological data (8km resolution)
- **Soil Data**: BDGSF - Soil water reserve capacity
- **Period**: 2020-2025 (6 years of daily data)
- **Points**: 3 SAFRAN grid points (prototype)

## Browser Support

Modern browsers with ES6+ support:
- Chrome 60+
- Firefox 60+
- Safari 12+
- Edge 79+

## Customization

### Change Color Scheme

Edit `css/styles.css`:

```css
:root {
    --color-stock: #4575b4;    /* Stock line color */
    --color-gap: #d73027;      /* Gap area color */
    --color-precipitation: #91bfdb;  /* P bars color */
    --color-etp: #fc8d59;      /* ETP line color */
}
```

### Add More Points

1. Process additional points in Python:
   ```python
   # In process_gap.py, change:
   n_test_points = 10  # or more
   ```

2. Re-run data preparation:
   ```bash
   python scripts/prepare_data.py
   ```

3. Refresh the web application - it will automatically load all points

## Deployment

This is a static web application that can be deployed to:

### GitHub Pages

```bash
# Push webapp folder to gh-pages branch
git subtree push --prefix webapp origin gh-pages
```

### Netlify

1. Drag and drop the `webapp/` folder to Netlify
2. Or connect your repository and set build folder to `webapp/`

### Any Static Host

Simply upload the contents of the `webapp/` folder.

## Documentation

For detailed technical documentation, see:
- [Architecture Guide](../docs/webapp_architecture.md)
- [Data Processing Guide](../README_GAP_PROCESSING.txt)

## Course Context

This project was created for the **Interactive Data Visualization** course, focusing on:
- Original D3.js visualizations
- Interactive linked views
- Climate change data communication
- Web-based data exploration

## License

This project uses open data sources. Please credit the data providers when reusing.

## Support

For issues or questions, please refer to the project documentation or contact the course instructor.

---

**Version:** 1.0 (Prototype)  
**Last Updated:** January 30, 2026
