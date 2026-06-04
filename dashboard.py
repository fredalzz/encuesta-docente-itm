import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter

st.set_page_config(
    page_title="Dashboard Encuesta Docente ITM",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 100%);
        padding: 20px 30px; border-radius: 10px;
        color: white; margin-bottom: 20px;
    }
    .section-title {
        color: #1e3a5f; font-size: 17px; font-weight: 600;
        border-bottom: 2px solid #2d6a9f;
        padding-bottom: 5px; margin: 20px 0 10px 0;
    }
    .filter-banner {
        background: #fff8e1; border-left: 4px solid #f39c12;
        padding: 8px 14px; border-radius: 6px; margin-bottom: 12px;
        font-size: 13px; color: #7d5a00;
    }
    [data-testid="stMetric"] {
        background: white; border: 1px solid #dde6f0;
        border-radius: 8px; padding: 15px !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
</style>
""", unsafe_allow_html=True)

COLORS = ["#2d6a9f","#27ae60","#e74c3c","#f39c12","#8e44ad",
          "#16a085","#d35400","#2980b9","#c0392b","#1abc9c",
          "#7f8c8d","#f1c40f","#e67e22","#3498db","#2ecc71"]

# ─── LOAD DATA ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    res_file = pd.read_excel("Docentes_Resultados_por_Pregunta.xlsx", sheet_name=None)
    raw = pd.read_excel(
        "Respuestas Encuesta de Percepción Docente_ Autoevaluación con fines de Acreditación AGPM(1-32).xlsx"
    )

    indice = res_file["Indice"].dropna(subset=["hoja"]).copy()
    indice.columns = ["hoja", "pregunta"]

    # Build full preguntas from aggregated file (used when no filter)
    preguntas_full = {}
    for _, row in indice.iterrows():
        hoja = row["hoja"]
        if hoja not in res_file:
            continue
        df = res_file[hoja].copy().iloc[:, :3]
        df.columns = ["opcion", "cantidad", "porcentaje"]
        df = df[df["opcion"].notna()]
        df = df[~df["opcion"].astype(str).str.strip().isin(["Opción", "Total", "nan"])]
        df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce")
        df["porcentaje"] = pd.to_numeric(df["porcentaje"], errors="coerce")
        df["opcion"] = df["opcion"].astype(str).str.strip().str.rstrip(";")
        df = df.dropna(subset=["cantidad"])
        if not df.empty:
            preguntas_full[hoja] = {"titulo": row["pregunta"], "datos": df}

    # Map raw columns to P-keys by matching question text
    col_map = {}  # P-key -> raw column name
    for _, row in indice.iterrows():
        hoja = row["hoja"]
        titulo = str(row["pregunta"]).strip()
        for col in raw.columns:
            if str(col).strip() == titulo:
                col_map[hoja] = col
                break

    # Teacher type column (index 6)
    tipo_col = raw.columns[6]
    tipos = sorted(raw[tipo_col].dropna().unique().tolist())

    return preguntas_full, raw, indice, col_map, tipo_col, tipos


def compute_preguntas_filtered(raw_filtered, indice, col_map, preguntas_full):
    """Recompute aggregates from filtered raw data."""
    preguntas = {}
    for _, row in indice.iterrows():
        hoja = row["hoja"]
        if hoja not in col_map:
            # fallback to full data (question not in raw)
            if hoja in preguntas_full:
                preguntas[hoja] = preguntas_full[hoja]
            continue
        col = col_map[hoja]
        series = raw_filtered[col].dropna().astype(str).str.strip().str.rstrip(";")
        if series.empty:
            continue
        counts = series.value_counts().reset_index()
        counts.columns = ["opcion", "cantidad"]
        total = counts["cantidad"].sum()
        counts["porcentaje"] = counts["cantidad"] / total
        preguntas[hoja] = {"titulo": row["pregunta"], "datos": counts}
    return preguntas


preguntas_full, raw, indice, col_map, tipo_col, tipos = load_data()

# ─── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎓 Encuesta Docente ITM")
    st.markdown("**Acreditación AGPM · 2026**")
    st.divider()

    vista = st.radio("Vista", ["📊 Resumen General", "🔍 Análisis por Pregunta", "📋 Datos Individuales"])
    st.divider()

    st.markdown("#### 🔽 Filtrar por tipo de docente")
    tipos_sel = st.multiselect(
        "Tipo de vinculación",
        options=tipos,
        default=tipos,
        help="Selecciona uno o varios tipos para filtrar todos los gráficos"
    )

    filtro_activo = set(tipos_sel) != set(tipos) and len(tipos_sel) > 0
    st.divider()
    st.caption(f"📋 Preguntas: **{len(preguntas_full)}**")

# ─── APPLY FILTER ──────────────────────────────────────────────────────────────
if not tipos_sel:
    tipos_sel = tipos

raw_filtered = raw[raw[tipo_col].isin(tipos_sel)] if filtro_activo else raw
n_docentes = len(raw_filtered)

if filtro_activo:
    preguntas = compute_preguntas_filtered(raw_filtered, indice, col_map, preguntas_full)
else:
    preguntas = preguntas_full

# ─── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h2 style="margin:0">📊 Dashboard — Encuesta de Percepción Docente</h2>
    <p style="margin:5px 0 0 0;opacity:0.85">Autoevaluación con fines de Acreditación AGPM · ITM · 2026</p>
</div>
""", unsafe_allow_html=True)

if filtro_activo:
    st.markdown(
        f'<div class="filter-banner">⚠️ Filtro activo: mostrando solo <strong>{", ".join(tipos_sel)}</strong> '
        f'— {n_docentes} de {len(raw)} docentes</div>',
        unsafe_allow_html=True
    )

# ─── KPIs ──────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Docentes (filtro)", n_docentes, delta=f"{n_docentes - len(raw)} vs total" if filtro_activo else None)
k2.metric("Preguntas Analizadas", len(preguntas))

tipo_counts = raw_filtered[tipo_col].value_counts()
catedra = int(tipo_counts.get("Docente de Cátedra", 0)) if not filtro_activo else sum(
    1 for v in raw_filtered[tipo_col] if "tedra" in str(v))
ocasional = int(tipo_counts.filter(like="Ocasional").sum()) if hasattr(tipo_counts, "filter") else 0

d_p1 = preguntas.get("P1", {}).get("datos", pd.DataFrame())
if not d_p1.empty:
    opc_counts = d_p1.set_index("opcion")["cantidad"]
    catedra_v = opc_counts.filter(like="tedra").sum() if not d_p1.empty else 0
    ocasional_v = opc_counts.filter(like="casional").sum() if not d_p1.empty else 0
    k3.metric("Docentes Cátedra", int(catedra_v))
    k4.metric("Docentes Ocasional", int(ocasional_v))

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
if vista == "📊 Resumen General":
# ═══════════════════════════════════════════════════════════════════════════════

    st.markdown('<div class="section-title">Perfil Demográfico del Cuerpo Docente</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        d = preguntas.get("P1", {}).get("datos", pd.DataFrame())
        if not d.empty:
            fig = px.pie(d, names="opcion", values="cantidad",
                         title="Relación Laboral", hole=0.4,
                         color_discrete_sequence=COLORS)
            fig.update_traces(textposition="outside", textinfo="percent+label")
            fig.update_layout(showlegend=False, height=300, margin=dict(t=45, b=5))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        d = preguntas.get("P2", {}).get("datos", pd.DataFrame())
        if not d.empty:
            fig = px.bar(d.sort_values("cantidad"), x="cantidad", y="opcion",
                         orientation="h", title="Años de Experiencia en ITM",
                         color="cantidad", color_continuous_scale="Blues", text="cantidad")
            fig.update_layout(yaxis_title="", xaxis_title="Docentes",
                              height=300, coloraxis_showscale=False, margin=dict(t=45, b=5))
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

    with col3:
        d = preguntas.get("P3", {}).get("datos", pd.DataFrame())
        if not d.empty:
            d_top = d.nlargest(8, "cantidad")
            fig = px.bar(d_top.sort_values("cantidad"), x="cantidad", y="opcion",
                         orientation="h", title="Áreas de Enseñanza (Top 8)",
                         color="cantidad", color_continuous_scale="Greens", text="cantidad")
            fig.update_layout(yaxis_title="", xaxis_title="Docentes",
                              height=300, coloraxis_showscale=False, margin=dict(t=45, b=5))
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

    # ── Barra favorabilidad ───────────────────────────────────────────────────
    st.markdown('<div class="section-title">Porcentaje de Respuesta Favorable por Pregunta</div>', unsafe_allow_html=True)

    positivos = ["siempre", "sí", "de acuerdo", "totalmente de acuerdo",
                 "casi siempre", "muy satisfecho", "satisfecho"]
    resumen = []
    for key, val in list(preguntas.items())[3:]:
        d = val["datos"]
        pct = d[d["opcion"].str.lower().str.contains("|".join(positivos), na=False)]["porcentaje"].sum()
        resumen.append({"Pregunta": key, "% Favorable": round(pct * 100, 1), "Título": val["titulo"][:80]})

    if resumen:
        res_df = pd.DataFrame(resumen)
        fig = px.bar(res_df, x="Pregunta", y="% Favorable",
                     hover_data=["Título"],
                     color="% Favorable",
                     color_continuous_scale="RdYlGn",
                     range_color=[0, 100])
        fig.add_hline(y=70, line_dash="dash", line_color="#c0392b",
                      annotation_text="Umbral 70%", annotation_position="top right")
        fig.update_layout(height=380, coloraxis_showscale=True,
                          xaxis_title="Pregunta", yaxis_title="% Favorable",
                          margin=dict(t=20, b=50))
        st.plotly_chart(fig, use_container_width=True)

        c_top, c_bot = st.columns(2)
        with c_top:
            st.markdown("**Top 5 — Mayor satisfacción**")
            st.dataframe(res_df.nlargest(5, "% Favorable")[["Pregunta", "% Favorable", "Título"]],
                         hide_index=True, use_container_width=True)
        with c_bot:
            st.markdown("**Bottom 5 — Menor satisfacción**")
            st.dataframe(res_df.nsmallest(5, "% Favorable")[["Pregunta", "% Favorable", "Título"]],
                         hide_index=True, use_container_width=True)

    # ── Radar + Diverging Bar ─────────────────────────────────────────────────
    st.markdown('<div class="section-title">Radar — Favorabilidad por Tipo de Docente</div>', unsafe_allow_html=True)

    positivos_radar = ["siempre", "sí", "de acuerdo", "totalmente de acuerdo", "casi siempre"]

    # Compute favorability per question per teacher type
    radar_pregs = [k for k in list(preguntas.keys())[3:] if k in col_map][:15]
    radar_rows = {}
    for tipo in tipos:
        sub = raw[raw[tipo_col] == tipo]
        vals = []
        for key in radar_pregs:
            col_raw = col_map[key]
            serie = sub[col_raw].dropna().astype(str).str.lower()
            if len(serie) == 0:
                vals.append(0)
                continue
            pos = serie.str.contains("|".join(positivos_radar)).sum()
            vals.append(round(pos / len(serie) * 100, 1))
        radar_rows[tipo] = vals

    if radar_rows:
        fig_radar = go.Figure()
        radar_colors = ["#2d6a9f", "#27ae60", "#e74c3c"]
        for i, (tipo, vals) in enumerate(radar_rows.items()):
            fig_radar.add_trace(go.Scatterpolar(
                r=vals + [vals[0]],
                theta=radar_pregs + [radar_pregs[0]],
                fill="toself",
                name=tipo,
                line_color=radar_colors[i % len(radar_colors)],
                fillcolor=radar_colors[i % len(radar_colors)],
                opacity=0.3
            ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100],
                                       ticksuffix="%", tickfont_size=10)),
            showlegend=True,
            height=480,
            margin=dict(t=30, b=30, l=60, r=60),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_radar, use_container_width=True)
        st.caption("Muestra las primeras 15 preguntas (P4–P18). Cada eje = % respuesta favorable.")

    # ── Diverging Bar ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Barras Divergentes — Distribución Likert por Pregunta</div>', unsafe_allow_html=True)

    LIKERT_NEG = ["nada de acuerdo", "poco de acuerdo", "totalmente en desacuerdo", "en desacuerdo", "casi nunca", "nunca"]
    LIKERT_NEU = ["ni de acuerdo ni en desacuerdo", "no sabe o no responde", "a veces"]
    LIKERT_POS = ["totalmente de acuerdo", "de acuerdo", "siempre", "casi siempre", "sí"]
    LIKERT_ORDER = LIKERT_NEG + LIKERT_NEU + LIKERT_POS

    div_pregs = [k for k in list(preguntas.keys())[3:] if k in col_map]
    div_rows = []
    for key in div_pregs:
        col_raw = col_map[key]
        serie = raw_filtered[col_raw].dropna().astype(str).str.strip().str.rstrip(";").str.lower()
        if serie.empty:
            continue
        total = len(serie)
        row = {"Pregunta": key}
        for opt in LIKERT_ORDER:
            cnt = serie.str.contains(opt, regex=False).sum()
            pct = round(cnt / total * 100, 1)
            # negatives go left (negative value)
            if opt in LIKERT_NEG:
                row[opt] = -pct
            else:
                row[opt] = pct
        div_rows.append(row)

    if div_rows:
        div_df = pd.DataFrame(div_rows).fillna(0)
        existing_opts = [o for o in LIKERT_ORDER if o in div_df.columns and div_df[o].abs().sum() > 0]

        COLOR_MAP = {
            "nada de acuerdo": "#c0392b", "poco de acuerdo": "#e74c3c",
            "totalmente en desacuerdo": "#c0392b", "en desacuerdo": "#e74c3c",
            "casi nunca": "#e74c3c", "nunca": "#c0392b",
            "ni de acuerdo ni en desacuerdo": "#bdc3c7", "no sabe o no responde": "#95a5a6",
            "a veces": "#bdc3c7",
            "totalmente de acuerdo": "#1a7a4a", "de acuerdo": "#27ae60",
            "siempre": "#1a7a4a", "casi siempre": "#27ae60", "sí": "#27ae60"
        }

        fig_div = go.Figure()
        for opt in existing_opts:
            fig_div.add_trace(go.Bar(
                name=opt.title(),
                y=div_df["Pregunta"],
                x=div_df[opt],
                orientation="h",
                marker_color=COLOR_MAP.get(opt, "#95a5a6"),
                hovertemplate=f"<b>%{{y}}</b><br>{opt.title()}: %{{customdata:.1f}}%<extra></extra>",
                customdata=div_df[opt].abs()
            ))

        fig_div.add_vline(x=0, line_width=1.5, line_color="black")
        fig_div.update_layout(
            barmode="relative",
            height=max(400, len(div_df) * 22),
            xaxis=dict(title="← Negativo / Positivo →", ticksuffix="%",
                       tickvals=[-100, -75, -50, -25, 0, 25, 50, 75, 100],
                       ticktext=["100%","75%","50%","25%","0","25%","50%","75%","100%"]),
            yaxis=dict(autorange="reversed", title=""),
            legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="center", x=0.5,
                        traceorder="normal"),
            margin=dict(l=60, r=20, t=20, b=80)
        )
        st.plotly_chart(fig_div, use_container_width=True)

    # ── Heatmap ───────────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Mapa de Calor — Distribución de Respuestas Likert</div>', unsafe_allow_html=True)

    opcion_counter = Counter()
    for val in list(preguntas.values())[3:]:
        for o in val["datos"]["opcion"]:
            opcion_counter[o.strip()] += 1
    common_opts = [o for o, c in opcion_counter.items() if c >= 5]

    if common_opts:
        hm_rows = []
        for key, val in list(preguntas.items())[3:]:
            d = val["datos"]
            row = {"Pregunta": key}
            for opt in common_opts:
                match = d[d["opcion"] == opt]["porcentaje"]
                row[opt] = round(match.values[0] * 100, 1) if len(match) > 0 else 0
            if sum(row[o] for o in common_opts) > 0:
                hm_rows.append(row)

        if hm_rows:
            hm_df = pd.DataFrame(hm_rows)
            z_vals = hm_df[common_opts].values
            fig = go.Figure(data=go.Heatmap(
                z=z_vals, x=common_opts, y=hm_df["Pregunta"],
                colorscale="RdYlGn",
                text=[[f"{v:.0f}%" for v in row] for row in z_vals],
                texttemplate="%{text}",
                hovertemplate="<b>%{y}</b><br>%{x}: %{z:.1f}%<extra></extra>"
            ))
            fig.update_layout(
                height=max(350, len(hm_df) * 20),
                margin=dict(l=60, r=20, t=10, b=80),
                xaxis=dict(side="bottom", tickangle=-30),
                yaxis=dict(autorange="reversed")
            )
            st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
elif vista == "🔍 Análisis por Pregunta":
# ═══════════════════════════════════════════════════════════════════════════════

    pregunta_sel = st.selectbox(
        "Selecciona una pregunta",
        options=list(preguntas.keys()),
        format_func=lambda k: f"{k} — {preguntas[k]['titulo'][:90]}"
    )

    if pregunta_sel:
        info = preguntas[pregunta_sel]
        d = info["datos"].copy()
        d["pct"] = (d["porcentaje"] * 100).round(1)
        d_sorted = d.sort_values("cantidad", ascending=False)

        st.info(f"**{pregunta_sel}:** {info['titulo']}")

        # Comparar tipos si no hay filtro activo
        if not filtro_activo and pregunta_sel in col_map:
            st.markdown('<div class="section-title">Comparación por Tipo de Docente</div>', unsafe_allow_html=True)
            col_raw = col_map[pregunta_sel]
            comp_rows = []
            for tipo in tipos:
                sub = raw[raw[tipo_col] == tipo][col_raw].dropna().astype(str).str.strip().str.rstrip(";")
                if sub.empty:
                    continue
                cnt = sub.value_counts().reset_index()
                cnt.columns = ["opcion", "cantidad"]
                cnt["tipo"] = tipo
                cnt["porcentaje"] = cnt["cantidad"] / cnt["cantidad"].sum()
                comp_rows.append(cnt)

            if comp_rows:
                comp_df = pd.concat(comp_rows, ignore_index=True)
                fig_comp = px.bar(comp_df, x="opcion", y="porcentaje",
                                  color="tipo", barmode="group",
                                  color_discrete_sequence=COLORS,
                                  text=comp_df["porcentaje"].apply(lambda x: f"{x*100:.0f}%"),
                                  labels={"opcion": "", "porcentaje": "Porcentaje", "tipo": "Tipo"})
                fig_comp.update_layout(height=350, yaxis_tickformat=".0%",
                                       margin=dict(t=10, b=60), xaxis_tickangle=-15)
                fig_comp.update_traces(textposition="outside")
                st.plotly_chart(fig_comp, use_container_width=True)

        col_chart, col_detail = st.columns([3, 1])

        with col_chart:
            tipo_g = st.radio("Tipo de gráfico", ["Barras Verticales", "Barras Horizontales", "Pastel / Dona"],
                              horizontal=True)
            if tipo_g == "Barras Verticales":
                fig = px.bar(d_sorted, x="opcion", y="cantidad",
                             color="opcion", color_discrete_sequence=COLORS, text="cantidad")
                fig.update_traces(textposition="outside")
                fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Nº Docentes",
                                  height=400, xaxis_tickangle=-20)
            elif tipo_g == "Barras Horizontales":
                fig = px.bar(d_sorted.sort_values("cantidad"), x="cantidad", y="opcion",
                             orientation="h", color="cantidad",
                             color_continuous_scale="Blues", text="cantidad")
                fig.update_traces(textposition="outside")
                fig.update_layout(yaxis_title="", xaxis_title="Nº Docentes",
                                  coloraxis_showscale=False, height=400)
            else:
                fig = px.pie(d_sorted, names="opcion", values="cantidad",
                             hole=0.4, color_discrete_sequence=COLORS)
                fig.update_traces(textposition="outside", textinfo="percent+label")
                fig.update_layout(height=400, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)

        with col_detail:
            st.markdown("##### Resultados")
            tabla = d_sorted[["opcion", "cantidad", "pct"]].copy()
            tabla.columns = ["Opción", "N", "%"]
            st.dataframe(tabla, hide_index=True, use_container_width=True, height=280)
            st.metric("Total respuestas", int(d["cantidad"].sum()))
            dom = d_sorted.iloc[0]
            st.metric("Respuesta dominante", dom["opcion"][:25])
            st.metric("% dominante", f"{dom['pct']:.1f}%")

        # Gauge
        fig_g = go.Figure(go.Indicator(
            mode="gauge+number",
            value=dom["pct"],
            title={"text": f'Respuesta dominante: "{dom["opcion"]}"', "font": {"size": 13}},
            number={"suffix": "%", "font": {"size": 28}},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#2d6a9f"},
                "steps": [
                    {"range": [0, 40], "color": "#fde8e8"},
                    {"range": [40, 70], "color": "#fef9e7"},
                    {"range": [70, 100], "color": "#e8f8f5"}
                ],
                "threshold": {"line": {"color": "#c0392b", "width": 3}, "value": 70}
            }
        ))
        fig_g.update_layout(height=220, margin=dict(t=40, b=10, l=30, r=30))
        st.plotly_chart(fig_g, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
elif vista == "📋 Datos Individuales":
# ═══════════════════════════════════════════════════════════════════════════════

    st.markdown('<div class="section-title">Respuestas Individuales</div>', unsafe_allow_html=True)

    col_f, col_s = st.columns([3, 1])
    with col_f:
        cols_sel = st.multiselect("Columnas a mostrar", list(raw_filtered.columns),
                                  default=list(raw_filtered.columns)[:8])
    with col_s:
        buscar = st.text_input("Buscar texto", placeholder="Filtrar...")

    df_show = raw_filtered[cols_sel] if cols_sel else raw_filtered
    if buscar:
        mask = df_show.astype(str).apply(lambda c: c.str.contains(buscar, case=False, na=False)).any(axis=1)
        df_show = df_show[mask]

    st.dataframe(df_show, use_container_width=True, height=500)
    st.caption(f"Mostrando **{len(df_show)}** de **{len(raw)}** registros")

    csv = df_show.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Descargar CSV", csv, "encuesta_docente_filtrada.csv", "text/csv")
