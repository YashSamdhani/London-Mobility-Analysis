# 🗺 London Mobility Analysis
### Population-scale movement patterns derived from mobile phone location data — Greater London Area, November 2021

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Data](https://img.shields.io/badge/Data-Mobile%20CDR%2FGPS-4fc9a0?style=flat-square)](.)
[![Geography](https://img.shields.io/badge/Geography-MSOA%20·%20GLA-f4845f?style=flat-square)](.)
[![Sample](https://img.shields.io/badge/Sample-5%2C000%20users%20·%20574K%20stays-7c6af7?style=flat-square)](.)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

---

## Overview

This project analyses human mobility patterns across Greater London using stay-point data derived from mobile phone location traces. It characterises **what people do**, **where they travel**, **how far they range**, and **which movement patterns cluster into functional regions** — with a dedicated lens on privacy risk from sensitive place exposure.

The analysis covers five interconnected themes:

| Theme | Key Output | Core Finding |
|---|---|---|
| Activity patterns | Stay-point classification + transitions | Home/Others dominate; work trips form a distinct minority |
| Origin–destination flows | O-D matrix + flow distribution | Strong intra-zone self-loops; power-law corridor distribution (α = 1.43) |
| Individual mobility | Radius of gyration distribution | Median range 17 km; heavy-tailed, bimodal |
| Flow uniqueness | Entropy, Gini, HHI, LQ, Asymmetry per zone | Most zones are moderately diverse; a minority funnel to a single destination |
| Privacy risk | Sensitive POI mapping + proximity analysis | 3,600+ sensitive locations across GLA; no area is free of sensitive proximity events |

---

## Key Findings

**Londoners are fundamentally local movers.** The O-D matrix diagonal dominates at every spatial scale — most trips start and end in the same MSOA zone. The median radius of gyration is **17 km**, and roughly 70% of users confine monthly movement within 30 km.

**Flow demand is highly concentrated.** O-D corridor volumes follow a power law with exponent α = 1.43. A small fraction of corridors carries a disproportionate share of all trips. Work trips and leisure trips use almost entirely separate corridor networks (Spearman ρ = 0.611 between work and all-activity flows), with most O-D pairs being near-zero for work.

**London's labour market is polycentric.** Louvain community detection on the work-trip network yields **10 roughly equal functional regions** (330–1,050 MSOAs each), challenging the assumption of a single dominant employment centre and suggesting transport planning should serve orbital as well as radial demand.

**Re-identification risk is non-trivial.** Movement patterns are individually predictable — entropy and Gini metrics show moderate destination diversity, but a significant tail of zones with dominant single destinations creates highly fingerprintable mobility signatures. Combined with **3,600+ sensitive POIs** (pharmacies, schools, places of worship, hospitals, military sites) distributed across the entire GLA footprint, any sufficiently precise mobility dataset will contain sensitive proximity events that require careful handling under GDPR Article 9.

---

## Repository Structure

```
london-mobility-analysis/
│
├── data/
│   ├── raw/                        # Source CDR/GPS stay-point files (not committed)
│   ├── processed/
│   │   ├── 06_OD_uniqueness_metrics.csv    # Per-zone entropy, Gini, HHI, LQ, asymmetry
│   │   ├── 10_sensitive_pois.csv           # Sensitive POI catalogue (type, lat, lon)
│   │   ├── 17_top20_corridors.csv          # Top 20 O-D corridors by flow volume
│   │   └── 18_network_communities.csv      # MSOA → Louvain community assignment
│   └── README.md                   # Data dictionary
│
├── notebooks/
│   ├── 01_activity_analysis.ipynb          # Stay-point classification + activity dashboard
│   ├── 02_activity_transitions.ipynb       # Transition matrix construction
│   ├── 05_od_matrix.ipynb                  # O-D heatmap (top 50 origins)
│   ├── 06_od_uniqueness.ipynb              # Entropy/Gini/HHI/LQ metrics
│   ├── 07_metrics_distributions.ipynb      # Distribution plots for all metrics
│   ├── 08_entropy_vs_gini.ipynb            # Uniqueness space scatter
│   ├── 09_radius_gyration.ipynb            # Individual mobility range
│   ├── 10_sensitive_pois.ipynb             # POI catalogue + spatial mapping
│   ├── 11_sensitive_pois_clustered.ipynb   # Interactive cluster map
│   ├── 12_sensitive_pois_heatmap.ipynb     # Density heatmap
│   ├── 15_zipf_flow_distribution.ipynb     # Power-law rank-size plot
│   ├── 18_network_communities.ipynb        # Louvain community detection
│   ├── 21_temporal_profiles.ipynb          # Hourly/daily activity profiles
│   └── 22_work_vs_allactivity.ipynb        # Work trip share analysis
│
├── outputs/
│   ├── figures/                    # All static PNG outputs (numbered to match notebooks)
│   └── html/                       # Interactive HTML maps (Folium/Plotly)
│
├── src/
│   ├── staypoints.py               # Stay-point detection and activity classification
│   ├── od_matrix.py                # O-D flow construction and aggregation
│   ├── metrics.py                  # Entropy, Gini, HHI, LQ, asymmetry calculations
│   ├── community.py                # Louvain community detection wrapper
│   └── privacy.py                  # Sensitive POI proximity analysis
│
├── requirements.txt
└── README.md
```

---

## Visual Outputs

| # | Figure | Description |
|---|---|---|
| 01 | Activity Dashboard | Stay count, median duration, hourly mix, day-of-week volume |
| 02 | Activity Transition Matrix | 8×8 matrix of sequential activity pairs |
| 05 | O-D Flow Heatmap | Top 50 origin zones, log-scale colour |
| 07 | Metrics Distributions | Six histograms: entropy, Gini, HHI, LQ, asymmetry |
| 08 | Entropy vs Gini Scatter | Per-zone uniqueness space (work trips) |
| 09 | Radius of Gyration | Individual mobility range, 5,000-user sample |
| 13 | Sensitive POIs Static | Bar chart + spatial scatter of 11 POI categories |
| 15 | Zipf Flow Distribution | Rank-size log-log plot with power-law fit |
| 19 | Community Sizes | Bar chart of 10 Louvain communities by MSOA count |
| 21 | Temporal Profiles | Hourly distribution, daily distribution, stacked activity-by-hour |
| 22 | Work vs All-Activity | Scatter + work-share histogram per O-D corridor |

Interactive HTML outputs (Folium):
- `11_sensitive_pois_clustered.html` — clustered marker map of all sensitive POIs
- `12_sensitive_pois_heatmap.html` — kernel density heatmap of POI coverage

---

## Methods

### Stay-point Detection
Raw GPS/CDR pings are clustered into stay-points using a distance–duration threshold (δ_d = 200 m, δ_t = 10 min). Each stay-point is classified into one of eight activity types using time-of-day priors, land-use data, and visit frequency:

`Home · Work · Education · Shopping_1 · Shopping_2 · Eating and drinking · Entertainment · Others`

### Origin–Destination Matrix
A trip is recorded between two consecutive distinct stay-points. Trips are aggregated to MSOA level using the centroid of each stay-point's GPS cluster. The full matrix spans ~983 London MSOAs (plus a small number of external zones).

### Flow Uniqueness Metrics
For each origin zone, outgoing trip flows are treated as a probability distribution over destination zones. Six metrics characterise the shape of this distribution:

| Metric | Formula | Interpretation |
|---|---|---|
| Shannon Entropy | H = −Σ pᵢ log₂(pᵢ) | Diversity of destinations (bits) |
| Gini Coefficient | G = 1 − 2∫₀¹L(x)dx | Concentration inequality (0–1) |
| HHI | HHI = Σ pᵢ² | Dominant-destination risk (0–1) |
| Location Quotient | LQ = sᵢ / s̄ | Over/under-representation vs. average |
| Asymmetry | A = \|out−in\| / (out+in) | Directional flow imbalance (0–1) |

### Radius of Gyration
For each user u with N visited locations {rᵢ}, the radius of gyration is:

```
r_g(u) = sqrt( (1/N) * Σ ||rᵢ − r_cm||² )
```

where r_cm is the centre of mass of all visited locations, weighted by visit count.

### Community Detection
The work-trip O-D matrix is treated as a weighted directed graph (MSOAs = nodes, flow volume = edge weight). The Louvain algorithm maximises modularity Q:

```
Q = (1/2m) * Σᵢⱼ [ Aᵢⱼ − kᵢkⱼ/2m ] · δ(cᵢ, cⱼ)
```

where Aᵢⱼ is the adjacency matrix, kᵢ the degree of node i, m the total edge weight, and δ the Kronecker delta over community assignments.

### Sensitive POI Analysis
Sensitive POIs (pharmacies, schools, hospitals, places of worship, military, government, courts, prisons, universities, police stations, social care) are sourced from OpenStreetMap via the Overpass API. Proximity events are defined as a stay-point falling within a configurable radius (default: 100 m) of a sensitive POI.

---

## Findings in Numbers

```
Activity analysis
  Total stay-points recorded          574,149
  Top activity by count               Others (216,766 · 37.7%)
  Home stays                          170,151 (29.6%)
  Work stays                           60,085 (10.5%)
  Median home stay duration           ~480 min
  Median work stay duration           ~150 min
  Busiest day                         Monday (~95,000 stays)

O-D flows
  Power-law exponent (α)              1.43
  Spearman ρ (work vs. all-activity)  0.611
  Dominant flow type                  Intra-zone (diagonal)
  High-flow cluster                   E02005118–E02005155 (inner south London)

Individual mobility
  Sample size                         5,000 users
  Median radius of gyration           17.0 km
  Users with r_g < 30 km             ~70%
  Maximum observed r_g               ~200+ km

Flow uniqueness (work trips)
  Median Shannon entropy              4.929 bits
  Median Gini coefficient             0.389
  Median HHI                          0.051
  Median Location Quotient            0.980
  Median Asymmetry                    0.182

Sensitive POIs
  Total POIs catalogued               3,600+
  Most numerous type                  Pharmacy (1,016)
  Second most numerous                School (904)
  Third most numerous                 Place of worship (590)

Network communities
  Algorithm                           Louvain
  Communities detected                10
  Largest community (C0)              ~1,050 MSOAs
  Smallest community (C9)             ~330 MSOAs
```

---

## Privacy Considerations

This dataset is derived from anonymised mobile phone location data. All analysis is conducted at population level and no individual trajectories are published. However, researchers using similar data should be aware:

**Re-identification risk.** With a median radius of gyration of 17 km and moderate destination entropy, individual movement signatures are distinctive. The combination of home location + workplace + one additional frequent location is sufficient to uniquely identify most individuals in datasets of this scale.

**Sensitive place exposure.** The GLA contains 3,600+ sensitive POIs across 11 categories. Given the density of pharmacies (1,016) and places of worship (590) alone, virtually any mobility trace of sufficient precision will contain proximity events that could infer health status or religion — protected characteristics under GDPR Article 9.

**Data minimisation.** Aggregating to MSOA level reduces but does not eliminate re-identification risk, particularly for zones with small populations or highly predictable flow patterns (low entropy, high Gini outliers).

Any derivative dataset or publication from this work should complete a Data Protection Impact Assessment (DPIA) before release.

---

## Getting Started

```bash
# Clone the repository
git clone https://github.com/your-org/london-mobility-analysis.git
cd london-mobility-analysis

# Install dependencies
pip install -r requirements.txt

# Run all notebooks in order
jupyter nbconvert --to notebook --execute notebooks/01_activity_analysis.ipynb
# or open JupyterLab and run interactively
jupyter lab
```

### Requirements

```
pandas>=1.5
geopandas>=0.13
numpy>=1.24
matplotlib>=3.7
seaborn>=0.12
folium>=0.14
networkx>=3.1
python-louvain>=0.16
scikit-learn>=1.2
scipy>=1.10
shapely>=2.0
```

---

## Data

Raw location data is not included in this repository due to privacy restrictions. The processed outputs in `data/processed/` are derived aggregates at MSOA level and contain no individual-level records.

To reproduce the analysis from raw data, you will need:

- Mobile phone stay-point records in the format `[user_id, timestamp_start, timestamp_end, lat, lon, activity_label]`
- MSOA boundary shapefiles — available from the [ONS Open Geography Portal](https://geoportal.statistics.gov.uk/)
- OpenStreetMap POI data for Greater London — retrievable via the [Overpass API](https://overpass-api.de/)

---

## Citation

If you use this analysis or the methodology in your work, please cite:

```bibtex
@misc{london_mobility_2021,
  title   = {London Mobility Analysis: Population-scale movement patterns
             from mobile phone data, GLA November 2021},
  year    = {2021},
  url     = {https://github.com/your-org/london-mobility-analysis},
  note    = {Data: anonymised mobile CDR/GPS traces, MSOA-level aggregation}
}
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.

The underlying location data is subject to separate data sharing agreements and is not redistributed here. OpenStreetMap POI data is © OpenStreetMap contributors, licensed under [ODbL](https://www.openstreetmap.org/copyright).
