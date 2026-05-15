import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os, warnings
warnings.filterwarnings("ignore")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
OUT = os.path.join(SCRIPT_DIR, "outputs")
os.makedirs(OUT, exist_ok=True)

stays = pd.read_csv(os.path.join(DATA_DIR, "trajectory_GLA_sample5000_updated.csv"))
stays = stays.rename(columns={
    "userid": "uid", "start_time": "t_start", "end_time": "t_end",
    "duration": "duration", "loc_msoa": "msoa", "activity": "activity",
})
stays["t_start"] = pd.to_datetime(stays["t_start"], errors="coerce")
stays["t_end"]   = pd.to_datetime(stays["t_end"],   errors="coerce")
stays["hour"] = stays["t_start"].dt.hour
stays["dow"]  = stays["t_start"].dt.day_name()

print(f"{stays['uid'].nunique():,} users, {len(stays):,} stays — {stays['activity'].unique()}")

work_od = pd.read_csv(os.path.join(DATA_DIR, "MSOA_county_home_work.csv"))
all_od  = pd.read_csv(os.path.join(DATA_DIR, "msoa_ODs_allactivity.csv"))

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

# activity dashboard — 4 panels
ACT_COLOURS = {
    "Home": "#4ecdc4", "Work": "#ff6b35", "Shopping_1": "#f7b731",
    "Shopping_2": "#f7b731", "Other": "#a55eea", "Leisure": "#26de81",
    "Education": "#fd9644", "Unknown": "#888888",
}
def act_col(name):
    for k, v in ACT_COLOURS.items():
        if k.lower() in str(name).lower():
            return v
    return "#aaaaaa"

act_counts = stays["activity"].value_counts()
act_dur    = stays.groupby("activity")["duration"].median().sort_values(ascending=False)
hourly     = stays.groupby(["hour", "activity"]).size().unstack(fill_value=0)
dow_order  = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
dow_counts = stays.groupby("dow")["uid"].count().reindex(dow_order)

fig, axes = plt.subplots(2, 2, figsize=(18, 12))
fig.patch.set_facecolor("#0d1117")
for ax in axes.flatten():
    ax.set_facecolor("#1a1a2e")

ax = axes[0, 0]
ax.barh(act_counts.index, act_counts.values,
        color=[act_col(a) for a in act_counts.index], edgecolor="none")
for i, v in enumerate(act_counts.values):
    ax.text(v + 50, i, f"{v:,}", va="center", color="white", fontsize=8)
ax.set_title("Stay Count by Activity", color="white", fontsize=12)
ax.set_xlabel("# Stays", color="white")
ax.tick_params(colors="white")
for sp in ax.spines.values(): sp.set_color("#333")

ax = axes[0, 1]
ax.barh(act_dur.index, act_dur.values,
        color=[act_col(a) for a in act_dur.index], edgecolor="none")
ax.set_title("Median Stay Duration by Activity (min)", color="white", fontsize=12)
ax.set_xlabel("Median duration (min)", color="white")
ax.tick_params(colors="white")
for sp in ax.spines.values(): sp.set_color("#333")

ax = axes[1, 0]
hourly_norm = hourly.div(hourly.sum(axis=1), axis=0).fillna(0)
im = ax.imshow(hourly_norm.T, aspect="auto", cmap="magma",
               extent=[-0.5, 23.5, -0.5, len(hourly_norm.columns) - 0.5])
ax.set_yticks(range(len(hourly_norm.columns)))
ax.set_yticklabels(hourly_norm.columns, fontsize=7, color="white")
ax.set_xticks(range(0, 24, 2))
ax.set_xticklabels(range(0, 24, 2), color="white", fontsize=8)
ax.set_xlabel("Hour of day", color="white")
ax.set_title("Activity Mix by Hour (normalised)", color="white", fontsize=12)
plt.colorbar(im, ax=ax, label="Share")

ax = axes[1, 1]
ax.bar(dow_counts.index, dow_counts.values,
       color=["#ff6b35" if d in ("Saturday","Sunday") else "#4ecdc4"
              for d in dow_counts.index],
       edgecolor="none")
ax.set_title("Stay Volume by Day of Week", color="white", fontsize=12)
ax.set_xlabel("Day", color="white")
ax.set_ylabel("# Stays", color="white")
ax.tick_params(colors="white", axis="x", rotation=30)
for sp in ax.spines.values(): sp.set_color("#333")

plt.suptitle("Stay-Point Activity Analysis — GLA Sample (Nov 2021)",
             color="white", fontsize=14, y=1.01)
plt.tight_layout()
plt.savefig(f"{OUT}/01_activity_dashboard.png", dpi=180,
            bbox_inches="tight", facecolor="#0d1117")
plt.close()

# activity sequence transition matrix
stays_s = stays.sort_values(["uid", "t_start"])
stays_s["next_act"] = stays_s.groupby("uid")["activity"].shift(-1)
trans = (stays_s.dropna(subset=["next_act"])
         .groupby(["activity", "next_act"]).size()
         .reset_index(name="count"))
top_acts = act_counts.head(8).index.tolist()
trans_mat = (trans[trans["activity"].isin(top_acts) & trans["next_act"].isin(top_acts)]
             .pivot(index="activity", columns="next_act", values="count")
             .fillna(0))

fig, ax = plt.subplots(figsize=(12, 9))
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#1a1a2e")
sns.heatmap(trans_mat.astype(int), annot=True, fmt="d", cmap="YlOrRd",
            linewidths=0.5, linecolor="#333", ax=ax,
            cbar_kws={"label": "Transition count"})
ax.set_title("Activity Transition Matrix", color="white", fontsize=12, pad=10)
ax.set_xlabel("Next activity", color="white")
ax.set_ylabel("Current activity", color="white")
ax.tick_params(colors="white")
plt.tight_layout()
plt.savefig(f"{OUT}/02_activity_transitions.png", dpi=180,
            bbox_inches="tight", facecolor="#0d1117")
plt.close()

# OD flow matrix — top 50 origin zones
top_zones = work_od.groupby("origin")["flow"].sum().nlargest(50).index.tolist()
matrix = (work_od[work_od["origin"].isin(top_zones) & work_od["destination"].isin(top_zones)]
          .pivot_table(index="origin", columns="destination",
                       values="flow", aggfunc="sum", fill_value=0))

fig, ax = plt.subplots(figsize=(16, 14))
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#0d1117")
sns.heatmap(np.log1p(matrix), cmap="magma", linewidths=0, ax=ax,
            cbar_kws={"label": "log(1 + flow)"})
ax.set_title("O-D Flow Matrix — Top 50 Origin Zones (log scale)",
             color="white", fontsize=13, pad=10)
ax.set_xlabel("Destination MSOA", color="white")
ax.set_ylabel("Origin MSOA", color="white")
ax.tick_params(colors="white", labelsize=6)
plt.tight_layout()
plt.savefig(f"{OUT}/03_od_matrix.png", dpi=180,
            bbox_inches="tight", facecolor="#0d1117")
plt.close()

print("Task 1 done → outputs/01–03")
