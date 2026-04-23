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

INTERAZIONALI_MAP = {
    "Presa di turno": "Presa di turno",
    "Richiesta di accordo/conferma": "Richiesta di accordo/conferma",
    "Manifestazione di accordo": "Accordo",
    "Conferma dell'attenzione": "Conferma dell'attenzione",
    "Interruzione": "Interruzione",
    "Cessione del turno": "Cessione del turno",
    "Marcatura della conoscenza condivisa" : "Marcatura della conoscenza condivisa" ,
    "Richiesta di attenzione": "Richiesta di attenzione",
    "Strategie di cortesia": "Strategia di cortesia"
}

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


# === NORMALIZE ===
def normalize_token(x):
    return re.sub(r"[^\wàèéìòù']+$", "", x).strip()

# === BUILD KIPARLA INDEX ===
def build_kiparla_index():
    index = {}

    for sub in GITHUB_ROOT.iterdir():
        if not sub.is_dir() or sub.name not in VALID_CORPORA:
            continue

        tsv_folder = sub / "tsv"

        if tsv_folder.exists():
            for file in tsv_folder.glob("*.tsv"):
                conv_id = file.stem.replace(".vert", "")
                index[conv_id] = (file, sub.name)

    return index

# === BUILD METADATA INDEX ===
def build_metadata_index():
    metadata = {}

    for corpus in VALID_CORPORA:
        corpus_path = GITHUB_ROOT / corpus

        conv_file = corpus_path / "metadata" / "conversations.tsv"
        part_file = corpus_path / "metadata" / "participants.tsv"

        conv_data = {}
        part_data = {}

        if conv_file.exists():
            with open(conv_file, encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    conv_data[row["code"]] = row

        if part_file.exists():
            with open(part_file, encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    part_data[row["code"]] = row

        metadata[corpus] = {
            "conversations": conv_data,
            "participants": part_data
        }

    return metadata

# === TOKEN MATCH ===
def find_token_id(tsv_path, kwic, left_ctx, right_ctx):
    kwic = str(kwic).strip()
    if not kwic:
        return "#CHECK", "#CHECK", "_"

    with open(tsv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        elements = [
            (x["token_id"], normalize_token(x["form"]), x.get("speaker", "_"))
            for x in reader
            if x["type"] == "linguistic"
        ]

    kwic = normalize_token(kwic)
    kwic_tokens = kwic.split()

    # === TOKEN SINGOLO ===
    if len(kwic_tokens) == 1:
        kwic_single = kwic_tokens[0]
        possibilities = {}

        for i, (tid, form, speaker) in enumerate(elements):
            if form == kwic_single:
                left_window = elements[max(0, i - len(left_ctx)):i]
                right_window = elements[i + 1:i + 1 + len(right_ctx)]

                left_score = sum(1 for _, el, _ in left_window if el in left_ctx)
                right_score = sum(1 for _, el, _ in right_window if el in right_ctx)

                possibilities[(tid, tid, speaker)] = left_score + right_score

        if not possibilities:
            return "#CHECK", "#CHECK", "_"

        best = sorted(possibilities.items(), key=lambda x: -x[1])[0][0]
        return best  # (id, span, speaker)

    # === MWE ===
    k_len = len(kwic_tokens)
    possibilities = {}

    for i in range(len(elements) - k_len + 1):
        window = elements[i:i + k_len]
        forms = [w[1] for w in window]

        if forms == kwic_tokens:
            ids = [tid for tid, _, _ in window]
            if not ids:
                continue

            start_id = ids[0]
            span = "|".join(ids)
            speaker = window[0][2]

            left_window = elements[max(0, i - len(left_ctx)):i]
            right_window = elements[i + k_len:i + k_len + len(right_ctx)]

            left_score = sum(1 for _, el, _ in left_window if el in left_ctx)
            right_score = sum(1 for _, el, _ in right_window if el in right_ctx)

            possibilities[(start_id, span, speaker)] = left_score + right_score

    if not possibilities:
        return "#CHECK", "#CHECK", "_"

    best = sorted(possibilities.items(), key=lambda x: -x[1])[0][0]
    return best

# === COLONNE FUNZIONI ===
def segn_disc_from_funcs(inter, meta, cog):
    return "yes" if any(v != "_" for v in [inter, meta, cog]) else "no"

def build_multi(row, columns, mapping):
    values = []
    for col in columns:
        if row.get(col) == "1":
            values.append(mapping[col])
    return "|".join(values) if values else "_"

# === INIT ===
kiparla_index = build_kiparla_index()
metadata_index = build_metadata_index()

# === PROCESSING ===
for csv_file in CSV_FOLDER.glob("*.csv"):
    output_file = OUTPUT_FOLDER / (csv_file.stem + ".tsv")

    with open(csv_file, encoding="utf-8-sig") as fin, \
         open(output_file, "w", encoding="utf-8", newline="") as fout:

        reader = csv.DictReader(fin, delimiter=";")

        fieldnames = [
            "corpus", "conv_id", "token_id", "token_span", "speaker_id", "audio",

            # conversations metadata
            "type", "duration", "participants-number",
            "participants-relationship", "moderator",
            "topic", "year", "collection-point",

            # speaker metadata
            "occupation", "gender", "school-region", "age-range",

            # annotation
            "SegnDisc", "Func:Interazionale",
            "Func:Metatestuale", "Func:Cognitiva",

            "left", "form", "right",
        ]

        writer = csv.DictWriter(fout, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()

        for row in reader:
            conv = row["Reference"]

            if conv not in kiparla_index:
                token_id, token_span, speaker_id = "#CHECK", "#CHECK", "_"
                corpus = "_"
            else:
                tsv_path, corpus = kiparla_index[conv]

                left_ctx = ''.join(row["Left"].split("//")).split()
                kwic = row["KWIC"]
                right_ctx = ''.join(row["Right"].split("//")).split()

                token_id, token_span, speaker_id = find_token_id(
                    tsv_path, kwic, left_ctx, right_ctx
                )

            corpus_meta = metadata_index.get(corpus, {})
            conv_meta = corpus_meta.get("conversations", {}).get(conv, {})
            speaker_meta = corpus_meta.get("participants", {}).get(speaker_id, {})

            func_inter = build_multi(row, INTERAZIONALI_MAP.keys(), INTERAZIONALI_MAP)
            func_meta = build_multi(row, METATESTUALI_MAP.keys(), METATESTUALI_MAP)
            func_cog = build_multi(row, COGNITIVE_MAP.keys(), COGNITIVE_MAP)

            out_row = {
                "corpus": corpus,
                "conv_id": conv,
                "token_id": token_id,
                "token_span": token_span,
                "speaker_id": speaker_id,
                "audio": row["annotation.audio_file"],

                # conversations
                "type": conv_meta.get("type", "_"),
                "duration": conv_meta.get("duration", "_"),
                "participants-number": conv_meta.get("participants-number", "_"),
                "participants-relationship": conv_meta.get("participants-relationship", "_"),
                "moderator": conv_meta.get("moderator", "_"),
                "topic": conv_meta.get("topic", "_"),
                "year": conv_meta.get("year", "_"),
                "collection-point": conv_meta.get("collection-point", "_"),

                # speaker
                "occupation": speaker_meta.get("occupation", "_"),
                "gender": speaker_meta.get("gender", "_"),
                "school-region": speaker_meta.get("school-region", "_"),
                "age-range": speaker_meta.get("age-range", "_"),

                # annotation
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