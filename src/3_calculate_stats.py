import csv
import yaml
from pathlib import Path
from collections import defaultdict

# =========================
# PATH
# =========================
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

INPUT_DIR = PROJECT_ROOT / "data" / "tsv"
COSI_DIR = PROJECT_ROOT / "cosi"              # qui stanno i nome_sd.yaml con nOccTot
OUTPUT_DIR = PROJECT_ROOT / "cosi" / "stats"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# CORPUS DATA
# =========================
with open(PROJECT_ROOT / "project_materials" / "corpus-data.yaml", encoding="utf-8") as f:
    corpus_data = yaml.safe_load(f)

# =========================
# NORMALIZZAZIONE (CRITICA)
# =========================
def norm(x):
    return str(x).strip().lower().replace(" ", "")


AGE_MAP = {
    "16-20": "16-20",
    "21-25": "21-30",
    "26-30": "21-30",

    "31-35": "31-40",
    "36-40": "31-40",

    "41-45": "41-50",
    "46-50": "41-50",

    "51-55": "51-60",
    "56-60": "51-60",

    "61-65": "61-70",
    "66-70": "61-70",

    "71-75": ">71",
    "76-80": ">71",
    "81-85": ">71",
    "over85": ">71",
    "over 85": ">71"
}

CORPUS_AGE = defaultdict(int)

for k, v in corpus_data["age-range"].items():
    bucket = AGE_MAP.get(norm(k))
    if bucket is None:
        continue
    CORPUS_AGE[bucket] += v

# =========================
# MACROAREE
# =========================
MACROAREA = {
    # Nord
    "emilia-romagna": "Nord",
    "piemonte": "Nord",
    "lombardia": "Nord",
    "veneto": "Nord",
    "friuli-venezia-giulia": "Nord",
    "valle-d-aosta": "Nord",
    "trentino-alto-adige": "Nord",
    "liguria": "Nord",
    # Centro
    "lazio": "Centro",
    "marche": "Centro",
    "toscana": "Centro",
    "umbria": "Centro",
    # Sud e Isole
    "puglia": "Sud e Isole",
    "sicilia": "Sud e Isole",
    "calabria": "Sud e Isole",
    "campania": "Sud e Isole",
    "basilicata": "Sud e Isole",
    "sardegna": "Sud e Isole",
    "abruzzo": "Sud e Isole",
    "molise": "Sud e Isole",
}
AREA_ORDER = ["Nord", "Centro", "Sud e Isole"]

# Token del corpus per macroarea = somma dei token di TUTTE le regioni dell'area
CORPUS_AREA = defaultdict(int)
for k, v in corpus_data["region"].items():
    area = MACROAREA.get(norm(k))
    if area:
        CORPUS_AREA[area] += v


def norm_age(x):
    return AGE_MAP.get(norm(x), norm(x))

def canon(field, key):
    if field == "age-range":
        return norm_age(key)
    return key

# =========================
# TOTAL CORPUS
# =========================
def get_total(field, key):

    key = canon(field, key)

    if field == "type":
        v = corpus_data["type"].get(key)
        return v["freq"] if v else None

    elif field == "region":
        return corpus_data["region"].get(key)

    elif field == "age-range":
        return CORPUS_AGE.get(key)

    elif field == "macroarea":
        return CORPUS_AREA.get(key)

    return None

def fpmw(count, total):
    return (count / total) * 1_000_000 if total else 0

# =========================
# CAMPIONAMENTO / PROIEZIONE
# =========================
# nOccTot letto da tutti i yaml dei segnali in cosi/,
# indicizzato sia per nome del tsv (campo "file") sia per nome del yaml
N_OCC_BY_FILE = {}
N_OCC_BY_STEM = {}

for p in COSI_DIR.glob("*.yaml"):
    with open(p, encoding="utf-8") as f:
        d = yaml.safe_load(f) or {}
    if not isinstance(d, dict) or d.get("nOccTot") is None:
        continue
    N_OCC_BY_STEM[p.stem] = d["nOccTot"]
    if d.get("file"):
        N_OCC_BY_FILE[Path(str(d["file"])).name] = d["nOccTot"]


def get_sampling(tsv_file, nrows):
    """
    Se nOccTot > righe del tsv, il tsv è un campione:
    fattore di proiezione = nOccTot / righe estratte.
    """
    n_occ_tot = N_OCC_BY_FILE.get(tsv_file.name, N_OCC_BY_STEM.get(tsv_file.stem))

    try:
        n_occ_tot = int(n_occ_tot)
    except (TypeError, ValueError):
        n_occ_tot = None

    is_sample = n_occ_tot is not None and nrows > 0 and n_occ_tot > nrows
    factor = n_occ_tot / nrows if is_sample else 1.0

    return {
        "nOccTot": n_occ_tot,
        "nRows": nrows,
        "is_sample": is_sample,
        "factor": factor
    }

def make_entry(field, key, count, factor):
    """count = conteggio reale; fpmw calcolata sul conteggio proiettato."""
    entry = {"count": count}
    count_proj = count * factor

    if factor != 1.0:
        entry["count_proj"] = round(count_proj, 2)

    total = get_total(field, key)
    if total:
        entry["fpmw"] = fpmw(count_proj, total)

    return entry

# =========================
# FUNZIONI
# =========================
FUNC_MAP = {
    "Func:Interazionale": "Interazionale",
    "Func:Metatestuale": "Metatestuale",
    "Func:Cognitiva": "Cognitiva"
}

META_ALL = [
    "type",
    "participants-relationship",
    "topic",
    "year",
    "occupation",
    "gender",
    "region",
    "age-range"
]

# =========================
# UTILS
# =========================
def is_empty(v):
    return v is None or v == "" or v == "_"

def is_sd(row):
    return row.get("SegnDisc", "").strip().lower() == "yes"

# =========================
# PROCESSING
# =========================
for tsv_file in INPUT_DIR.glob("*.tsv"):

    ntokens = 0
    nSD = 0

    macro = {v: 0 for v in FUNC_MAP.values()}
    micro = {v: defaultdict(int) for v in FUNC_MAP.values()}
    metadata_counts = {k: defaultdict(int) for k in META_ALL}

    with open(tsv_file, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:

            ntokens += 1

            if not is_sd(row):
                continue

            nSD += 1

            # =====================
            # METADATA (SD ONLY)
            # =====================
            for m in META_ALL:
                val = row.get(m)

                if is_empty(val):
                    continue

                val = canon(m, val)
                metadata_counts[m][val] += 1

            # =====================
            # MACRO + MICRO
            # =====================
            for col, macro_name in FUNC_MAP.items():

                val = row.get(col, "_")

                if is_empty(val):
                    continue

                macro[macro_name] += 1

                for label in val.split("|"):
                    label = label.strip()
                    if not is_empty(label):
                        micro[macro_name][label] += 1

    # =========================
    # SAMPLING
    # =========================
    sampling = get_sampling(tsv_file, ntokens)
    factor = sampling["factor"]

    # =========================
    # MACROAREE (dalle regioni)
    # =========================
    area_counts = {a: 0 for a in AREA_ORDER}
    for reg, c in metadata_counts["region"].items():
        area = MACROAREA.get(norm(reg))
        if area:
            area_counts[area] += c

    # =========================
    # OUTPUT METADATA
    # =========================
    metadata_out = {}

    for field, values in metadata_counts.items():
        metadata_out[field] = {
            k: make_entry(field, k, v, factor)
            for k, v in values.items()
        }

    metadata_out["macroarea"] = {
        a: make_entry("macroarea", a, c, factor)
        for a, c in area_counts.items()
    }

    micro = {k: dict(v) for k, v in micro.items()}

    # =========================
    # OUTPUT
    # =========================
    counts = {"ntokens": ntokens, "nSD": nSD}
    if sampling["is_sample"]:
        counts["nSD_proj"] = round(nSD * factor, 2)

    out = {
        "file": tsv_file.name,
        "sampling": sampling,
        "counts": counts,
        "macrofunctions_SD": macro,
        "microfunctions_SD": micro,
        "metadata_SD": metadata_out
    }

    out_file = OUTPUT_DIR / (tsv_file.stem + ".yaml")

    with open(out_file, "w", encoding="utf-8") as f:
        yaml.dump(out, f, allow_unicode=True, sort_keys=False)

    # diagnostica: così vedi subito se nOccTot è stato trovato
    if sampling["nOccTot"] is None:
        tag = "  [nOccTot NON trovato]"
    elif sampling["is_sample"]:
        tag = f"  [campione: {ntokens} su {sampling['nOccTot']}, ×{factor:.2f}]"
    else:
        tag = f"  [completo: {ntokens} righe, nOccTot {sampling['nOccTot']}]"
    print(f"Creato: {out_file.name}{tag}")