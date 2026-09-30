import yaml
import json
import csv
from pathlib import Path
from example_builder import build_example
import shutil

# =========================
# PATH
# =========================
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

SIGNALS_DIR = PROJECT_ROOT / "cosi"
STATS_DIR = PROJECT_ROOT / "cosi" / "stats"
TSV_DIR = PROJECT_ROOT / "data" / "tsv"

DOCS_DIR = PROJECT_ROOT / "docs"
SIGNAL_PAGES_DIR = DOCS_DIR / "segnali"

DOCS_DIR.mkdir(parents=True, exist_ok=True)
SIGNAL_PAGES_DIR.mkdir(parents=True, exist_ok=True)

DOCS_IMGS_DIR = DOCS_DIR / "imgs"

# =========================
# COLORI
# =========================
COLOR_MAP = {
    "Interazionale": "#ffe0cc",
    "Metatestuale": "#d4f5d4",
    "Cognitiva": "#d6eaff"
}

# Versione di Plotly.js caricata da CDN, una sola volta per pagina
PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"

# =========================
# HTML BASE
# =========================
def base_html(title, body, base_path=""):

    return f"""
<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>

<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap" rel="stylesheet">

<!-- Plotly.js caricato una sola volta da CDN -->
<script src="{PLOTLY_CDN}"></script>

<style>
body {{
    margin: 0;
    font-family: 'Inter', sans-serif;
    background: #f5f7fa;
    color: #1a1a1a;
}}

.container {{
    max-width: 1100px;
    margin: auto;
    padding: 2rem;
}}

.card {{
    background: white;
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 10px 25px rgba(0,0,0,0.05);
}}

/* Titoli nelle card: coerenti con le pagine statiche */
.card h2 {{
    margin-top: 0;
    color: #1e3c72;
}}

.card h3 {{
    margin-top: 0;
    color: #1e3c72;
    border-bottom: 2px solid #eef1f6;
    padding-bottom: 0.6rem;
}}

table {{
    width: 100%;
    border-collapse: collapse;
}}

th, td {{
    padding: 10px;
    border-bottom: 1px solid #eee;
    text-align: left;
}}

tr:hover {{
    background: #f9fbff;
}}

input {{
    width: 100%;
    box-sizing: border-box;
    padding: 0.9rem;
    border-radius: 12px;
    border: 1px solid #ddd;
    margin-bottom: 1rem;
    font-size: 1rem;
}}

.badge {{
    background: #2a5298;
    color: white;
    padding: 3px 8px;
    border-radius: 8px;
    font-size: 12px;
}}

.plot-container {{
    width: 100%;
    height: 400px;
}}

.example {{
    padding: 10px 0;
    border-bottom: 2px solid #ddd;
    font-size: 0.95rem;
}}

.example:last-child {{
    border-bottom: none;
}}

.audio {{
    margin-left: 8px;
    text-decoration: none;
}}

.header {{
    background: #ffffff;
    border-bottom: 1px solid #e5e5e5;
}}

/* Riga logo: [UNISA + DipSUM] | COSÌ | [PAROLE] */
.brand {{
    --unisa-h: 100px;
    --dipsum-w: 130px;
    --stack-gap: 5px;
    --side-gap: clamp(16px, 6vw, 100px);   /* distanza dal logo COSÌ (non usata con allineamento centrato) */
    --side-lift: 30px;                     /* quanto salgono dal fondo */
    --parole-scale: 1.08;                  /* 1 = uguale a UNISA+DipSUM */

    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: end;
    padding: 0.6rem 1.5rem 0 1.5rem;
}}

.brand img {{ display: block; }}

.brand .logo-main {{
    height: 250px;
    width: auto;
    margin-bottom: 8px;
    grid-column: 2;
}}

.brand .side {{ margin-bottom: var(--side-lift); }}

.brand .side-left {{
    grid-column: 1;
    justify-self: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--stack-gap);
}}

.brand .side-right {{
    grid-column: 3;
    justify-self: center;
}}

.brand .logo-unisa  {{ height: var(--unisa-h); width: auto; }}
.brand .logo-dipsum {{ width: var(--dipsum-w); height: auto; }}

/* PAROLE = (UNISA + spazio + DipSUM) * scala. 3.556 = proporzione 2560:720 di DipSUM */
.brand .logo-parole {{
    height: calc((var(--unisa-h) + var(--stack-gap) + var(--dipsum-w) / 3.556) * var(--parole-scale));
    width: auto;
}}

@media (max-width: 700px) {{
    .brand {{
        --unisa-h: 55px;
        --dipsum-w: 72px;
        --stack-gap: 4px;
        --side-lift: 12px;
        padding: 0.6rem 0.8rem 0 0.8rem;
    }}
    .brand .logo-main {{ height: 140px; }}
}}

.navbar {{
    display: flex;
    justify-content: center;
    gap: 24px;
    padding: 6px 0 10px 0;
    background: white;
    margin-top: 6px;
}}

.navbar a {{
    text-decoration: none;
    color: #095775;
    font-weight: 500;
    font-size: 0.95rem;
}}

.navbar a:hover {{
    color: #b51700;
}}

.dropdown {{
    position: relative;
}}

.dropdown-content {{
    display: none;
    position: absolute;
    top: 22px;
    background: white;
    min-width: 160px;
    border: 1px solid #eee;
    box-shadow: 0 8px 20px rgba(0,0,0,0.08);
    z-index: 100;
}}

.dropdown-content a {{
    display: block;
    padding: 10px;
    font-size: 0.9rem;
}}

.dropdown-content a:hover {{
    background: #f5f7fa;
}}

.dropdown:hover .dropdown-content {{
    display: block;
}}

/* Ricerca avanzata */
.adv-toggle {{
    background: none;
    border: none;
    padding: 0;
    color: #095775;
    font-family: inherit;
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
}}

.adv-toggle:hover {{
    color: #b51700;
}}

.adv-panel {{
    display: none;
    margin-top: 1rem;
}}

.adv-panel label {{
    display: block;
    font-size: 0.85rem;
    color: #555;
    margin-bottom: 4px;
}}

.adv-panel input {{
    margin-bottom: 0;
}}

/* Intestazioni ordinabili */
th.sortable {{
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
}}

th.sortable:hover {{
    color: #b51700;
}}

th.sortable .sort-icon {{
    display: inline-block;
    margin-left: 4px;
    font-size: 0.8rem;
    color: #999;
}}

th.sortable[aria-sort="ascending"] .sort-icon,
th.sortable[aria-sort="descending"] .sort-icon {{
    color: #2a5298;
}}
</style>

<script>
function toggle(id) {{
    const el = document.getElementById(id);
    const arrow = document.getElementById('arrow-' + id);
    const isHidden = el.style.display === "none";

    el.style.display = isHidden ? "table-row" : "none";
    if (arrow) {{
        arrow.textContent = isHidden ? "▲" : "↕";
    }}
}}

function loadPlot(divId, jsonPath) {{
    fetch(jsonPath)
        .then(r => {{
            if (!r.ok) throw new Error("Impossibile caricare " + jsonPath);
            return r.json();
        }})
        .then(fig => {{
            Plotly.newPlot(divId, fig.data, fig.layout, {{responsive: true}});
        }})
        .catch(err => {{
            document.getElementById(divId).innerText = "Grafico non disponibile";
            console.error(err);
        }});
}}
</script>
</head>
<body>

<header class="header">

    <div class="brand">
        <div class="side side-left">
            <a href="https://www.unisa.it" target="_blank" rel="noopener">
                <img class="logo-unisa" src="{base_path}logo_unisa.png" alt="Università di Salerno">
            </a>
            <a href="https://www.dipsum.unisa.it" target="_blank" rel="noopener">
                <img class="logo-dipsum" src="{base_path}logo_dipsum.png" alt="DipSUM - Dipartimento di Studi Umanistici">
            </a>
        </div>

        <img class="logo-main" src="{base_path}logo_cosi.png" alt="COSÌ logo">

        <a class="side side-right" href="https://www.dipsum.unisa.it/dipartimento/strutture?id=75" target="_blank" rel="noopener">
            <img class="logo-parole" src="{base_path}logo_parole.png" alt="P.A.R.O.L.E.">
        </a>
    </div>

    <nav class="navbar">
        <a href="{base_path}index.html">Home</a>
        <a href="{base_path}chi_siamo.html">Chi siamo</a>
        <div class="dropdown">
            <a href="{base_path}progetto.html">Progetto ▾</a>
            <div class="dropdown-content">
                <a href="{base_path}architettura.html">Architettura del database</a>
                <a href="{base_path}schema_annotazione.html">Schema di annotazione</a>
            </div>
        </div>
        <a href="{base_path}search.html">Cerca nel database</a>
        <a href="{base_path}prodotti.html">Prodotti della ricerca</a>
        <a href="{base_path}contatti.html">Contatti</a>
    </nav>

</header>

<div class="container">
{body}
</div>

</body>
</html>
"""

# =========================
# LOAD YAML
# =========================
def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

# =========================
# ESEMPI TSV
# =========================
def get_examples(tsv_path, target_micro, max_examples=2):
    examples = []
    if not tsv_path.exists():
        return examples

    target_micro = target_micro.strip().lower()

    with open(tsv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            if row.get("SegnDisc", "").strip().lower() != "yes":
                continue

            found = False
            for col in ["Func:Interazionale", "Func:Metatestuale", "Func:Cognitiva"]:
                labels = [x.strip().lower() for x in row.get(col, "").split("|") if x.strip()]
                if target_micro in labels:
                    found = True
                    break

            if not found:
                continue

            examples.append({
                "html": build_example(row, PROJECT_ROOT),
                "audio": row.get("audio", "")
            })

            if len(examples) >= max_examples:
                break

    return examples

# =========================
# INDEX
# =========================
search_index = []

# =========================
# BUILD PAGINE
# =========================
for signal_file in SIGNALS_DIR.glob("*.yaml"):

    name = signal_file.stem

    signal = load_yaml(signal_file)
    stats = load_yaml(STATS_DIR / f"{name}.yaml")

    tsv_path = TSV_DIR / signal["file"]

    ntokens = stats["counts"]["ntokens"]
    nSD = stats["counts"]["nSD"]
    varianti = signal["varianti"]

    if varianti is None:
        varianti = "-"

    macro = stats["macrofunctions_SD"]
    micro = stats["microfunctions_SD"]

    macro_sorted = sorted(macro.items(), key=lambda x: -x[1])

    macro_html = "<table><tr><th>Macro</th><th>Freq</th></tr>"
    for m, v in macro_sorted:
        color = COLOR_MAP.get(m, "white")
        macro_html += f'<tr style="background:{color}"><td>{m}</td><td>{v}</td></tr>'
    macro_html += "</table>"

    micro_flat = [(m, k, v) for m, vals in micro.items() for k, v in vals.items()]
    micro_sorted = sorted(micro_flat, key=lambda x: -x[2])

    micro_html = "<table><tr><th style='width:30px;'></th><th>Macro</th><th>Micro</th><th>Freq</th></tr>"

    for i, (m, k, v) in enumerate(micro_sorted[:10]):

        color = COLOR_MAP.get(m, "white")
        examples = get_examples(tsv_path, k)

        examples_html = ""

        if examples:
            for ex in examples:

                text = ex.get("text", "").strip()
                audio = ex.get("audio", "").strip()
                conv_id = ex.get("conv_id", "").strip()

                audio_html = f'<a class="audio" href="{audio}" target="_blank"></a>' if audio else ""
                conv_html = f" <span style='color:#888'>(conv_id: {conv_id})</span>" if conv_id else ""

                examples_html += f"""
                <div class="example">
                    {ex["html"]} {audio_html}
                </div>
                """
        else:
            examples_html = "<i>Nessun esempio disponibile</i>"

        micro_html += f"""
<tr style="background:{color}; cursor:pointer;" onclick="toggle('ex{i}')">
    <td style="text-align:center; color:#555; font-size:0.85rem;"><span id="arrow-ex{i}">↕</span></td>
    <td>{m}</td>
    <td>{k}</td>
    <td>{v}</td>
</tr>

<tr id="ex{i}" style="display:none; background:#fafafa">
    <td colspan="4">{examples_html}</td>
</tr>
"""

    micro_html += "</table>"

    type_json = f"../imgs/{name}/type.json"
    age_json = f"../imgs/{name}/age.json"
    region_json = f"../imgs/{name}/region_map.json"

    body = f"""
<div class="card">

    <h2 style="font-size: 1.6rem; margin-bottom: 0.4rem;">
        {signal["nomeSD"]}
    </h2>

    <div style="font-size: 1rem; color: #555; margin-bottom: 1rem;">
        da <b>{signal["source"]["lemma"]}</b>
        <span style="color:#888;">({signal["source"]["pos"]})</span>
    </div>

    <div style="font-size: 0.95rem; color: #666;">
        <b>Frequenza:</b>
        Occorrenze analizzate: {ntokens} | Segnali Discorsivi: {nSD}
    </div>
    <br>
    <div style="font-size: 0.95rem; color: #666;">
        <b>Varianti incluse:</b> <i>{varianti}</i>
    </div>

</div>

<div class="card">
    <h3>Macrofunzioni</h3>
    {macro_html}
    <p>{signal["descrizione_macro"]}</p>
</div>

<div class="card">
    <h3>Microfunzioni</h3>
    {micro_html}
    <p>{signal["descrizione_micro"]}</p>
</div>

<div class="card">
    <h3>Tipi di interazione</h3>
    <div id="plot-type" class="plot-container"></div>
</div>

<div class="card">
    <h3>Età</h3>
    <div id="plot-age" class="plot-container"></div>
</div>

<div class="card">
    <h3>Regioni</h3>
    <div id="plot-region" class="plot-container"></div>
</div>

<script>
    loadPlot('plot-type', '{type_json}');
    loadPlot('plot-age', '{age_json}');
    loadPlot('plot-region', '{region_json}');
</script>
"""

    html = base_html(name, body, base_path="../")
    (SIGNAL_PAGES_DIR / f"{name}.html").write_text(html, encoding="utf-8")

    search_index.append({
        "lemma": signal["nomeSD"],
        "frequenza": signal["fascia_frequenza"],
        "micro": ", ".join([k for _, k, _ in micro_sorted[:5]]),
        "link": f"segnali/{name}.html"
    })

# =========================
# INDEX HTML (pagina di ricerca)
# NB: stringa raw, NON f-string -> le graffe restano singole
# =========================
index_body = r"""
<div class="card">
  <h2>Ricerca per segnale discorsivo</h2>
  <input id="search" type="text" placeholder="Cerca segnale...">

  <button type="button" class="adv-toggle" id="advToggle" aria-expanded="false">+ Ricerca avanzata</button>

  <div class="adv-panel" id="advPanel">
    <label for="searchMicro">Microfunzione</label>
    <input id="searchMicro" type="text" placeholder="Es. riformulazione, presa di turno...">
  </div>
</div>

<div class="card">
<table>
<thead>
<tr>
<th class="sortable" data-key="lemma" aria-sort="none">Segnale<span class="sort-icon">↕</span></th>
<th class="sortable" data-key="frequenza" aria-sort="none">Fascia di frequenza<span class="sort-icon">↕</span></th>
<th>Microfunzioni</th>
</tr>
</thead>
<tbody></tbody>
</table>
</div>

<script src="data.js"></script>

<script>
const tableBody = document.querySelector("tbody");
const input = document.getElementById("search");
const microInput = document.getElementById("searchMicro");
const advToggle = document.getElementById("advToggle");
const advPanel = document.getElementById("advPanel");
const headers = document.querySelectorAll("th.sortable");

// Ordine delle fasce di frequenza (dalla più alta alla più bassa)
const FREQ_ORDER = ["alta", "medio-alta", "medio-bassa", "bassa"];
const collator = new Intl.Collator("it", { sensitivity: "base" });

let sortKey = null;   // "lemma" | "frequenza" | null (ordine originale)
let sortDir = "asc";  // "asc" | "desc"

// minuscolo + senza accenti, per una ricerca più tollerante
function norm(s) {
    return String(s || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, c => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[c]);
}

function freqRank(f) {
    const i = FREQ_ORDER.indexOf(String(f || "").trim().toLowerCase());
    return i === -1 ? FREQ_ORDER.length : i; // valori sconosciuti in fondo
}

function compare(a, b) {
    let r;
    if (sortKey === "frequenza") {
        r = freqRank(a.frequenza) - freqRank(b.frequenza);
        if (r === 0) r = collator.compare(a.lemma, b.lemma); // a parità, A-Z
    } else {
        r = collator.compare(a.lemma, b.lemma);
    }
    return sortDir === "asc" ? r : -r;
}

function updateHeaders() {
    headers.forEach(th => {
        const active = th.dataset.key === sortKey;
        th.setAttribute("aria-sort", active ? (sortDir === "asc" ? "ascending" : "descending") : "none");
        th.querySelector(".sort-icon").textContent = active ? (sortDir === "asc" ? "▲" : "▼") : "↕";
    });
}

function render() {
    const qLemma = norm(input.value);
    const qMicro = norm(microInput.value);

    // il segnale si cerca sempre; la microfunzione solo se compilata (AND)
    let rows = DATA.filter(x =>
        norm(x.lemma).includes(qLemma) &&
        (!qMicro || norm(x.micro).includes(qMicro))
    );

    if (sortKey) rows = rows.slice().sort(compare);

    tableBody.innerHTML = rows.map(x => `
        <tr onclick="window.location='${esc(x.link)}'" style="cursor:pointer">
            <td><b>${esc(x.lemma)}</b></td>
            <td><span class="badge">${esc(x.frequenza)}</span></td>
            <td>${esc(x.micro) || "-"}</td>
        </tr>`).join("");
}

headers.forEach(th => {
    th.addEventListener("click", () => {
        const key = th.dataset.key;
        if (sortKey === key) {
            sortDir = sortDir === "asc" ? "desc" : "asc";
        } else {
            sortKey = key;
            sortDir = "asc";
        }
        updateHeaders();
        render();
    });
});

advToggle.addEventListener("click", () => {
    const open = advPanel.style.display !== "block";
    advPanel.style.display = open ? "block" : "none";
    advToggle.textContent = open ? "− Ricerca avanzata" : "+ Ricerca avanzata";
    advToggle.setAttribute("aria-expanded", open);
    if (!open) {          // richiudendo, il filtro microfunzione si azzera
        microInput.value = "";
        render();
    }
});

input.addEventListener("input", render);
microInput.addEventListener("input", render);
render();
</script>
"""
home_body = """
<div class="card">
  <h2>Benvenuto in COSÌ</h2>

  <p>
    COSÌ è una risorsa dedicata allo studio dei segnali discorsivi nell'italiano parlato.
  </p>

  <p>
    Il database permette di esplorare le funzioni pragmatiche dei segnali,
    la loro distribuzione nei contesti comunicativi e le caratteristiche sociolinguistiche.
  </p>

  <p>
    Vai alla sezione <b>Cerca nel database</b> per esplorare i dati.
  </p>
</div>
"""

(DOCS_DIR / "index.html").write_text(
    base_html("Home", home_body, base_path=""),
    encoding="utf-8"
)

(DOCS_DIR / "search.html").write_text(
    base_html("Cerca nel database", index_body, base_path=""),
    encoding="utf-8"
)

(DOCS_DIR / "data.js").write_text(
    "const DATA = " + json.dumps(search_index, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("SITO GENERATO ✔")