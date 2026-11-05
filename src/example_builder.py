import csv
import re
from pathlib import Path
from urllib.parse import quote

# Pagina HTML della conversazione su KIParla-artifacts
KIPARLA_HTML_URL = "https://kiparla.github.io/KIParla-artifacts/{corpus}/html/{conv_id}"

# Token "puliti": solo lettere/cifre (anche accentate). Restano fuori
# troncamenti (ha~), apostrofi (l'), [PAUSE], sovrapposizioni ecc., che
# nella pagina KIParla sono resi in modo diverso dal TSV.
CLEAN_TOKEN = re.compile(r"^\w+(?:'\w+)*$", re.UNICODE)

# Apostrofi tipografici normalizzati a quello ASCII usato nelle pagine KIParla
APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "`": "'"})


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

def _merged_forms(tu_rows):
    """
    Forme del turno come appaiono nella pagina KIParla.
    Nel TSV "l' orzo" sono due token, nella pagina è "l'orzo": per il
    browser è UNA parola (l'apostrofo tra lettere non separa le parole),
    quindi va ricomposta, altrimenti "orzo" da solo non viene trovato.
    Solo l'elisione (l', dell', un', c': consonante + apostrofo) si
    attacca alla parola dopo; il troncamento (po', mo', fa') no.
    """
    forms = []
    for r in tu_rows:
        form = r["form"].strip().translate(APOSTROPHES)
        if not form:
            continue
        prev = forms[-1] if forms else ""
        if (len(prev) >= 2 and prev.endswith("'")
                and CLEAN_TOKEN.match(prev[:-1])
                and prev[-2].lower() not in "aeiouàèéìòóù"):
            forms[-1] += form
        else:
            forms.append(form)
    return forms

def _clean_runs(tu_rows):
    """Sequenze contigue di token puliti all'interno di un turno."""
    runs, cur = [], []
    for form in _merged_forms(tu_rows):
        if CLEAN_TOKEN.match(form):
            cur.append(form)
        else:
            if cur:
                runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return runs

def _turn_text(tu_rows):
    return " ".join(_merged_forms(tu_rows)).lower()

def _occurs(phrase, text):
    """Occorrenza a parola intera, come la cerca il browser
    (l'apostrofo non è un confine: 'orzo' non sta in "l'orzo")."""
    pat = r"(?<![\w'])" + re.escape(phrase.lower()) + r"(?![\w'])"
    return re.search(pat, text) is not None

def _enc(s):
    # Nei text fragment vanno codificati anche '-', ',' e '&'
    return quote(s, safe="").replace("-", "%2D")

def _pick_start(tus, keys, first, last):
    """
    Primo turno (da first verso last) che ha un inizio univoco:
    la frase non deve comparire in nessun turno precedente della
    conversazione, altrimenti il browser partirebbe da lì.
    Restituisce (indice turno, frase).
    """
    for i in range(first, last + 1):
        runs = _clean_runs(tus[keys[i]])
        before = [_turn_text(tus[k]) for k in keys[:i]]
        for run in runs:
            for n in range(min(4, len(run)), len(run) + 1):
                phrase = " ".join(run[:n])
                if not any(_occurs(phrase, t) for t in before):
                    return i, phrase
    return None, None

def _pick_end(tus, keys, start_i, last):
    """
    Ultimo turno (da last verso start_i) con una fine che non compare
    prima nell'esempio: il browser chiude la selezione alla PRIMA
    occorrenza della fine dopo l'inizio.
    """
    for i in range(last, start_i, -1):
        runs = _clean_runs(tus[keys[i]])
        between = [_turn_text(tus[k]) for k in keys[start_i:i]]
        for run in reversed(runs):
            for n in range(min(3, len(run)), len(run) + 1):
                phrase = " ".join(run[-n:])
                if not any(_occurs(phrase, t) for t in between):
                    return phrase
    return None

def conversation_url(corpus, conv_id, tus, context_keys, target_tu=None):
    """
    URL della conversazione che evidenzia l'intero esempio
    (dal primo all'ultimo turno di contesto) con
    #:~:text=inizio,fine. Se non trova parole affidabili,
    rimanda alla pagina senza evidenziazione.
    """
    base = KIPARLA_HTML_URL.format(corpus=corpus, conv_id=conv_id)

    keys = sorted(tus.keys(), key=lambda x: int(x))
    first = keys.index(context_keys[0])
    last = keys.index(context_keys[-1])

    start_i, start = _pick_start(tus, keys, first, last)
    if start is None:
        return base

    end = _pick_end(tus, keys, start_i, last)
    if end is None:
        return f"{base}#:~:text={_enc(start)}"

    return f"{base}#:~:text={_enc(start)},{_enc(end)}"

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
    conv_url = conversation_url(corpus, conv_id, tus, context_keys, target_tu)
    read_html = (
        f'<a href="{conv_url}" class="read-btn" target="_blank" rel="noopener">'
        f'Leggi la conversazione</a>'
    )

    audio = sd_row.get("audio", "").strip()
    audio_html = ""
    if audio:
        audio_html = f'<a href="{audio}" class="audio-btn" target="_blank" rel="noopener">▶ Ascolta su KIParla</a>'

    return f"""
    <div class="example-card">
        <div class="example-header">
            <span class="conv-id">{corpus}, {conv_id}</span>
            <span class="example-actions">
                {read_html}
                {audio_html}
            </span>
        </div>
        <table class="transcript-table">
            <tbody>
                {table_body}
            </tbody>
        </table>
    </div>
    """