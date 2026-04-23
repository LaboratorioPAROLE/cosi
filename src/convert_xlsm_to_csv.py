import pandas as pd
import os

input_folder = "../data/xlsm"
output_folder = "../data/csv"

os.makedirs(output_folder, exist_ok=True)

# parole chiave che fanno scartare la prima riga
skip_first_row_keywords = [
    "Non SD",
    "Macrofunzione interazionale",
    "Macrofunzione metatestuale",
    "Macrofunzione cognitiva"
]

def build_header(row1, row2):
    header = []

    # controllo globale: se nella prima riga appare una keyword → ignorala
    skip_row1 = any(
        any(kw in str(cell) for kw in skip_first_row_keywords)
        for cell in row1
    )

    for c1, c2 in zip(row1, row2):
        c1 = str(c1).strip() if pd.notna(c1) else ""
        c2 = str(c2).strip() if pd.notna(c2) else ""

        if skip_row1:
            header.append(c2 if c2 else c1)
        else:
            if c1 and not c2:
                header.append(c1)
            elif c2 and not c1:
                header.append(c2)
            elif c1 and c2:
                # puoi cambiare questa logica se non vuoi concatenare
                header.append(f"{c1}_{c2}")
            else:
                header.append("")

    return header


for filename in os.listdir(input_folder):
    if filename.endswith((".xlsm", ".xlsx")):
        file_path = os.path.join(input_folder, filename)

        # leggi senza header
        df = pd.read_excel(file_path, header=None, engine="openpyxl")

        # prendi prime due righe
        row1 = df.iloc[0]
        row2 = df.iloc[1]

        # costruisci header
        new_header = build_header(row1, row2)

        # dati senza le prime due righe
        df_data = df.iloc[2:].copy()
        df_data.columns = new_header

        # nome output
        output_name = os.path.splitext(filename)[0] + ".csv"
        output_path = os.path.join(output_folder, output_name)

        # salva CSV con encoding corretto
        df_data.to_csv(output_path, sep=";", index=False, encoding="utf-8-sig")

        print(f"Creato: {output_path}")