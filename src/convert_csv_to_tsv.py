import os
import csv
from pathlib import Path
import re


# === PATH ===
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent                  
GITHUB_ROOT = PROJECT_ROOT.parent               

DATA_DIR = PROJECT_ROOT / "data"

CSV_FOLDER = DATA_DIR / "csv"
OUTPUT_FOLDER = DATA_DIR / "tsv"

VALID_CORPORA = {"KIP", "ParlaTO", "ParlaBO", "KIPasti"}

# === COLONNE ===

INTERAZIONALI = [
    "Presa di turno",
    "Richiesta di accordo/conferma",
    "Manifestazione di accordo",
    "Conferma dell'attenzione",
    "Interruzione",
    "Cessione del turno",
    "Marcatura della conoscenza condivisa",
    "Richiesta di attenzione",
    "Strategie di cortesia"
]

METATESTUALI_MAP = {
    "Gestione del topic: introduzione o ripresa di topic": "Introduzione o ripresa del topic",
    "Chiusura di un topic": "Chiusura del topic",
    "Prolettico, marca di formulazione: ecco": "Prolettico",
    "Riformulazione": "Riformulazione",
    "Marcatura di citazione/discorso riportato": "Citazione/Discorso Riportato",
    "Esemplificazione": "Esemplificazione",
    "Filler, riempimento dei tempi di formulazione": "Filler",
    "General extenders e marche di generalizzazione": "Marca di generalizzazione"
}

COGNITIVE_MAP = {
    "Marcatura dell'inferenza": "Marcatura dell'inferenza",
    "Modulazione del grado di confidenza del parlante": "Modulazione del grado di confidenza",
    "Approssimazione": "Approssimazione",
    "Specificazione": "Specificazione",
    "Attenuazione": "Attenuazione",
    "Intensificazione": "Intensificazione"
}

# === COSTRUZIONE INDICE KIPARLA ===
def build_kiparla_index():
    index = {}

    for sub in GITHUB_ROOT.iterdir():
        if not sub.is_dir():
            continue

        if sub.name not in VALID_CORPORA:
            continue

        tsv_folder = sub / "tsv"

        if tsv_folder.exists():
            for file in tsv_folder.glob("*.tsv"):
                conv_id = file.stem.replace(".vert", "")
                index[conv_id] = (file, sub.name)

    return index


def normalize_token(x):
    return re.sub(r"[^\wàèéìòù']+$", "", x).strip()

# === TOKEN MATCH ===
def find_token_id(tsv_path, kwic, left_ctx, right_ctx):
    kwic = str(kwic).strip()

    if not kwic:
        return "#CHECK", "#CHECK"

    
    with open(tsv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        elements = [(x["token_id"], x["form"]) for x in reader if x["type"] == "linguistic"]

    kwic = normalize_token(str(kwic))
    kwic_tokens = kwic.split()

    # =========================
    # CASO 1: TOKEN SINGOLO
    # =========================
    if len(kwic_tokens) == 1:
        kwic_single = kwic_tokens[0]
        possibilities = {}

        for i, (tid, form) in enumerate(elements):
            if form == kwic_single:
                left_window = elements[max(0, i - len(left_ctx)):i]
                right_window = elements[i + 1:i + 1 + len(right_ctx)]

                left_score = sum(1 for _, el in left_window if el in left_ctx)
                right_score = sum(1 for _, el in right_window if el in right_ctx)

                possibilities[tid] = left_score + right_score

        if not possibilities:
            return "#CHECK", "#CHECK"

        best = sorted(possibilities.items(), key=lambda x: -x[1])[0][0]

        # span = id singolo
        return best, best

    # =========================
    # CASO 2: MWE
    # =========================
    k_len = len(kwic_tokens)
    possibilities = {}

    for i in range(len(elements) - k_len + 1):
        window = elements[i:i + k_len]
        forms = [w[1] for w in window]

        if forms == kwic_tokens:
            ids = [tid for tid, _ in window]

            start_id = ids[0]
            span = "|".join(ids)

            left_window = elements[max(0, i - len(left_ctx)):i]
            right_window = elements[i + k_len:i + k_len + len(right_ctx)]

            left_score = sum(1 for _, el in left_window if el in left_ctx)
            right_score = sum(1 for _, el in right_window if el in right_ctx)

            possibilities[(start_id, span)] = left_score + right_score

    if not possibilities:
        return "#CHECK", "#CHECK"

    best = sorted(possibilities.items(), key=lambda x: -x[1])[0][0]
    return best

# === FUNZIONI COLONNE ===
def segn_disc_from_funcs(inter, meta, cog):
    return "yes" if any(v != "_" for v in [inter, meta, cog]) else "no"


def build_multi(row, columns, mapping=None):
    values = []
    for col in columns:
        if row.get(col) == "1":
            values.append(mapping[col] if mapping else col)
    return "|".join(values) if values else "_"

kiparla_index = build_kiparla_index()

# === PROCESSING ===
for csv_file in CSV_FOLDER.glob("*.csv"):
    output_file = OUTPUT_FOLDER / (csv_file.stem + ".tsv")

    with open(csv_file, encoding="utf-8-sig") as fin, \
         open(output_file, "w", encoding="utf-8", newline="") as fout:

        reader = csv.DictReader(fin, delimiter=";")

        fieldnames = [
            "corpus", "conv_id", "token_id", "token_span", "audio",
            "SegnDisc", "Func:Interazionale",
            "Func:Metatestuale", "Func:Cognitiva", "left", "form", "right",
        ]

        writer = csv.DictWriter(fout, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()


        for row in reader:
            conv = row["Reference"]

            if conv not in kiparla_index:
                token_id = "#CHECK"
                corpus = "_"
            else:
                tsv_path, corpus = kiparla_index[conv]

                left_ctx = ''.join(row["Left"].split("//")).split()
                kwic = row["KWIC"]
                right_ctx = ''.join(row["Right"].split("//")).split()

                token_id, token_span = find_token_id(tsv_path, kwic, left_ctx, right_ctx)

            func_inter = build_multi(row, INTERAZIONALI)
            func_meta = build_multi(row, METATESTUALI_MAP.keys(), METATESTUALI_MAP)
            func_cog = build_multi(row, COGNITIVE_MAP.keys(), COGNITIVE_MAP)

            out_row = {
                "corpus": corpus,
                "conv_id": conv,
                "token_id": token_id,
                "token_span": token_span,
                "audio":row["annotation.audio_file"],
                "SegnDisc": segn_disc_from_funcs(func_inter, func_meta, func_cog),
                "Func:Interazionale": func_inter,
                "Func:Metatestuale": func_meta,
                "Func:Cognitiva": func_cog,
                "left": row["Left"],
                "form": row["KWIC"],
                "right": row["Right"]
            }
            
            writer.writerow(out_row)

    print(f"Creato: {output_file}")