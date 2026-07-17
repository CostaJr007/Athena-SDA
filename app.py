"""
Athena-SDA — Space Domain Awareness Copilot
Dashboard Streamlit: Globe.gl + pipeline ML + copiloto Bob (IBM Granite / local).
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from src.bob import answer_operator_query
from src.models import load_models, train_and_save_models
from src.pipeline import build_demo_constellation, process_constellation, process_to_dataframe

# Optional .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(page_title="Athena-SDA | Space Domain Awareness Copilot", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
    .stApp { background: #0a0a0f !important; color: #e1e1e1; font-family: 'Inter', sans-serif !important; }
    .block-container { padding-top: 1rem !important; padding-bottom: 0 !important; max-width: 100% !important; }
    h1, h2, h3, h4, h5, h6 { font-family: 'Outfit', 'Inter', sans-serif !important; color: #e1e1e1 !important; font-weight: 600 !important; letter-spacing: 0.02em; }
    .main-title {
        background: linear-gradient(135deg, #00d4ff 0%, #0099cc 50%, #006688 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-size: 2.4rem !important; font-weight: 800; font-family: 'Outfit', sans-serif !important; margin-bottom: 0; letter-spacing: 0.08em;
    }
    .sub-title { color: #8e8e93; font-size: 0.95rem; margin-bottom: 1.5rem; letter-spacing: 0.04em; }
    .glass-card {
        background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 10px; padding: 1.2rem; margin-bottom: 0.8rem;
        backdrop-filter: blur(16px); box-shadow: 0 2px 20px rgba(0, 0, 0, 0.5);
    }
    .alert-card-red { border-left: 3px solid #ff2d55 !important; background: rgba(255, 45, 85, 0.06) !important; }
    .alert-card-orange { border-left: 3px solid #ff6b35 !important; background: rgba(255, 107, 53, 0.06) !important; }
    .alert-card-yellow { border-left: 3px solid #ffd60a !important; background: rgba(255, 214, 10, 0.04) !important; }
    .stTextInput>div>div>input {
        background-color: rgba(255, 255, 255, 0.04) !important; color: #e1e1e1 !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important; border-radius: 8px !important;
    }
    .stButton>button {
        background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%) !important;
        color: #0a0a0f !important; border: none !important; border-radius: 8px !important; font-weight: 600 !important;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 0px; background: rgba(255, 255, 255, 0.02); border-radius: 8px; padding: 4px; }
    .stTabs [data-baseweb="tab"] { font-size: 0.85rem; font-weight: 500; color: #8e8e93; padding: 8px 20px; border-radius: 6px; }
    .stTabs [aria-selected="true"] { background: rgba(0, 212, 255, 0.1) !important; color: #00d4ff !important; }
    [data-testid="stSidebar"] { background: #07070b !important; border-right: 1px solid rgba(255, 255, 255, 0.04); }
    [data-testid="stMetric"] { background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 8px; padding: 12px !important; }
    [data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace !important; color: #00d4ff !important; }
    [data-testid="stChatMessage"] { background: rgba(255, 255, 255, 0.02) !important; border: 1px solid rgba(255, 255, 255, 0.04) !important; border-radius: 8px !important; }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
    .section-divider { border-top: 1px solid rgba(255,255,255,0.04); margin: 1.5rem 0; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def init_ml_models():
    return load_models()


@st.cache_data
def get_constellation():
    return build_demo_constellation()


@st.cache_data
def run_pipeline(_iforest, _xgb, _rkhs):
    all_sats = get_constellation()
    processed = process_constellation(all_sats, _iforest, _xgb, _rkhs)
    return processed


def get_flag(country_code: str) -> str:
    flags = {
        "US": "🇺🇸", "CN": "🇨🇳", "RU": "🇷🇺", "BR": "🇧🇷",
        "FR": "🇫🇷", "EU": "🇪🇺", "UK": "🇬🇧", "IN": "🇮🇳",
        "JP": "🇯🇵", "KR": "🇰🇷", "IL": "🇮🇱", "DE": "🇩🇪",
    }
    return flags.get(str(country_code).upper(), "🌐")


color_map = {
    "NORMAL": "#30d158",
    "ANÔMALO": "#ffd60a",
    "SUSPEITO": "#ff6b35",
    "HOSTIL": "#ff2d55",
}

# --- Load models & process ---
iforest, xgb_model, rkhs_ref, train_metrics = init_ml_models()
all_sats = get_constellation()
processed_sats = run_pipeline(iforest, xgb_model, rkhs_ref)
df_sats = process_to_dataframe(processed_sats)
processed_by_id = {p["id"]: p for p in processed_sats}

# Rebuild features dict access for Bob (stored on processed list)
for p in processed_sats:
    processed_by_id[p["id"]] = p

hostis = int((df_sats["classification"] == "HOSTIL").sum())
suspeitos = int((df_sats["classification"] == "SUSPEITO").sum())
anomalos = int((df_sats["classification"] == "ANÔMALO").sum())
normais = int(len(df_sats) - hostis - suspeitos - anomalos)

# --- Header ---
st.markdown("<div class='main-title'>ATHENA-SDA</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='sub-title'>Space Domain Awareness Copilot — Isolation Forest → XGBoost → Fuzzy → Bob (IBM watsonx.ai / Granite)</div>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### 📡 STATUS ORBITAL")
    st.metric("Objetos no catálogo demo", len(df_sats))
    st.caption("Demo curada + física aproximada. Escala de produção usaria o catálogo Space-Track completo.")
    st.markdown(f"""
    <div class='glass-card' style='padding: 0.8rem;'>
        <div style='display:flex; justify-content:space-between; margin-bottom:6px;'>
            <span style='color:#ff2d55;'>● HOSTIL</span>
            <span style='font-family:JetBrains Mono,monospace; color:#ff2d55;'>{hostis}</span>
        </div>
        <div style='display:flex; justify-content:space-between; margin-bottom:6px;'>
            <span style='color:#ff6b35;'>● SUSPEITO</span>
            <span style='font-family:JetBrains Mono,monospace; color:#ff6b35;'>{suspeitos}</span>
        </div>
        <div style='display:flex; justify-content:space-between; margin-bottom:6px;'>
            <span style='color:#ffd60a;'>● ANÔMALO</span>
            <span style='font-family:JetBrains Mono,monospace; color:#ffd60a;'>{anomalos}</span>
        </div>
        <div style='display:flex; justify-content:space-between;'>
            <span style='color:#30d158;'>● NORMAL</span>
            <span style='font-family:JetBrains Mono,monospace; color:#30d158;'>{normais}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### ⚙️ IBM WATSONX.AI")
    api_key_input = st.text_input("API Key", value=os.environ.get("WATSONX_APIKEY", ""), type="password")
    project_id_input = st.text_input("Project ID", value=os.environ.get("WATSONX_PROJECT_ID", ""))
    if api_key_input and project_id_input:
        os.environ["WATSONX_APIKEY"] = api_key_input
        os.environ["WATSONX_PROJECT_ID"] = project_id_input
        st.success("✓ Credenciais ativas (sessão)")
    else:
        st.info("Sem API: Bob usa briefing local (offline).")

    if train_metrics:
        st.markdown("### 📊 Último treino")
        st.caption(
            f"n={train_metrics.get('n_samples', '?')} | "
            f"acc={train_metrics.get('accuracy_test', 0):.2%} | "
            f"logloss={train_metrics.get('log_loss_test', float('nan')):.3f}"
        )

tab1, tab2, tab3 = st.tabs(["🚀 Dashboard Tático", "🧠 Model Insights", "📖 Glossário"])

# ====================================================================
# TAB 1 — DASHBOARD
# ====================================================================
with tab1:
    sat_data_for_globe = []
    for _, row in df_sats.iterrows():
        sat_id = int(row["id"])
        hist_df = all_sats[sat_id]["history"]
        color = color_map.get(row["classification"], "#30d158")
        is_hostile = row["classification"] in ("HOSTIL", "SUSPEITO")
        sat_data_for_globe.append({
            "name": row["name"],
            "sma": float(hist_df["semi_major_axis_km"].values[-1]),
            "inc": float(hist_df["inclination_deg"].iloc[0]),
            "raan": float(hist_df["raan_deg"].iloc[0]),
            "mean_motion": float(hist_df["mean_motion_rev_per_day"].values[-1]),
            "color": color,
            "classification": row["classification"],
            "country": row["country"],
            "purpose": row["purpose"],
            "orbit": row["orbit"],
            "threat": float(row["threat_level"]),
            "confidence": float(row["confidence"]),
            "is_hostile": is_hostile,
            "initial_anomaly": float(np.random.default_rng(sat_id).uniform(0, 2 * np.pi)),
        })

    globe_html = """
    <html>
    <head>
      <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Inter:wght@300;400;500&display=swap" rel="stylesheet">
      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { overflow: hidden; background: #0a0a0f; font-family: 'Inter', sans-serif; }
        #globeViz { width: 100%; height: 100vh; }
        .hud-counter { position: absolute; top: 16px; right: 20px; z-index: 100; text-align: right; }
        .hud-counter .count { font-family: 'JetBrains Mono', monospace; font-size: 32px; font-weight: 500; color: #00d4ff; }
        .hud-counter .label { font-size: 10px; color: rgba(255,255,255,0.3); letter-spacing: 0.15em; text-transform: uppercase; }
        .hud-title { position: absolute; top: 16px; left: 20px; z-index: 100; }
        .hud-title .name { font-size: 14px; font-weight: 500; color: rgba(255,255,255,0.5); letter-spacing: 0.08em; }
        .hud-title .status { font-size: 10px; color: #30d158; letter-spacing: 0.12em; text-transform: uppercase; margin-top: 3px; }
        .hud-title .status::before {
            content: ''; display: inline-block; width: 6px; height: 6px; background: #30d158;
            border-radius: 50%; margin-right: 6px; animation: pulse-dot 2s ease-in-out infinite;
        }
        @keyframes pulse-dot { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
        .sat-tooltip {
            position: absolute; display: none; z-index: 200; background: rgba(10, 10, 15, 0.85);
            backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;
            padding: 12px 16px; pointer-events: none; min-width: 220px;
        }
        .sat-tooltip .tt-name { font-size: 13px; font-weight: 600; color: #e1e1e1; margin-bottom: 6px; }
        .sat-tooltip .tt-row { display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 3px; }
        .sat-tooltip .tt-label { color: rgba(255,255,255,0.4); }
        .sat-tooltip .tt-value { font-family: 'JetBrains Mono', monospace; color: #e1e1e1; }
        .sat-tooltip .tt-bar { height: 3px; background: rgba(255,255,255,0.06); border-radius: 2px; margin-top: 6px; overflow: hidden; }
        .sat-tooltip .tt-bar-fill { height: 100%; border-radius: 2px; }
        .loading-overlay {
            position: absolute; inset: 0; background: #0a0a0f; display: flex; flex-direction: column;
            align-items: center; justify-content: center; z-index: 500; transition: opacity 0.8s ease;
        }
        .loading-overlay.hidden { opacity: 0; pointer-events: none; }
        .loading-spinner {
            width: 40px; height: 40px; border: 2px solid rgba(255,255,255,0.06);
            border-top-color: #00d4ff; border-radius: 50%; animation: spin 1s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loading-text { margin-top: 16px; font-size: 11px; color: rgba(255,255,255,0.3); letter-spacing: 0.15em; text-transform: uppercase; }
      </style>
      <script src="https://unpkg.com/globe.gl@2.35.1"></script>
    </head>
    <body>
      <div class="loading-overlay" id="loader"><div class="loading-spinner"></div><div class="loading-text">Carregando órbitas...</div></div>
      <div class="hud-title"><div class="name">ATHENA-SDA</div><div class="status">Pipeline ML ativo</div></div>
      <div class="hud-counter"><div class="count">__SAT_COUNT__</div><div class="label">Objetos rastreados</div></div>
      <div class="sat-tooltip" id="tooltip"></div>
      <div id="globeViz"></div>
      <script>
        const satData = __SAT_DATA_PLACEHOLDER__;
        const tooltip = document.getElementById('tooltip');
        const globe = Globe()(document.getElementById('globeViz'))
          .globeImageUrl('https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg')
          .bumpImageUrl('https://unpkg.com/three-globe/example/img/earth-topology.png')
          .backgroundImageUrl('https://unpkg.com/three-globe/example/img/night-sky.png')
          .backgroundColor('#0a0a0f').showAtmosphere(true).atmosphereColor('#0099cc').atmosphereAltitude(0.18)
          .pointOfView({ lat: 20, lng: 0, altitude: 2.5 });
        globe.controls().autoRotate = true; globe.controls().autoRotateSpeed = 0.3;
        globe.controls().enableZoom = true; globe.controls().minDistance = 120; globe.controls().maxDistance = 600;
        globe.controls().enableDamping = true; globe.controls().dampingFactor = 0.1;

        function getOrbitalPos(sat, t) {
            const radPerSec = (sat.mean_motion * 2 * Math.PI) / 86400;
            const theta = (radPerSec * t * 150) + sat.initial_anomaly;
            const x_orb = sat.sma * Math.cos(theta); const y_orb = sat.sma * Math.sin(theta);
            const incRad = (sat.inc * Math.PI) / 180;
            const y_rot = y_orb * Math.cos(incRad); const z_rot = y_orb * Math.sin(incRad);
            const raanRad = (sat.raan * Math.PI) / 180;
            const x_final = x_orb * Math.cos(raanRad) - y_rot * Math.sin(raanRad);
            const y_final = x_orb * Math.sin(raanRad) + y_rot * Math.cos(raanRad);
            return { lat: Math.asin(z_rot / sat.sma) * (180 / Math.PI), lon: Math.atan2(y_final, x_final) * (180 / Math.PI), alt: (sat.sma - 6371) / 6371 };
        }
        function getOrbitPath(sat) {
            const path = [];
            for (let i = 0; i <= 120; i++) {
                const theta = (i / 120) * 2 * Math.PI;
                const x = sat.sma * Math.cos(theta); const y = sat.sma * Math.sin(theta);
                const incRad = (sat.inc * Math.PI) / 180;
                const yR = y * Math.cos(incRad); const zR = y * Math.sin(incRad);
                const raanRad = (sat.raan * Math.PI) / 180;
                const xF = x * Math.cos(raanRad) - yR * Math.sin(raanRad);
                const yF = x * Math.sin(raanRad) + yR * Math.cos(raanRad);
                path.push({ lat: Math.asin(zR / sat.sma) * (180 / Math.PI), lng: Math.atan2(yF, xF) * (180 / Math.PI), alt: (sat.sma - 6371) / 6371 });
            }
            return path;
        }
        const orbitPaths = satData.map(sat => ({ coords: getOrbitPath(sat), color: sat.is_hostile ? sat.color + '60' : sat.color + '25' }));
        globe.pathsData(orbitPaths).pathPoints('coords').pathPointLat(p => p.lat).pathPointLng(p => p.lng).pathPointAlt(p => p.alt)
          .pathColor('color').pathStroke(d => d.color.includes('ff2d55') || d.color.includes('ff6b35') ? 0.6 : 0.3)
          .pathDashLength(0.01).pathDashGap(0).pathDashAnimateTime(0);
        const hostileRings = satData.filter(s => s.is_hostile);
        satData.forEach(sat => { const p = getOrbitalPos(sat, 0); sat.lat = p.lat; sat.lng = p.lon; sat.alt = p.alt; sat.size = sat.is_hostile ? 0.6 : 0.35; });
        globe.pointsData(satData).pointLat('lat').pointLng('lng').pointAltitude('alt').pointColor('color').pointRadius('size').pointsMerge(true).pointResolution(8);
        globe.labelsData(satData).labelLat('lat').labelLng('lng').labelAltitude(d => d.alt + 0.01).labelText('name')
          .labelSize(d => d.is_hostile ? 0.6 : 0.4).labelDotRadius(0).labelColor(d => d.color + 'aa').labelResolution(2).labelIncludeDot(false);
        globe.ringsData(hostileRings).ringLat(d => d.lat || 0).ringLng(d => d.lng || 0).ringAltitude(d => d.alt || 0.05)
          .ringColor(d => d.color + '80').ringMaxRadius(2.5).ringPropagationSpeed(1.5).ringRepeatPeriod(2000);
        globe.onPointClick(d => globe.pointOfView({ lat: d.lat, lng: d.lng, altitude: Math.max(d.alt + 0.5, 0.8) }, 1200));
        globe.onPointHover(d => {
            if (d) {
                tooltip.style.display = 'block';
                const orbitAlt = ((d.sma - 6371)).toFixed(0);
                tooltip.innerHTML = `<div class="tt-name" style="color:${d.color}">${d.name}</div>
                    <div class="tt-row"><span class="tt-label">País</span><span class="tt-value">${d.country}</span></div>
                    <div class="tt-row"><span class="tt-label">Missão</span><span class="tt-value">${d.purpose}</span></div>
                    <div class="tt-row"><span class="tt-label">Órbita</span><span class="tt-value">${d.orbit} (${orbitAlt} km)</span></div>
                    <div class="tt-row"><span class="tt-label">Ameaça</span><span class="tt-value" style="color:${d.color}">${d.classification} (${(d.threat * 100).toFixed(0)}%)</span></div>
                    <div class="tt-bar"><div class="tt-bar-fill" style="width:${d.threat * 100}%; background:${d.color};"></div></div>`;
            } else { tooltip.style.display = 'none'; }
        });
        document.addEventListener('mousemove', e => {
            if (tooltip.style.display === 'block') { tooltip.style.left = (e.clientX + 16) + 'px'; tooltip.style.top = (e.clientY - 20) + 'px'; }
        });
        let startTime = Date.now();
        function animate() {
            const t = (Date.now() - startTime) / 1000;
            for (let i = 0; i < satData.length; i++) {
                const pos = getOrbitalPos(satData[i], t);
                satData[i].lat = pos.lat; satData[i].lng = pos.lon; satData[i].alt = pos.alt;
            }
            globe.pointsData(satData); globe.labelsData(satData); globe.ringsData(hostileRings);
            requestAnimationFrame(animate);
        }
        globe.onGlobeReady(() => { document.getElementById('loader').classList.add('hidden'); animate(); });
      </script>
    </body>
    </html>
    """.replace("__SAT_DATA_PLACEHOLDER__", json.dumps(sat_data_for_globe)).replace("__SAT_COUNT__", str(len(sat_data_for_globe)))

    components.html(globe_html, height=620)
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    alert_col, chat_col = st.columns([1.2, 1.0])

    with alert_col:
        st.markdown("### 🚨 ALERTAS ATIVOS")
        st.caption("Ordenados por Kelly (alocação de sensores). Scores = XGBoost + Fuzzy fundidos.")
        alertas = df_sats[df_sats["classification"] != "NORMAL"].sort_values(by="kelly_allocation", ascending=False)

        for _, row in alertas.iterrows():
            flag = get_flag(row["country"])
            target = row.get("closest_asset_name") or "—"
            if row["classification"] == "HOSTIL":
                card_class, badge, badge_color = "glass-card alert-card-red", "HOSTIL", "#ff2d55"
                diag = f"⚠️ Ameaça elevada / RPO<br><span style='color:#ff2d55'>🎯 Alvo: {target}</span>"
            elif row["classification"] == "SUSPEITO":
                card_class, badge, badge_color = "glass-card alert-card-orange", "SUSPEITO", "#ff6b35"
                diag = f"👁️ Comportamento anômalo persistente<br><span style='color:#ff6b35'>🎯 Possível alvo: {target}</span>"
            else:
                card_class, badge, badge_color = "glass-card alert-card-yellow", "ANÔMALO", "#ffd60a"
                diag = "🔍 Desvio da baseline Kepleriana (CUSUM/ADF)"

            xgb_c = row.get("xgb_class", "—")
            st.markdown(f"""
            <div class="{card_class}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:600; font-size:0.95rem;">{flag} {row['name']}</span>
                    <span style="font-family:'JetBrains Mono',monospace; font-size:0.75rem; color:{badge_color}; background:{badge_color}15; padding:2px 8px; border-radius:4px;">{badge}</span>
                </div>
                <div style="margin-top:6px; font-size:0.8rem; color:#8e8e93;">
                    {row['country']} · {row['purpose']} · {row['orbit']} · NORAD #{row['id']} · XGB:{xgb_c}
                </div>
                <div style="margin-top:6px; font-size:0.82rem; color:#e1e1e1;">{diag}</div>
                <div style="margin-top:8px; display:flex; gap:16px; font-size:0.78rem; color:#8e8e93;">
                    <span>Ameaça <span style="color:{badge_color}; font-family:'JetBrains Mono',monospace;">{row['threat_level']:.2f}</span></span>
                    <span>Conf <span style="color:#e1e1e1; font-family:'JetBrains Mono',monospace;">{row['confidence']*100:.0f}%</span></span>
                    <span>Kelly <span style="color:#00d4ff; font-family:'JetBrains Mono',monospace;">{row['kelly_allocation']*100:.0f}%</span></span>
                    <span>Dist <span style="color:#e1e1e1; font-family:'JetBrains Mono',monospace;">{row['min_dist_mil']:.1f} km</span></span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        if alertas.empty:
            st.success("Nenhum alerta — todos os objetos classificados NORMAL.")

    with chat_col:
        st.markdown("### 💬 COPILOTO BOB")
        st.caption("Pergunte: briefing #ID · alertas · clima espacial · histórico · aproximações")
        if "messages" not in st.session_state:
            st.session_state.messages = [{
                "role": "assistant",
                "content": (
                    f"Operador, catálogo demo com **{len(df_sats)}** objetos. "
                    f"**{hostis}** HOSTIL · **{suspeitos}** SUSPEITO · **{anomalos}** ANÔMALO. "
                    f"Pipeline: Isolation Forest → XGBoost → Fuzzy → Kelly. "
                    f"Ex.: `Briefing do #44231` ou `Quais alertas ativos?`"
                ),
            }]
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_input = st.chat_input("Ex: Briefing do satélite #44231")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)
            with st.chat_message("assistant"):
                with st.spinner("Bob analisando (tools + ML)..."):
                    response_text = answer_operator_query(
                        user_input, all_sats, processed_sats, processed_by_id
                    )
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    insp_col, chart_col1, chart_col2 = st.columns([1.4, 0.8, 0.8])

    with insp_col:
        st.markdown("### 🛰️ INSPETOR")
        selected_sat_name = st.selectbox("Satélite", df_sats["name"].unique(), label_visibility="collapsed")
        sat_row = df_sats[df_sats["name"] == selected_sat_name].iloc[0]
        full = processed_by_id[int(sat_row["id"])]
        feats = full["features"]
        flag = get_flag(sat_row["country"])
        threat_color = color_map.get(sat_row["classification"], "#30d158")
        st.markdown(f"""
        <div class="glass-card">
            <div style="font-size:1.05rem; font-weight:600; color:#00d4ff; margin-bottom:8px;">{flag} {selected_sat_name}</div>
            <div style="font-size:0.82rem; color:#8e8e93; line-height:1.8;">
                <div>Classificação: <span style="color:{threat_color}; font-weight:600;">{sat_row['classification']}</span>
                    (XGB: {sat_row.get('xgb_class','—')} / Fuzzy: {sat_row.get('fuzzy_classification','—')})</div>
                <div>Ameaça: {sat_row['threat_level']:.2f} · Conf: {sat_row['confidence']*100:.0f}% · Kelly: {sat_row['kelly_allocation']*100:.0f}%</div>
                <div>Dist. militar: {sat_row['min_dist_mil']:.2f} km · Cointeg. p: {sat_row.get('cointegration_pvalue', 1):.4f}</div>
                <div>Hurst: {feats.get('hurst_exponent_sma',0):.2f} · Shannon: {feats.get('shannon_entropy_sma_30d',0):.2f}
                    · CUSUM: {feats.get('l1_cusum_sma',0):.2f}</div>
                <div>Kolmogorov: {feats.get('kolmogorov_proxy_7d',0):.2f} · RKHS: {feats.get('spectral_anomaly_rkhs',0):.2f}
                    · Ricci: {feats.get('ricci_mean',0):.2f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with chart_col1:
        st.markdown("##### Por País")
        country_counts = df_sats["country"].value_counts().reset_index()
        country_counts.columns = ["País", "Qtd"]
        fig_c = go.Figure(go.Bar(x=country_counts["País"], y=country_counts["Qtd"], marker=dict(color="#00d4ff", line=dict(width=0))))
        fig_c.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#8e8e93", family="Inter", size=11), height=220,
                            margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
        st.plotly_chart(fig_c, width="stretch")

    with chart_col2:
        st.markdown("##### Por Classificação")
        cls_counts = df_sats["classification"].value_counts().reset_index()
        cls_counts.columns = ["Classe", "Qtd"]
        colors = [color_map.get(c, "#888") for c in cls_counts["Classe"]]
        fig_o = go.Figure(go.Bar(x=cls_counts["Classe"], y=cls_counts["Qtd"], marker=dict(color=colors, line=dict(width=0))))
        fig_o.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#8e8e93", family="Inter", size=11), height=220,
                            margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
        st.plotly_chart(fig_o, width="stretch")

# ====================================================================
# TAB 2 — MODEL INSIGHTS
# ====================================================================
with tab2:
    st.markdown("### 🧠 Model Insights — Isolation Forest + XGBoost + Fuzzy")
    st.markdown(
        "<span style='color:#8e8e93;font-size:0.9rem;'>DAG: features matemáticas → IF anomaly → XGB classe → Fuzzy calibração → Kelly.</span>",
        unsafe_allow_html=True,
    )
    ml_col1, ml_col2 = st.columns([1.5, 1])

    with ml_col1:
        st.markdown("##### Feature Importance (XGBoost)")
        try:
            importances = xgb_model.feature_importances_
            names = list(getattr(xgb_model, "feature_names_in_", None) or [f"f{i}" for i in range(len(importances))])
            df_imp = pd.DataFrame({"Feature": names, "Importância": importances}).sort_values("Importância", ascending=True)
            vmax = max(df_imp["Importância"].max(), 1e-9)
            colors = [f"rgba(0, {int(150 + 105 * v / vmax)}, {int(200 + 55 * v / vmax)}, 0.85)" for v in df_imp["Importância"]]
            fig_ml = go.Figure(go.Bar(x=df_imp["Importância"], y=df_imp["Feature"], orientation="h",
                                      marker=dict(color=colors, line=dict(width=0))))
            fig_ml.update_layout(margin=dict(l=10, r=20, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)",
                                 plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#8e8e93", family="Inter", size=10),
                                 height=520, xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
            st.plotly_chart(fig_ml, width="stretch")
        except Exception as e:
            st.warning(f"Não foi possível plotar importâncias: {e}")

    with ml_col2:
        st.markdown("##### Métricas de treino (hold-out 20%)")
        if train_metrics:
            st.markdown(f"""
            <div class='glass-card'>
                <div style="font-size:0.85rem; line-height:1.9; color:#e1e1e1;">
                    <div>Amostras: <span style="color:#00d4ff; font-family:JetBrains Mono,monospace;">{train_metrics.get('n_samples')}</span></div>
                    <div>Features XGB: <span style="color:#00d4ff; font-family:JetBrains Mono,monospace;">{train_metrics.get('n_features')}</span></div>
                    <div>Accuracy: <span style="color:#30d158; font-family:JetBrains Mono,monospace;">{train_metrics.get('accuracy_test',0):.3f}</span></div>
                    <div>Macro F1: <span style="color:#30d158; font-family:JetBrains Mono,monospace;">{train_metrics.get('macro_f1',0):.3f}</span></div>
                    <div>LogLoss: <span style="color:#00d4ff; font-family:JetBrains Mono,monospace;">{train_metrics.get('log_loss_test', float('nan')):.4f}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            dist = train_metrics.get("class_distribution", {})
            if dist:
                st.json(dist)
        else:
            st.info("Métricas não encontradas. Retreine os modelos.")

        st.markdown("##### Arquitetura (patente-inspired)")
        st.markdown("""
        <div class='glass-card' style="font-size:0.82rem; color:#8e8e93; line-height:1.7;">
        <b style="color:#e1e1e1;">US 2024/0394296</b> — filtro → ML quantitativo → LLM descritivo → classificação<br>
        <b style="color:#e1e1e1;">US 12,657,514</b> — Data/Inference API + DAG de modelos<br>
        <b style="color:#e1e1e1;">US 2023/0050870</b> — micro-modelos IF + XGB + fuzzy
        </div>
        """, unsafe_allow_html=True)

        if st.button("🔄 Retreinar Modelos"):
            with st.spinner("Retreinando Isolation Forest + XGBoost..."):
                metrics = train_and_save_models()
                st.success(f"✓ acc={metrics.get('accuracy_test', 0):.3f} logloss={metrics.get('log_loss_test', 0):.4f}")
                st.cache_resource.clear()
                st.cache_data.clear()
                st.rerun()

# ====================================================================
# TAB 3 — GLOSSÁRIO
# ====================================================================
with tab3:
    st.markdown("### 📖 Glossário do Framework Matemático")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        <div class="glass-card">
            <div style="font-size:0.8rem; color:#00d4ff; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:10px;">Sinais & Caos Orbital</div>
            <ul style="font-size:0.85rem; color:#e1e1e1; line-height:1.7; padding-left:18px;">
                <li><strong>Hurst (H):</strong> memória longa — H&gt;0.7 sugere empuxo contínuo.</li>
                <li><strong>Shannon:</strong> desordem em ΔSMA — órbita caótica eleva entropia.</li>
                <li><strong>Kolmogorov (zlib):</strong> complexidade algorítmica da trajetória.</li>
                <li><strong>L1-CUSUM:</strong> quebra estrutural / manobra Delta-V.</li>
                <li><strong>ADF:</strong> não-estacionariedade (manobra de baixo empuxo).</li>
                <li><strong>Mandelbrot:</strong> caudas pesadas em anomalias raras.</li>
                <li><strong>Cointegração:</strong> shadowing entre espião e alvo.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="glass-card">
            <div style="font-size:0.8rem; color:#00d4ff; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:10px;">Geometria, Lógica & Decisão</div>
            <ul style="font-size:0.85rem; color:#e1e1e1; line-height:1.7; padding-left:18px;">
                <li><strong>RKHS:</strong> anomalia espectral vs baseline normal.</li>
                <li><strong>Ricci (Ollivier):</strong> distorção de vizinhança / convergência.</li>
                <li><strong>Homologia H0/H1:</strong> topologia da nuvem de posições.</li>
                <li><strong>Chern-Simons proxy:</strong> não-conservação de h = r×v.</li>
                <li><strong>Fuzzy Mamdani:</strong> calibração sob incerteza de TLE.</li>
                <li><strong>Łukasiewicz:</strong> consistência lógica (cointeg → Hurst).</li>
                <li><strong>Kelly:</strong> sizing de tasking de sensores.</li>
                <li><strong>Williams:</strong> valor intrínseco por país/missão/órbita.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
