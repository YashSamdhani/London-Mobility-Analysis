# Urban Mobility Analysis — England Dataset (Zenodo 13327082)

Paper: https://www.nature.com/articles/s41597-025-06323-8  
Data: https://zenodo.org/records/13327082

## Setup

```bash
pip install geopandas folium osmnx shapely contextily matplotlib seaborn scipy pandas numpy networkx requests
```

## Data

```bash
mkdir -p data
curl -L "https://zenodo.org/records/13327082/files/trajectory_GLA_sample5000.csv.gz?download=1" -o data/trajectory_GLA_sample5000.csv.gz
curl -L "https://zenodo.org/records/13327082/files/msoa_OD_travel2work.csv.gz?download=1" -o data/msoa_OD_travel2work.csv.gz
curl -L "https://zenodo.org/records/13327082/files/msoa_OD_allactivity.csv.gz?download=1" -o data/msoa_OD_allactivity.csv.gz

# MSOA boundaries (needed for Task 3 privacy risk map)
curl -L "https://services1.arcgis.com/ESMARspQHYMTt3So/arcgis/rest/services/MSOA_Dec_2011_Boundaries_Super_Generalised_Clipped_BSC_EW_V3/FeatureServer/0/query?where=1%3D1&outFields=MSOA11CD&outSR=4326&f=geojson" -o data/msoa_boundaries.geojson
```

## Running

```bash
python run_all.py            # all four tasks
python 01_visualisation.py   # activity dashboard + OD matrix
python 02_uniqueness_metrics.py  # entropy, Gini, HHI, LQ, asymmetry
python 03_sensitive_pois.py  # OSM PoI scrape + privacy risk
python 04_patterns.py        # Zipf, communities, temporal, flow overlap
```

## Outputs

| File | Description |
|------|-------------|
| `01_activity_dashboard.png` | Stay counts, durations, hourly heatmap, day-of-week |
| `02_activity_transitions.png` | Activity sequence transition matrix |
| `03_od_matrix.png` | OD flow heatmap (top 50 origins) |
| `04_uniqueness_metrics.csv` | Per-zone metric table |
| `05_metric_distributions.png` | Histograms of all six metrics |
| `06_entropy_vs_gini.png` | Entropy–Gini scatter (uniqueness space) |
| `07_mobility_range.png` | Distribution of unique zones per user |
| `08_sensitive_pois.csv` | All scraped PoIs with lat/lon |
| `09_pois_clustered.html` | Interactive clustered PoI map |
| `10_pois_heatmap.html` | Per-category heatmap overlay |
| `11_pois_static.png` | Bar chart + scatter map |
| `12_poi_privacy_risk.png` | PoI density near user destinations |
| `13_zipf_flows.png` | Rank-size / Zipf fit |
| `14_top20_corridors.csv` | Dominant OD pairs |
| `15_network_communities.csv` | Louvain community assignments |
| `16_community_sizes.png` | Community size distribution |
| `17_temporal_profiles.png` | Hourly, daily, and per-activity profiles |
| `18_work_vs_all.png` | Work flow vs all-activity scatter + share histogram |
