import requests
import pandas as pd
import numpy as np
import geopandas as gpd
import folium
from folium.plugins import MarkerCluster, HeatMap
import matplotlib.pyplot as plt
import os, time, warnings
warnings.filterwarnings("ignore")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
OUT = os.path.join(SCRIPT_DIR, "outputs")
os.makedirs(OUT, exist_ok=True)

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
HEADERS = {
    "User-Agent": "MobilityResearchBot/1.0 (academic; contact@example.com)",
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded",
}

GLA_BBOX = (51.28, -0.51, 51.70, 0.33)

QUERIES = {
    "hospital":     '[out:json][timeout:60]; node["amenity"~"hospital|clinic"]{bbox}; out body;',
    "pharmacy":     '[out:json][timeout:60]; node["amenity"="pharmacy"]{bbox}; out body;',
    "police":       '[out:json][timeout:60]; node["amenity"="police"]{bbox}; out body;',
    "court":        '[out:json][timeout:60]; node["amenity"~"courthouse|magistrate"]{bbox}; out body;',
    "prison":       '[out:json][timeout:60]; (node["amenity"="prison"]{bbox}; way["amenity"="prison"]{bbox};); out center;',
    "school":       '[out:json][timeout:60]; node["amenity"~"school|kindergarten|childcare"]{bbox}; out body;',
    "university":   '[out:json][timeout:60]; node["amenity"="university"]{bbox}; out body;',
    "place_worship":'[out:json][timeout:60]; node["amenity"="place_of_worship"]{bbox}; out body;',
    "military":     '[out:json][timeout:60]; (node["landuse"="military"]{bbox}; way["landuse"="military"]{bbox};); out center;',
    "social_care":  '[out:json][timeout:60]; node["amenity"~"social_facility|shelter|refugee"]{bbox}; out body;',
    "government":   '[out:json][timeout:60]; node["office"~"government|embassy|consulate"]{bbox}; out body;',
}

COLOURS = {
    "hospital": "#e74c3c", "pharmacy": "#ff8fab", "police": "#2980b9",
    "court": "#1a5276", "prison": "#6c3483", "school": "#f39c12",
    "university": "#d4ac0d", "place_worship": "#27ae60",
    "military": "#7f8c8d", "social_care": "#e67e22", "government": "#2ecc71",
}


def fetch_poi(category, query_template, bbox, retries=3):
    bbox_str = f"({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]})"
    query = query_template.replace("{bbox}", bbox_str)
    for attempt, url in enumerate(OVERPASS_ENDPOINTS * retries):
        if attempt >= retries * len(OVERPASS_ENDPOINTS):
            break
        try:
            resp = requests.post(url, data={"data": query}, headers=HEADERS, timeout=90)
            resp.raise_for_status()
            rows = []
            for el in resp.json().get("elements", []):
                lat = el.get("lat") or el.get("center", {}).get("lat")
                lon = el.get("lon") or el.get("center", {}).get("lon")
                if lat and lon:
                    tags = el.get("tags", {})
                    rows.append({
                        "category": category, "lat": lat, "lon": lon,
                        "name": tags.get("name", ""),
                        "amenity": tags.get("amenity", tags.get("landuse", tags.get("office", ""))),
                    })
            return pd.DataFrame(rows)
        except Exception as e:
            wait = 2 * (attempt % retries + 1)
            print(f"  {url.split('/')[2]} failed ({e}), retry in {wait}s …")
            time.sleep(wait)
    print(f"  All endpoints failed for {category}")
    return pd.DataFrame()


print("Fetching sensitive PoIs from OpenStreetMap …")
pois = []
for cat, query in QUERIES.items():
    print(f"  {cat} …", end=" ", flush=True)
    df = fetch_poi(cat, query, GLA_BBOX)
    print(len(df))
    pois.append(df)
    time.sleep(1.5)

poi_df = pd.concat(pois, ignore_index=True)
poi_df.to_csv(f"{OUT}/08_sensitive_pois.csv", index=False)
print(f"\nTotal: {len(poi_df):,} PoIs")
print(poi_df.groupby("category").size().to_string())

# interactive clustered map
m = folium.Map(location=[51.50, -0.12], zoom_start=11, tiles="CartoDB dark_matter")
for cat in poi_df["category"].unique():
    sub = poi_df[poi_df["category"] == cat]
    layer = folium.FeatureGroup(name=f"{cat.replace('_',' ').title()} ({len(sub)})")
    cluster = MarkerCluster().add_to(layer)
    for _, row in sub.iterrows():
        folium.Marker(
            location=[row["lat"], row["lon"]],
            tooltip=f"<b>{row['name'] or cat.title()}</b><br>{row['amenity']}",
            icon=folium.Icon(color="blue", icon="info-sign", prefix="fa"),
        ).add_to(cluster)
    layer.add_to(m)
folium.LayerControl(collapsed=False).add_to(m)
m.save(f"{OUT}/09_pois_clustered.html")

# per-category heatmap overlay
m2 = folium.Map(location=[51.50, -0.12], zoom_start=11, tiles="CartoDB dark_matter")
for cat in poi_df["category"].unique():
    sub = poi_df[poi_df["category"] == cat][["lat","lon"]].dropna()
    if len(sub) < 5:
        continue
    fg = folium.FeatureGroup(name=f"{cat} heatmap")
    HeatMap(sub.values.tolist(), radius=18, blur=15, max_zoom=15, min_opacity=0.3).add_to(fg)
    fg.add_to(m2)
folium.LayerControl().add_to(m2)
m2.save(f"{OUT}/10_pois_heatmap.html")

# static summary bar + scatter map
cat_counts = poi_df.groupby("category").size().sort_values()
fig, axes = plt.subplots(1, 2, figsize=(18, 8))
fig.patch.set_facecolor("#0d1117")

ax = axes[0]
ax.set_facecolor("#1a1a2e")
bars = ax.barh(cat_counts.index, cat_counts.values,
               color=[COLOURS.get(c, "#888") for c in cat_counts.index], edgecolor="none")
for bar, val in zip(bars, cat_counts.values):
    ax.text(val + 5, bar.get_y() + bar.get_height() / 2,
            f"{val:,}", va="center", color="white", fontsize=9)
ax.set_xlabel("Count", color="white", fontsize=11)
ax.set_title("Sensitive PoI Counts — Greater London Area", color="white", fontsize=12, pad=10)
ax.tick_params(colors="white")
for sp in ax.spines.values(): sp.set_color("#333")

ax = axes[1]
ax.set_facecolor("#1a1a2e")
for cat in poi_df["category"].unique():
    sub = poi_df[poi_df["category"] == cat]
    ax.scatter(sub["lon"], sub["lat"], s=4, alpha=0.5,
               c=COLOURS.get(cat, "#888"), label=cat.replace("_", " ").title())
ax.set_xlabel("Longitude", color="white")
ax.set_ylabel("Latitude", color="white")
ax.set_title("Spatial Distribution of Sensitive PoIs — GLA", color="white", fontsize=12, pad=10)
ax.tick_params(colors="white")
ax.legend(loc="lower right", fontsize=7, facecolor="#1a1a2e", labelcolor="white", markerscale=3)
for sp in ax.spines.values(): sp.set_color("#333")

plt.tight_layout()
plt.savefig(f"{OUT}/11_pois_static.png", dpi=180, bbox_inches="tight", facecolor="#0d1117")
plt.close()

# privacy risk proxy — sensitive PoI density near each user's top destination
try:
    stays = pd.read_csv(os.path.join(DATA_DIR, "trajectory_GLA_sample5000_updated.csv"))
    stays = stays.rename(columns={"userid": "uid", "loc_msoa": "msoa", "activity": "activity"})

    msoa_geojson = os.path.join(DATA_DIR, "msoa_boundaries.geojson")
    if not os.path.exists(msoa_geojson):
        raise FileNotFoundError("msoa_boundaries.geojson not found")

    msoa_geo = gpd.read_file(msoa_geojson)
    msoa_geo.columns = [c if i > 0 else "msoa" for i, c in enumerate(msoa_geo.columns)]
    msoa_geo["clat"] = msoa_geo.geometry.centroid.y
    msoa_geo["clon"] = msoa_geo.geometry.centroid.x

    # most-visited non-home MSOA per user
    top_dest = (stays[stays["activity"] != "Home"]
                .groupby(["uid","msoa"]).size()
                .reset_index(name="visits")
                .sort_values("visits", ascending=False)
                .drop_duplicates("uid")
                .merge(msoa_geo[["msoa","clat","clon"]], on="msoa"))

    poi_gdf  = gpd.GeoDataFrame(poi_df,
                                geometry=gpd.points_from_xy(poi_df["lon"], poi_df["lat"]),
                                crs="EPSG:4326").to_crs("EPSG:27700")
    dest_gdf = gpd.GeoDataFrame(top_dest,
                                geometry=gpd.points_from_xy(top_dest["clon"], top_dest["clat"]),
                                crs="EPSG:4326").to_crs("EPSG:27700")
    dest_buf = dest_gdf.copy()
    dest_buf["geometry"] = dest_buf.geometry.buffer(500)

    joined = gpd.sjoin(poi_gdf, dest_buf, how="inner", predicate="within")
    risk = joined.groupby("uid").size().reset_index(name="poi_within_500m")
    top_dest = top_dest.merge(risk, on="uid", how="left").fillna(0)

    fig, ax = plt.subplots(figsize=(11, 8))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#1a1a2e")
    ax.hist(top_dest["poi_within_500m"], bins=30, color="#e74c3c", edgecolor="none", alpha=0.8)
    ax.set_xlabel("Sensitive PoIs within 500m of top destination", color="white", fontsize=11)
    ax.set_ylabel("# Users", color="white", fontsize=11)
    ax.set_title("Privacy-Risk Proxy: PoI Density at Most-Visited Destinations",
                 color="white", fontsize=12)
    ax.tick_params(colors="white")
    for sp in ax.spines.values(): sp.set_color("#333")
    pct = (top_dest["poi_within_500m"] >= 3).mean() * 100
    ax.text(0.97, 0.95, f"{pct:.1f}% of users' top destination\nnear ≥3 sensitive PoIs",
            transform=ax.transAxes, ha="right", va="top", color="white", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.3", fc="#e74c3c", alpha=0.7))
    plt.tight_layout()
    plt.savefig(f"{OUT}/12_poi_privacy_risk.png", dpi=180,
                bbox_inches="tight", facecolor="#0d1117")
    plt.close()

except Exception as e:
    print(f"Privacy risk map skipped: {e}")

print("Task 3 done → outputs/08–12")
