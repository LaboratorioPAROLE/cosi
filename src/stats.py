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
    "over85": "over85",
    "over 85": "over85"
}

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
        return corpus_data["age-range"].get(key)

    return None

def fpmw(count, total):
    return (count / total) * 1_000_000 if total else 0

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
    # OUTPUT METADATA
    # =========================
    metadata_out = {}

    for field, values in metadata_counts.items():

        metadata_out[field] = {}

        for k, v in values.items():

            entry = {"count": v}

            total = get_total(field, k)
            if total:
                entry["fpmw"] = fpmw(v, total)

            metadata_out[field][k] = entry

    micro = {k: dict(v) for k, v in micro.items()}

    # =========================
    # OUTPUT
    # =========================
    out = {
        "file": tsv_file.name,
        "counts": {
            "ntokens": ntokens,
            "nSD": nSD
        },
        "macrofunctions_SD": macro,
        "microfunctions_SD": micro,
        "metadata_SD": metadata_out
    }

    out_file = OUTPUT_DIR / (tsv_file.stem + ".yaml")

    with open(out_file, "w", encoding="utf-8") as f:
        yaml.dump(out, f, allow_unicode=True, sort_keys=False)

    print(f"Creato: {out_file}")