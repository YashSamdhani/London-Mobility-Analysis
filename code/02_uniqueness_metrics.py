import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import entropy as shannon
import os, warnings
warnings.filterwarnings("ignore")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
OUT = os.path.join(SCRIPT_DIR, "outputs")
os.makedirs(OUT, exist_ok=True)

work_od = pd.read_csv(os.path.join(DATA_DIR, "MSOA_county_home_work.csv"))
all_od  = pd.read_csv(os.path.join(DATA_DIR, "msoa_ODs_allactivity.csv"))
stays   = pd.read_csv(os.path.join(DATA_DIR, "trajectory_GLA_sample5000_updated.csv"))
stays   = stays.rename(columns={"userid": "uid", "loc_msoa": "msoa"})

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

# 1. Shannon entropy per origin — how spread out are a zone's destinations?
def zone_entropy(g):
    p = g["flow"].values / g["flow"].sum()
    return shannon(p, base=2)

ent_work = work_od.groupby("origin").apply(zone_entropy).reset_index()
ent_work.columns = ["msoa", "entropy_work"]
ent_all = all_od.groupby("origin").apply(zone_entropy).reset_index()
ent_all.columns = ["msoa", "entropy_all"]
ent = ent_work.merge(ent_all, on="msoa")

# 2. Gini — inequality of flow distribution
def gini(vals):
    v = np.sort(vals.astype(float))
    n = len(v)
    cumv = np.cumsum(v)
    return (n + 1 - 2 * np.sum(cumv) / cumv[-1]) / n if cumv[-1] > 0 else np.nan

gini_work = work_od.groupby("origin")["flow"].apply(gini).reset_index()
gini_work.columns = ["msoa", "gini"]
print(f"Median Gini (work): {gini_work['gini'].median():.3f}")

# 3. Flow asymmetry — net exporter vs net importer
out_f = work_od.groupby("origin")["flow"].sum()
in_f  = work_od.groupby("destination")["flow"].sum()
asym  = pd.DataFrame({"out": out_f, "in": in_f}).fillna(0)
asym["asymmetry"] = (asym["out"] - asym["in"]).abs() / (asym["out"] + asym["in"]).replace(0, np.nan)
asym  = asym["asymmetry"].rename_axis("msoa").reset_index()

# 4. HHI — flow concentration (1 = all trips go to a single destination)
def hhi(g):
    s = g["flow"] / g["flow"].sum()
    return (s ** 2).sum()

hhi_work = work_od.groupby("origin").apply(hhi).reset_index()
hhi_work.columns = ["msoa", "hhi"]
print(f"Median HHI (work): {hhi_work['hhi'].median():.4f}")

# 5. Location quotient — zones attracting more work trips than general activity
lq_num = work_od.groupby("destination")["flow"].sum() / work_od["flow"].sum()
lq_den = all_od.groupby("destination")["flow"].sum() / all_od["flow"].sum()
lq = (lq_num / lq_den.replace(0, np.nan)).rename_axis("msoa").reset_index()
lq.columns = ["msoa", "lq"]
print(f"LQ > 1 (work attractors): {(lq['lq'] > 1).sum()} / {len(lq)} zones")

# 6. Mobility range — unique MSOAs visited per user (proxy for radius of gyration)
mob = stays.groupby("uid")["msoa"].nunique().reset_index(name="n_zones")
print(f"Median unique zones per user: {mob['n_zones'].median():.0f}")

# 7. Work-trip share of total flow
flow_merge = work_od[["origin","destination","flow"]].merge(
    all_od[["origin","destination","flow"]], on=["origin","destination"],
    suffixes=("_work","_all"))
flow_merge["work_share"] = flow_merge["flow_work"] / flow_merge["flow_all"].replace(0, np.nan)
print(f"Median work share of all-activity flow: {flow_merge['work_share'].median():.3f}")

# combine and save
metrics = (ent
           .merge(gini_work, on="msoa")
           .merge(hhi_work,  on="msoa")
           .merge(lq,        on="msoa")
           .merge(asym,      on="msoa"))
metrics.to_csv(f"{OUT}/04_uniqueness_metrics.csv", index=False)
print(f"Metrics table saved — {len(metrics)} zones")

# distributions of all six metrics
cols = ["entropy_work", "entropy_all", "gini", "hhi", "lq", "asymmetry"]
fig, axes = plt.subplots(2, 3, figsize=(18, 11))
fig.patch.set_facecolor("#0d1117")
axes = axes.flatten()
palette = ["#ff6b35","#f7c59f","#efefd0","#004e89","#1a936f","#88d498"]

for ax, col, color in zip(axes, cols, palette):
    ax.set_facecolor("#1a1a2e")
    data = metrics[col].dropna()
    ax.hist(data, bins=60, color=color, edgecolor="none", alpha=0.85)
    ax.axvline(data.median(), color="white", linestyle="--", linewidth=1.2,
               label=f"median {data.median():.3f}")
    ax.set_title(col.replace("_", " ").title(), color="white", fontsize=11)
    ax.set_xlabel("Value", color="#aaa")
    ax.set_ylabel("# Zones", color="#aaa")
    ax.tick_params(colors="#888")
    ax.legend(fontsize=8, labelcolor="white", facecolor="#0d1117")
    for sp in ax.spines.values(): sp.set_color("#333")

plt.suptitle("O-D Uniqueness Metrics — MSOA Zone Distributions",
             color="white", fontsize=14, y=1.02)
plt.tight_layout()
plt.savefig(f"{OUT}/05_metric_distributions.png", dpi=180,
            bbox_inches="tight", facecolor="#0d1117")
plt.close()

# entropy vs gini scatter
fig, ax = plt.subplots(figsize=(10, 8))
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#1a1a2e")
sc = metrics[["entropy_work", "gini"]].dropna()
ax.scatter(sc["entropy_work"], sc["gini"],
           alpha=0.35, s=12, c=sc["entropy_work"], cmap="plasma")
ax.set_xlabel("Shannon Entropy (bits)", color="white", fontsize=12)
ax.set_ylabel("Gini Coefficient", color="white", fontsize=12)
ax.set_title("Entropy vs Gini per Origin Zone (work trips)", color="white", fontsize=13)
ax.tick_params(colors="white")
for sp in ax.spines.values(): sp.set_color("#333")
ax.text(0.02, 0.97, "Low entropy / Low Gini\n(balanced local flows)",
        transform=ax.transAxes, color="#aaa", va="top", fontsize=8)
ax.text(0.73, 0.97, "High entropy / Low Gini\n(diverse but balanced)",
        transform=ax.transAxes, color="#aaa", va="top", fontsize=8)
ax.text(0.02, 0.18, "Low entropy / High Gini\n(single dominant destination)",
        transform=ax.transAxes, color="#aaa", va="top", fontsize=8)
plt.tight_layout()
plt.savefig(f"{OUT}/06_entropy_vs_gini.png", dpi=180,
            bbox_inches="tight", facecolor="#0d1117")
plt.close()

# mobility range per user
fig, ax = plt.subplots(figsize=(10, 5))
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#1a1a2e")
ax.hist(mob["n_zones"], bins=80, color="#1a936f", edgecolor="none", alpha=0.85)
ax.axvline(mob["n_zones"].median(), color="white", linestyle="--",
           label=f"median {mob['n_zones'].median():.0f} zones")
ax.set_xlabel("Unique MSOAs visited per user", color="white", fontsize=12)
ax.set_ylabel("# Users", color="white", fontsize=12)
ax.set_title("Individual Mobility Range — GLA Sample (5000 users)", color="white", fontsize=12)
ax.tick_params(colors="white")
ax.legend(facecolor="#0d1117", labelcolor="white")
for sp in ax.spines.values(): sp.set_color("#333")
plt.tight_layout()
plt.savefig(f"{OUT}/07_mobility_range.png", dpi=180,
            bbox_inches="tight", facecolor="#0d1117")
plt.close()

print("Task 2 done → outputs/04–07")
