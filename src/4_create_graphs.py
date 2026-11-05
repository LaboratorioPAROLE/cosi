import yaml
import pandas as pd
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

# =========================
# COSTANTI MAPPA
# =========================
GRIGIO = "#e5e7eb"   # regioni senza dati
BORDO = "#b9b4c7"    # contorno uniforme per tutte le regioni

# Scala viola: lavanda chiarissimo -> viola scuro, con #823cf4 come tono alto
PURPLE_SCALE = [
    [0.0, "#f3ecfe"],
    [0.5, "#b794f8"],
    [0.75, "#823cf4"],
    [1.0, "#4a1a9e"],
]

GEOJSON_URL = "https://raw.githubusercontent.com/openpolis/geojson-italy/master/geojson/limits_IT_regions.geojson"

# =========================
# PATH
# =========================
PROJECT_ROOT = Path(__file__).resolve().parent.parent

YAML_DIR = PROJECT_ROOT / "cosi" / "stats"

OUT_DIR = PROJECT_ROOT / "docs" / "imgs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# LOAD CORPUS DATA
# =========================
with open(PROJECT_ROOT / "project_materials" / "corpus-data.yaml", encoding="utf-8") as f:
    corpus_data = yaml.safe_load(f)

REGION_TOTALS = corpus_data["region"]
MIN_REGION_TOKENS = 40000

# =========================
# CLEANING
# =========================
INVALID_VALUES = {"unknown", "n/a", "N/A", "===NONE===", "none", ""}

def clean_value(x):
    if x is None:
        return None
    x = str(x).strip().lower()
    if x in INVALID_VALUES:
        return None
    return x

# =========================
# AGE ORDER
# =========================
AGE_ORDER = [
    "16-20", "21-30", "31-40",
    "41-50", "51-60", "61-70", ">71"
]

# =========================
# LABEL MAPS
# =========================
TYPE_MAP = {
    "free-conversation": "Conversazione libera",
    "lecture": "Lezione",
    "exam": "Esame",
    "semistructured-interview": "Intervista",
    "office-hours": "Ricevimento studenti"
}

REGION_LABEL = {
    "emilia-romagna": "Emilia-Romagna",
    "piemonte": "Piemonte",
    "puglia": "Puglia",
    "lombardia": "Lombardia",
    "sicilia": "Sicilia",
    "calabria": "Calabria",
    "veneto": "Veneto",
    "campania": "Campania",
    "basilicata": "Basilicata",
    "lazio": "Lazio",
    "marche": "Marche",
    "toscana": "Toscana",
    "sardegna": "Sardegna",
    "abruzzo": "Abruzzo",
    "umbria": "Umbria",
    "friuli-venezia-giulia": "Friuli-Venezia Giulia",
    "valle-d-aosta": "Valle d'Aosta/Vallée d'Aoste",
    "trentino-alto-adige": "Trentino-Alto Adige/Südtirol",
    "liguria": "Liguria",
    "molise": "Molise"
}

MACROAREA = {
    "emilia-romagna": "Nord", "piemonte": "Nord", "lombardia": "Nord",
    "veneto": "Nord", "friuli-venezia-giulia": "Nord", "valle-d-aosta": "Nord",
    "trentino-alto-adige": "Nord", "liguria": "Nord",
    "lazio": "Centro", "marche": "Centro", "toscana": "Centro", "umbria": "Centro",
    "puglia": "Sud e Isole", "sicilia": "Sud e Isole", "calabria": "Sud e Isole",
    "campania": "Sud e Isole", "basilicata": "Sud e Isole", "sardegna": "Sud e Isole",
    "abruzzo": "Sud e Isole", "molise": "Sud e Isole",
}

# posizione (lat, lon) delle etichette di macroarea sulla mappa
AREA_LABEL_POS = {
    "Nord": (45.4, 10.2),
    "Centro": (42.9, 12.3),
    "Sud e Isole": (40.6, 15.9),
}

def clean_type(x):
    x = clean_value(x)
    if not x:
        return None
    return TYPE_MAP.get(x, x)


def save_fig_json(fig, path):
    """
    Salva solo i dati necessari a Plotly.js per ridisegnare il grafico
    (fig.to_json() usa il PlotlyJSONEncoder, gestisce numpy/pandas correttamente).
    Niente libreria Plotly duplicata: il file pesa KB, non MB.
    """
    path.write_text(fig.to_json(), encoding="utf-8")

# =========================
# PROIEZIONE: titolo, nota, hover
# =========================
def make_title(base, is_proj):
    return f"{base} (proiezione)" if is_proj else base

def add_proj_note(fig, sampling):
    if not sampling.get("is_sample"):
        return
    fig.add_annotation(
        text=(f"Valori normalizzati proiettati: campione di {sampling['nRows']} "
              f"occorrenze su {sampling['nOccTot']} (fattore ×{sampling['factor']:.2f})"),
        xref="paper", yref="paper", x=0.5, y=-0.2,
        showarrow=False, font=dict(size=11, color="#6b7280")
    )
    fig.update_layout(margin=dict(b=100))

def bar_hover(is_proj):
    h = "<b>%{x}</b><br>Freq: %{customdata[0]}"
    if is_proj:
        h += "<br>Freq proiettata: %{customdata[1]:.0f}"
    return h + "<br>Freq (norm.): %{y:.2f}<extra></extra>"

def count_proj(v):
    return v.get("count_proj", v.get("count", 0))


# =========================
# PROCESS FILES
# =========================
for yaml_file in YAML_DIR.glob("*.yaml"):

    with open(yaml_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    out_folder = OUT_DIR / yaml_file.stem
    out_folder.mkdir(parents=True, exist_ok=True)

    metadata = data.get("metadata_SD", {})
    sampling = data.get("sampling", {}) or {}
    is_proj = bool(sampling.get("is_sample"))

    # =========================
    # 1. TYPE BARPLOT
    # =========================
    if "type" in metadata:

        df = pd.DataFrame([
            {
                "Tipo": TYPE_MAP.get(k, k),
                "Freq": v.get("count", 0),
                "Freq_proj": count_proj(v),
                "Freq_norm": v.get("fpmw", 0)
            }
            for k, v in metadata["type"].items()
            if clean_type(k)
        ])

        if not df.empty:
            fig = px.bar(
                df,
                x="Tipo",
                y="Freq_norm",
                labels={"Freq_norm": "Freq (per milione)"}
            )

            fig.update_traces(
                hovertemplate=bar_hover(is_proj),
                customdata=df[["Freq", "Freq_proj"]].values
            )

            fig.update_layout(
                title=make_title("Distribuzione per tipo di interazione", is_proj),
                title_x=0.5
            )
            add_proj_note(fig, sampling)

            save_fig_json(fig, out_folder / "type.json")

    # =========================
    # 2. AGE BARPLOT
    # =========================
    if "age-range" in metadata:

        df = pd.DataFrame([
            {
                "Età": k,
                "Freq": v.get("count", 0),
                "Freq_proj": count_proj(v),
                "Freq_norm": v.get("fpmw", 0)
            }
            for k, v in metadata["age-range"].items()
            if clean_value(k)
        ])

        if not df.empty:
            df["Età"] = pd.Categorical(df["Età"], categories=AGE_ORDER, ordered=True)
            df = df.sort_values("Età")

            fig = px.bar(
                df,
                x="Età",
                y="Freq_norm",
                labels={"Freq_norm": "Freq (per milione)"}
            )

            fig.update_traces(
                hovertemplate=bar_hover(is_proj),
                customdata=df[["Freq", "Freq_proj"]].values
            )

            fig.update_layout(
                title=make_title("Distribuzione per età", is_proj),
                title_x=0.5
            )
            add_proj_note(fig, sampling)

            save_fig_json(fig, out_folder / "age.json")

    # =========================
    # 3. REGION MAP
    # =========================
    if "region" in metadata:

        rows = []

        for k, v in metadata["region"].items():
            k_clean = clean_value(k)
            if not k_clean:
                continue

            total = REGION_TOTALS.get(k_clean, 0)
            label = REGION_LABEL.get(k_clean, k_clean)

            if total < MIN_REGION_TOKENS:
                rows.append({"Regione": label, "Freq": None,
                             "Freq_proj": None, "Freq_norm": None})
            else:
                rows.append({
                    "Regione": label,
                    "Freq": v.get("count", 0),
                    "Freq_proj": count_proj(v),
                    "Freq_norm": v.get("fpmw", 0)
                })

        df = pd.DataFrame(rows)

        if not df.empty:

            df_valid = df[df["Freq_norm"].notna()].copy()
            valid_names = set(df_valid["Regione"])
            missing = [r for r in REGION_LABEL.values() if r not in valid_names]

            df_valid["Freq_norm_display"] = df_valid["Freq_norm"].round(2)
            df_valid["Freq_proj_display"] = df_valid["Freq_proj"].round(0)

            fig = px.choropleth(
                df_valid,
                geojson=GEOJSON_URL,
                featureidkey="properties.reg_name",
                locations="Regione",
                color="Freq_norm",
                color_continuous_scale=PURPLE_SCALE,
                labels={"Freq_norm": "Freq (per milione)"}
            )

            hover = "<b>%{location}</b><br>Freq: %{customdata[0]}<br>"
            if is_proj:
                hover += "Freq proiettata: %{customdata[1]}<br>"
            hover += "Freq (norm.): %{customdata[2]}<extra></extra>"

            fig.update_traces(
                hovertemplate=hover,
                customdata=df_valid[["Freq", "Freq_proj_display", "Freq_norm_display"]].values
            )

            if missing:
                fig.add_trace(go.Choropleth(
                    geojson=GEOJSON_URL,
                    featureidkey="properties.reg_name",
                    locations=missing,
                    z=[1] * len(missing),
                    colorscale=[[0, GRIGIO], [1, GRIGIO]],
                    showscale=False,
                    showlegend=False,
                    hovertemplate="<b>%{location}</b><br>Dati non disponibili<extra></extra>"
                ))

                fig.add_trace(go.Scattergeo(
                    lon=[None], lat=[None],
                    mode="markers",
                    marker=dict(size=12, symbol="square", color=GRIGIO,
                                line=dict(color=BORDO, width=1)),
                    name="Dati non disponibili",
                    showlegend=True
                ))

            fig.update_traces(
                marker_line_color=BORDO,
                marker_line_width=0.6,
                selector=dict(type="choropleth")
            )

            fig.update_geos(fitbounds="locations", visible=False)

            fig.update_layout(
                title=make_title("Distribuzione geografica", is_proj),
                title_x=0.5,
                legend=dict(orientation="h", y=0, x=0.5, xanchor="center")
            )
            add_proj_note(fig, sampling)

            save_fig_json(fig, out_folder / "region_map.json")

    # =========================
    # 4. MACROAREA MAP
    # =========================
    if "macroarea" in metadata:

        areas = metadata["macroarea"]

        # ogni regione prende il valore della sua macroarea
        rows = []
        for reg_key, label in REGION_LABEL.items():
            area = MACROAREA[reg_key]
            v = areas.get(area, {}) or {}
            rows.append({
                "Regione": label,
                "Area": area,
                "Freq": v.get("count", 0),
                "Freq_proj": round(count_proj(v)),
                "Freq_norm": v.get("fpmw", 0)
            })

        df = pd.DataFrame(rows)
        df["Freq_norm_display"] = df["Freq_norm"].round(2)
        vmax = df["Freq_norm"].max() or 1

        fig = px.choropleth(
            df,
            geojson=GEOJSON_URL,
            featureidkey="properties.reg_name",
            locations="Regione",
            color="Freq_norm",
            color_continuous_scale=PURPLE_SCALE,
            range_color=(0, vmax),
            labels={"Freq_norm": "Freq (per milione)"}
        )

        hover = "<b>%{customdata[0]}</b><br>(%{location})<br>Freq: %{customdata[1]}<br>"
        if is_proj:
            hover += "Freq proiettata: %{customdata[2]}<br>"
        hover += "Freq (norm.): %{customdata[3]}<extra></extra>"

        fig.update_traces(
            hovertemplate=hover,
            customdata=df[["Area", "Freq", "Freq_proj", "Freq_norm_display"]].values,
            marker_line_color=BORDO,
            marker_line_width=0.3
        )

        # etichette testuali delle tre macroaree
        lab_names, lab_lat, lab_lon = [], [], []
        for area, (lat, lon) in AREA_LABEL_POS.items():
            val = (areas.get(area, {}) or {}).get("fpmw", 0)
            lab_names.append(f"<b>{area}</b><br>{val:.1f}")
            lab_lat.append(lat)
            lab_lon.append(lon)

        fig.add_trace(go.Scattergeo(
            lat=lab_lat, lon=lab_lon, text=lab_names,
            mode="text",
            textfont=dict(size=12, color="#1f1235"),
            hoverinfo="skip",
            showlegend=False
        ))

        fig.update_geos(fitbounds="locations", visible=False)

        fig.update_layout(
            title=make_title("Distribuzione per macroarea", is_proj),
            title_x=0.5
        )
        add_proj_note(fig, sampling)

        save_fig_json(fig, out_folder / "macroarea_map.json")

    print(f"Creati dati grafici (JSON) per {yaml_file.stem}" +
          (" [proiezione]" if is_proj else ""))