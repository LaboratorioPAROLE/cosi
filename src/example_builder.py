import csv
from pathlib import Path

CORPUS_MAP = {
    "KIP": "KIP/tsv",
    "ParlaTO": "ParlaTO/tsv",
    "KIPasti": "KIPasti/tsv",
    "ParlaBO": "ParlaBO/tsv",
}

# Palette di 5 colori basilari per i parlanti
SPEAKER_PALETTE = [
    "#2b6cb0",  # Blu
    "#2f855a",  # Verde
    "#c53030",  # Rosso / Mattone
    "#805ad5",  # Viola
    "#dd6b20",  # Arancione
]

def load_tsv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))

def group_by_tu(rows):
    tus = {}
    for r in rows:
        tu = r["tu_id"]
        tus.setdefault(tu, []).append(r)
    return tus

def build_turn(tu_rows, highlight_token=None):
    speaker = tu_rows[0]["speaker"]
    text = []

    for r in tu_rows:
        token = r["form"]
        if highlight_token and r["token_id"] == highlight_token:
            token = f"<b>{token}</b>"
        text.append(token)

    return speaker, " ".join(text)

def get_context_turns(tus, target_tu, window=2):
    keys = sorted(tus.keys(), key=lambda x: int(x))
    idx = keys.index(target_tu)

    start = max(0, idx - window)
    end = min(len(keys), idx + window + 1)

    return keys[start:end]

def build_example(sd_row, corpus_root):

    corpus = sd_row["corpus"]
    conv_id = sd_row["conv_id"]
    token_id = sd_row["token_id"]

    corpus_path = Path(corpus_root).parent / CORPUS_MAP[corpus] / f"{conv_id}.vert.tsv"

    if not corpus_path.exists():
        return '<div class="example-card error"><i>Corpus non trovato</i></div>'

    rows = load_tsv(corpus_path)

    # trova riga target
    target = None
    for r in rows:
        if r["token_id"] == token_id:
            target = r
            break

    if not target:
        return '<div class="example-card error"><i>Token non trovato</i></div>'

    tus = group_by_tu(rows)
    target_tu = target["tu_id"]

    context_keys = get_context_turns(tus, target_tu)

    # Dizionario per assegnare un colore unico a ciascun parlante nell'esempio
    speaker_colors = {}

    table_rows = []
    for tu in context_keys:
        speaker, text = build_turn(
            tus[tu],
            highlight_token=token_id if tu == target_tu else None
        )

        # Mappatura del colore del parlante (fino a 5 colori)
        if speaker not in speaker_colors:
            color_index = len(speaker_colors) % len(SPEAKER_PALETTE)
            speaker_colors[speaker] = SPEAKER_PALETTE[color_index]

        spk_color = speaker_colors[speaker]
        is_target = (tu == target_tu)
        row_class = ' class="focus"' if is_target else ''

        table_rows.append(f"""
        <tr{row_class}>
            <td class="speaker-col" style="color: {spk_color};">{speaker}</td>
            <td class="text-col">{text}</td>
        </tr>""")

    table_body = "\n".join(table_rows)

    # Gestione Audio e Intestazione
    audio = sd_row.get("audio", "").strip()
    audio_html = ""
    if audio:
        audio_html = f'<a href="{audio}" class="audio-btn" target="_blank" rel="noopener">▶ Ascolta su KIParla</a>'

    return f"""
    <div class="example-card">
        <div class="example-header">
            <span class="conv-id">{corpus}, {conv_id}</span>
            {audio_html}
        </div>
        <table class="transcript-table">
            <tbody>
                {table_body}
            </tbody>
        </table>
    </div>
    """