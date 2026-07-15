import yaml
import pandas as pd
from pathlib import Path
import plotly.express as px

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
# PROCESS FILES
# =========================
for yaml_file in YAML_DIR.glob("*.yaml"):

    with open(yaml_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    out_folder = OUT_DIR / yaml_file.stem
    out_folder.mkdir(parents=True, exist_ok=True)

    metadata = data.get("metadata_SD", {})

    # =========================
    # 1. TYPE BARPLOT
    # =========================
    if "type" in metadata:

        df = pd.DataFrame([
            {
                "Tipo": TYPE_MAP.get(k, k),
                "Freq": v.get("count", 0),
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
                hovertemplate="<b>%{x}</b><br>Freq: %{customdata[0]}<br>Freq (norm.): %{y:.2f}",
                customdata=df[["Freq"]].values
            )

            fig.update_layout(title="Distribuzione per tipo di interazione", title_x=0.5)

            save_fig_json(fig, out_folder / "type.json")

    # =========================
    # 2. AGE BARPLOT
    # =========================
    if "age-range" in metadata:

        df = pd.DataFrame([
            {
                "Età": k,
                "Freq": v.get("count", 0),
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
                hovertemplate="<b>%{x}</b><br>Freq: %{customdata[0]}<br>Freq (norm.): %{y:.2f}",
                customdata=df[["Freq"]].values
            )

            fig.update_layout(title="Distribuzione per età", title_x=0.5)

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

            if total < MIN_REGION_TOKENS:
                rows.append({
                    "Regione": REGION_LABEL.get(k_clean, k_clean),
                    "Freq": None,
                    "Freq_norm": None
                })
            else:
                rows.append({
                    "Regione": REGION_LABEL.get(k_clean, k_clean),
                    "Freq": v.get("count", 0),
                    "Freq_norm": v.get("fpmw", 0)
                })

        df = pd.DataFrame(rows)

        if not df.empty:
            fig = px.choropleth(
                df,
                geojson="https://raw.githubusercontent.com/openpolis/geojson-italy/master/geojson/limits_IT_regions.geojson",
                featureidkey="properties.reg_name",
                locations="Regione",
                color="Freq_norm",
                color_continuous_scale="Reds"
            )

            df["Freq_norm_display"] = df["Freq_norm"].round(2)
            df["Freq_display"] = df["Freq"].fillna("NA")
            df["Freq_norm_display"] = df["Freq_norm_display"].fillna("NA")

            fig.update_traces(hovertemplate="<b>%{location}</b><br>" +
                  "Freq: %{customdata[0]}<br>" +
                  "Freq (norm.): %{customdata[1]}",
                    customdata=df[["Freq_display", "Freq_norm_display"]].values)

            fig.update_geos(fitbounds="locations", visible=False)

            fig.update_layout(title="Distribuzione geografica", title_x=0.5)

            save_fig_json(fig, out_folder / "region_map.json")

    print(f"Creati dati grafici (JSON) per {yaml_file.stem}")