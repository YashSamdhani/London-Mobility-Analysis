import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import spearmanr
import networkx as nx
import os, warnings
warnings.filterwarnings("ignore")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
OUT = os.path.join(SCRIPT_DIR, "outputs")
os.makedirs(OUT, exist_ok=True)

work_od = pd.read_csv(os.path.join(DATA_DIR, "MSOA_county_home_work.csv"))
all_od  = pd.read_csv(os.path.join(DATA_DIR, "msoa_ODs_allactivity.csv"))
stays   = pd.read_csv(os.path.join(DATA_DIR, "trajectory_GLA_sample5000_updated.csv"))

def clean_od(df):
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    mapping = {}
    for c in df.columns:
        if c in ("origin","o","orig","from","o_msoa","home","home_msoa","origin_msoa",
                 "msoa_o","start_msoa","msoa21cd_home","msoa11cd_home"):
            mapping[c] = "origin"
        elif c in ("destination","d","dest","to","d_msoa","work","work_msoa","dest_msoa",
                   "msoa_d","end_msoa","msoa21cd_work","msoa11cd_work"):
            mapping[c] = "destination"
        elif c in ("flow","count","trips","journeys","n","num","workers",
                   "commuters","weight","value","total"):
            mapping[c] = "flow"
        elif c.endswith("_home") and c.startswith("msoa"):
            mapping[c] = "origin"
        elif c.endswith("_work") and c.startswith("msoa"):
            mapping[c] = "destination"
    df.rename(columns=mapping, inplace=True)
    if "flow" not in df.columns:
        for c in df.columns:
            if c not in ("origin", "destination") and pd.api.types.is_numeric_dtype(df[c]):
                df.rename(columns={c: "flow"}, inplace=True)
                break
    return df

work_od = clean_od(work_od)
all_od  = clean_od(all_od)

stays = stays.rename(columns={
    "userid": "uid", "start_time": "t_start", "end_time": "t_end",
    "duration": "duration", "loc_msoa": "msoa", "activity": "activity",
})
stays["t_start"] = pd.to_datetime(stays["t_start"], errors="coerce")

# rank-size distribution — does flow follow Zipf?
flows_sorted = all_od["flow"].sort_values(ascending=False).reset_index(drop=True)
ranks = np.arange(1, len(flows_sorted) + 1)
mask  = flows_sorted > 0
coeffs = np.polyfit(np.log(ranks[mask]), np.log(flows_sorted[mask]), 1)
alpha  = -coeffs[0]
print(f"Zipf exponent α = {alpha:.3f}  (pure Zipf = 1.0)")

fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#1a1a2e")
ax.loglog(ranks[mask], flows_sorted[mask], '.', color="#ff6b35", alpha=0.3, ms=2)
x_fit = np.logspace(0, np.log10(len(flows_sorted)), 200)
ax.loglog(x_fit, np.exp(coeffs[1]) * x_fit**coeffs[0],
          color="white", linewidth=2, label=f"power-law fit  α = {alpha:.2f}")
ax.set_xlabel("Rank", color="white")
ax.set_ylabel("Flow volume", color="white")
ax.set_title("Rank-Size Distribution of O-D Flows (all activity)", color="white", fontsize=12)
ax.legend(facecolor="#0d1117", labelcolor="white")
ax.tick_params(colors="white")
for sp in ax.spines.values(): sp.set_color("#333")
plt.tight_layout()
plt.savefig(f"{OUT}/13_zipf_flows.png", dpi=180, bbox_inches="tight", facecolor="#0d1117")
plt.close()

# top-20 corridors
top20 = all_od.nlargest(20, "flow")[["origin","destination","flow"]]
print(top20.to_string(index=False))
top20.to_csv(f"{OUT}/14_top20_corridors.csv", index=False)

# community detection on work-trip network
G = nx.from_pandas_edgelist(
    work_od[work_od["flow"] > 0],
    source="origin", target="destination", edge_attr="flow",
    create_using=nx.DiGraph())
print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

try:
    from networkx.algorithms.community import louvain_communities
    communities = louvain_communities(G.to_undirected(), seed=42)
    comm_map = {node: i for i, comm in enumerate(communities) for node in comm}
    comm_df  = pd.DataFrame(list(comm_map.items()), columns=["msoa","community"])
    print(f"Found {len(communities)} communities")
    comm_df.to_csv(f"{OUT}/15_network_communities.csv", index=False)

    comm_sizes = comm_df["community"].value_counts().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#1a1a2e")
    ax.bar(range(len(comm_sizes)), comm_sizes.values,
           color=plt.cm.tab20(np.linspace(0, 1, len(comm_sizes))), edgecolor="none")
    ax.set_xlabel("Community ID (ranked by size)", color="white")
    ax.set_ylabel("# MSOA zones", color="white")
    ax.set_title(f"Work-Trip Network — {len(communities)} Mobility Communities (Louvain)",
                 color="white", fontsize=12)
    ax.tick_params(colors="white")
    for sp in ax.spines.values(): sp.set_color("#333")
    plt.tight_layout()
    plt.savefig(f"{OUT}/16_community_sizes.png", dpi=180,
                bbox_inches="tight", facecolor="#0d1117")
    plt.close()

except Exception as e:
    print(f"Community detection failed: {e}")

# temporal profiles
stays["hour"] = stays["t_start"].dt.hour
stays["day"]  = stays["t_start"].dt.day_name()
dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

hourly     = stays.groupby("hour").size().reset_index(name="count")
daily      = stays.groupby("day").size().reindex(dow_order).reset_index(name="count")
hourly_act = stays.groupby(["hour","activity"]).size().unstack(fill_value=0)

fig, axes = plt.subplots(1, 3, figsize=(22, 5))
fig.patch.set_facecolor("#0d1117")
for ax in axes:
    ax.set_facecolor("#1a1a2e")

axes[0].bar(hourly["hour"], hourly["count"], color="#4ecdc4", edgecolor="none")
axes[0].set_title("Hourly Stay Distribution", color="white", fontsize=11)
axes[0].set_xlabel("Hour of day", color="white")
axes[0].set_ylabel("# Stays", color="white")
axes[0].tick_params(colors="white")
for sp in axes[0].spines.values(): sp.set_color("#333")

axes[1].bar(daily["day"], daily["count"],
            color=["#ff6b6b" if d in ("Saturday","Sunday") else "#4ecdc4"
                   for d in daily["day"]],
            edgecolor="none")
axes[1].set_title("Daily Stay Distribution", color="white", fontsize=11)
axes[1].set_xlabel("Day", color="white")
axes[1].set_ylabel("# Stays", color="white")
axes[1].tick_params(colors="white", axis="x", rotation=30)
for sp in axes[1].spines.values(): sp.set_color("#333")

top_acts = stays["activity"].value_counts().head(5).index
hourly_top = hourly_act[[c for c in top_acts if c in hourly_act.columns]]
hourly_top.plot.area(ax=axes[2], alpha=0.75, colormap="tab10")
axes[2].set_title("Activity Type by Hour", color="white", fontsize=11)
axes[2].set_xlabel("Hour of day", color="white")
axes[2].set_ylabel("# Stays", color="white")
axes[2].tick_params(colors="white")
axes[2].legend(fontsize=7, facecolor="#1a1a2e", labelcolor="white")
for sp in axes[2].spines.values(): sp.set_color("#333")

plt.suptitle("Stay-Point Activity Profiles — GLA Sample (Nov 2021)",
             color="white", fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig(f"{OUT}/17_temporal_profiles.png", dpi=180,
            bbox_inches="tight", facecolor="#0d1117")
plt.close()

# work vs all-activity flow overlap
merged = work_od[["origin","destination","flow"]].merge(
    all_od[["origin","destination","flow"]], on=["origin","destination"],
    suffixes=("_work","_all"))
merged["work_frac"] = merged["flow_work"] / merged["flow_all"].replace(0, np.nan)

fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.patch.set_facecolor("#0d1117")
for ax in axes:
    ax.set_facecolor("#1a1a2e")

axes[0].scatter(merged["flow_all"], merged["flow_work"],
                alpha=0.15, s=5, c="#f7b731")
axes[0].set_xlabel("All-activity flow", color="white")
axes[0].set_ylabel("Work flow", color="white")
axes[0].set_title("Work vs All-Activity Flows (per corridor)", color="white", fontsize=11)
axes[0].tick_params(colors="white")
for sp in axes[0].spines.values(): sp.set_color("#333")
rho, _ = spearmanr(merged["flow_all"], merged["flow_work"])
axes[0].text(0.97, 0.05, f"Spearman ρ = {rho:.3f}",
             transform=axes[0].transAxes, ha="right", color="white", fontsize=9)

axes[1].hist(merged["work_frac"].dropna(), bins=60, color="#a55eea", edgecolor="none", alpha=0.8)
axes[1].set_xlabel("Work fraction of total flow", color="white")
axes[1].set_ylabel("# Corridors", color="white")
axes[1].set_title("Work-Trip Share per O-D Pair", color="white", fontsize=11)
axes[1].tick_params(colors="white")
for sp in axes[1].spines.values(): sp.set_color("#333")

plt.suptitle("Work Trips vs All-Activity Flows", color="white", fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig(f"{OUT}/18_work_vs_all.png", dpi=180, bbox_inches="tight", facecolor="#0d1117")
plt.close()

print("Task 4 done → outputs/13–18")
