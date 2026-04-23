import yaml
import pandas as pd
from pathlib import Path
import plotly.express as px

# =========================
# PATH
# =========================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
YAML_DIR = PROJECT_ROOT / "cosi" / "stats"
OUT_DIR = PROJECT_ROOT / "cosi" / "imgs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

INVALID_VALUES = {"unknown", "n/a", "N/A", "===NONE===", "none", ""}

def clean_value(x):
    if x is None:
        return None

    x = str(x).strip().lower()

    if x in INVALID_VALUES:
        return None

    return x

# =========================
# ORDINE AGE
# =========================
AGE_ORDER = [
    "16-20", "21-25", "26-30", "31-35",
    "36-40", "41-45", "46-50", "51-55",
    "56-60", "61-65", "66-70", "71-75",
    "76-80", "81-85", "over85"
]

# =========================
# MAPPA REGIONI (se serve normalizzazione)
# =========================
REGION_LABEL = {
      "emilia-romagna": "Emilia-Romagna",
      "piemonte" : "Piemonte",
      "puglia" : "Puglia",
      "lombardia": "Lombardia",
      "sicilia": "Sicilia",
      "calabria": "Calabria",
      "veneto": "Veneto",
      "campania": "Campania",
      "basilicata": "Basilicata",
      "lazio": "Lazio",
      "marche" : "Marche",
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

TYPE_MAP = {
    "free-conversation": "Conversazione libera",
    "lecture": "Lezione",
    "exam": "Esame",
    "semistructured-interview": "Intervista",
    "office-hours": "Ricevimento Studenti"
}

def clean_type(x):
    x = clean_value(x)
    if not x:
        return None
    return TYPE_MAP.get(x, x)

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
                "type": k,
                "count": v.get("count", 0),
                "fpmw": v.get("fpmw", 0)
            }
            for k, v in metadata["type"].items()
        ])

        fig = px.bar(
            df,
            x="type",
            y="fpmw",
            hover_data={"count": True, "fpmw": True, "type": True}
        )

        fig.write_html(out_folder / "type.html")

    # =========================
    # 2. AGE BARPLOT (ordinato)
    # =========================
    if "age-range" in metadata:

        df = pd.DataFrame([
            {
                "age": k,
                "count": v.get("count", 0),
                "fpmw": v.get("fpmw", 0)
            }
            for k, v in metadata["age-range"].items()
        ])

        df["age"] = pd.Categorical(df["age"], categories=AGE_ORDER, ordered=True)
        df = df.sort_values("age")

        fig = px.bar(
            df,
            x="age",
            y="fpmw",
            hover_data={"count": True, "fpmw": True, "age": True}
        )

        fig.write_html(out_folder / "age.html")

    # =========================
    # 3. REGION MAP (HEATMAP ITALIA)
    # =========================
    if "region" in metadata:

        df = pd.DataFrame([
            {
                "region": REGION_LABEL.get(k, k),
                "count": v.get("count", 0),
                "fpmw": v.get("fpmw", 0)
            }
            for k, v in metadata["region"].items()
        ])

        fig = px.choropleth(
            df,
            geojson="https://raw.githubusercontent.com/openpolis/geojson-italy/master/geojson/limits_IT_regions.geojson",
            featureidkey="properties.reg_name",
            locations="region",
            color="fpmw",
            hover_data={"count": True, "fpmw": True},
            color_continuous_scale="Reds"
        )

        fig.update_geos(fitbounds="locations", visible=False)

        fig.write_html(out_folder / "region_map.html")

    print(f"Creato grafici per {yaml_file.stem}")