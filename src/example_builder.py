import csv
from pathlib import Path

CORPUS_MAP = {
    "KIP": "KIP/tsv",
    "ParlaTO": "ParlaTO/tsv",
    "KIPasti": "KIPasti/tsv",
    "ParlaBO": "ParlaBO/tsv",
}


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
        return "<i>Corpus non trovato</i>"

    rows = load_tsv(corpus_path)

    # trova riga target
    target = None
    for r in rows:
        if r["token_id"] == token_id:
            target = r
            break

    if not target:
        return "<i>Token non trovato</i>"

    tus = group_by_tu(rows)
    target_tu = target["tu_id"]

    context_keys = get_context_turns(tus, target_tu)

    html = "<table>"

    for tu in context_keys:
        speaker, text = build_turn(
            tus[tu],
            highlight_token=token_id if tu == target_tu else None
        )

        audio = sd_row.get("audio", "").strip()



        html += f"""
        <tr>
            <td style="width:80px; color:#666">{speaker}</td>
            <td>{text}</td>
        </tr>
        """

    html += "</table>"


    audio_html = ""
    if audio:
        audio_html = f'<a href="{audio}" target="_blank" style="margin-left:10px;">🎧 ascolta occorrenza</a>'

    html += f"""
    <div style="margin-top:8px;">
    <b style="font-size:1rem;">({corpus}, {conv_id})</b>
    {audio_html}
    </div>
    """

    return html