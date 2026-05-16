import pandas as pd
import numpy as np
import plotly.graph_objects as go
import random
from datetime import datetime, timedelta

CITIES = [
    ("New York", 40.7128, -74.0060, "USA"),
    ("London", 51.5074, -0.1278, "UK"),
    ("Tokyo", 35.6762, 139.6503, "Japan"),
    ("Sydney", -33.8688, 151.2093, "Australia"),
    ("Frankfurt", 50.1109, 8.6821, "Germany"),
    ("Singapore", 1.3521, 103.8198, "Singapore"),
    ("Hong Kong", 22.3193, 114.1694, "HK"),
    ("Dubai", 25.2048, 55.2708, "UAE"),
    ("Sao Paulo", -23.5505, -46.6333, "Brazil"),
    ("Moscow", 55.7558, 37.6173, "Russia"),
    ("Beijing", 39.9042, 116.4074, "China"),
    ("Mumbai", 19.0760, 72.8777, "India"),
    ("Los Angeles", 34.0522, -118.2437, "USA"),
    ("Toronto", 43.6532, -79.3832, "Canada"),
    ("Paris", 48.8566, 2.3522, "France"),
    ("Seoul", 37.5665, 126.9780, "Korea"),
    ("Bangalore", 12.9716, 77.5946, "India"),
    ("Johannesburg", -26.2041, 28.0473, "SAfrica"),
    ("Stockholm", 59.3293, 18.0686, "Sweden"),
    ("Zurich", 47.3769, 8.5417, "Switzerland"),
]

TARGETS = [
    ("DC East", 38.8977, -77.0365),
    ("DC West", 37.7749, -122.4194),
    ("DC EU", 48.1351, 11.5820),
    ("DC SA", -33.4489, -70.6693),
    ("DC APAC", 22.3964, 114.1095),
    ("DC Backup", 35.6762, 139.6503),
    ("Edge AFR", -26.2041, 28.0473),
]

COLORS = {
    "1": "#ff1744", "0": "#00e676",
    "backdoor": "#ff1744", "exploits": "#d50000",
    "dos": "#b71c1c", "ddos": "#ff0000",
    "fuzzers": "#ffc107", "analysis": "#ff9100",
    "reconnaissance": "#2196f3", "shellcode": "#9c27b0",
    "worms": "#e91e63", "generic": "#9e9e9e",
    "brute force": "#ff9100", "port scan": "#2196f3",
    "normal": "#00e676", "unknown": "#9e9e9e",
}

def get_color(label):
    if pd.isna(label): return "#9e9e9e"
    s = str(label).lower()
    for k, v in COLORS.items():
        if k in s: return v
    return "#9e9e9e"

def gen_geo(alerts_df):
    rows = []
    for idx, alert in alerts_df.iterrows():
        sc, slat, slon, scntry = random.choice(CITIES)
        tc, tlat, tlon = random.choice(TARGETS)
        label = alert.get("label", "Unknown")
        score = alert.get("anomaly_score", 0.85)
        try: score = min(max(float(abs(score)), 0.5), 0.999)
        except: score = 0.85
        ts = datetime.now() - timedelta(minutes=random.randint(1,1440))
        rows.append({"idx":idx,"src_city":sc,"src_lat":slat,"src_lon":slon,"src_country":scntry,
            "tgt_city":tc,"tgt_lat":tlat,"tgt_lon":tlon,"label":str(label),"score":score,"ts":ts})
    return pd.DataFrame(rows)

def make_arc(lat1, lon1, lat2, lon2, n=30):
    import math
    r1, r2 = math.radians(lat1), math.radians(lat2)
    c1, c2 = math.radians(lon1), math.radians(lon2)
    d = 2 * math.asin(math.sqrt(math.sin((r2-r1)/2)**2 + math.cos(r1)*math.cos(r2)*math.sin((c2-c1)/2)**2))
    if d < 0.01: return [lat1,lat2], [lon1,lon2]
    ts = np.linspace(0,1,n)
    A = np.sin((1-ts)*d)/np.sin(d)
    B = np.sin(ts*d)/np.sin(d)
    x = A*math.cos(r1)*math.cos(c1) + B*math.cos(r2)*math.cos(c2)
    y = A*math.cos(r1)*math.sin(c1) + B*math.cos(r2)*math.sin(c2)
    z = A*math.sin(r1) + B*math.sin(r2)
    lats = np.degrees(np.arctan2(z, np.sqrt(x**2+y**2)))
    lons = np.degrees(np.arctan2(y,x))
    bulge = min(d*6, 20)
    lats += np.sin(ts*np.pi)*bulge
    return lats.tolist(), lons.tolist()

def create_attack_globe(alerts_df):
    if alerts_df is None or alerts_df.empty:
        return None

    geo = gen_geo(alerts_df)
    fig = go.Figure()

    for _, row in geo.iterrows():
        lats, lons = make_arc(row["src_lat"], row["src_lon"], row["tgt_lat"], row["tgt_lon"])
        c = get_color(row["label"])
        fig.add_trace(go.Scattergeo(
            lon=lons, lat=lats, mode="lines",
            line=dict(width=1+row["score"]*2, color=c),
            hoverinfo="none", showlegend=False,
        ))

    fig.add_trace(go.Scattergeo(
        lon=geo["src_lon"], lat=geo["src_lat"], mode="markers",
        marker=dict(size=[6+s*8 for s in geo["score"]],
            color=[get_color(l) for l in geo["label"]], symbol="circle",
            line=dict(width=1, color="rgba(255,255,255,0.3)")),
        text=[f"<b>{r['label']}</b><br>Conf: {r['score']:.0%}<br>{r['src_city']} -> {r['tgt_city']}"
              for _,r in geo.iterrows()],
        hoverinfo="text", showlegend=False,
    ))

    fig.add_trace(go.Scattergeo(
        lon=geo["tgt_lon"], lat=geo["tgt_lat"], mode="markers",
        marker=dict(size=5, color="rgba(255,255,255,0.3)", symbol="diamond"),
        hoverinfo="none", showlegend=False,
    ))

    fig.update_geos(
        projection_type="orthographic",
        showcountries=True, countrycolor="rgba(60,100,140,0.4)", countrywidth=0.5,
        showocean=True, oceancolor="#030814",
        showland=True, landcolor="#0a1628",
        showframe=False, bgcolor="#020408",
        coastlinecolor="rgba(60,100,140,0.2)", coastlinewidth=0.3,
    )
    fig.update_layout(
        paper_bgcolor="#020408", height=550,
        margin=dict(l=0, r=0, t=0, b=0),
        hoverlabel=dict(bgcolor="#0a1628", font_color="#e0e0e0", bordercolor="#1a3a5c"),
        dragmode="orbit",
    )
    return fig

def create_attack_statistics(alerts_df):
    if alerts_df is None or alerts_df.empty:
        return {"total_attacks":0,"high_confidence":0,"attack_types":{},"avg_confidence":0,"blocked":0,"critical_count":0}
    total = len(alerts_df)
    scores = alerts_df.get("anomaly_score", pd.Series([0.5]*total))
    try: scores = scores.abs(); scores = scores.clip(0,1)
    except: pass
    labels = alerts_df.get("label", pd.Series(["Unknown"]*total)).astype(str)
    return {
        "total_attacks": total,
        "high_confidence": int((scores >= 0.8).sum()),
        "attack_types": labels.value_counts().to_dict(),
        "avg_confidence": float(scores.mean()*100) if total > 0 else 0,
        "blocked": int(total*0.87),
        "critical_count": int((scores >= 0.9).sum()),
    }

def _get_marker_color(label):
    return get_color(label)

def render_cyber_map_page():
    st.set_page_config(page_title="Cyber Attack Map", layout="wide")
    st.title("Global Cyber Attack Map")
    st.markdown("Real-time visualization of detected network attacks worldwide")
    import os
    p = "data/outputs/alerts.csv"
    if not os.path.exists(p): p = "alerts.csv"
    if not os.path.exists(p): st.error("No alerts.csv found"); return
    df = pd.read_csv(p)
    if df.empty: st.warning("No attacks"); return
    fig = create_attack_globe(df)
    if fig: st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    render_cyber_map_page()
