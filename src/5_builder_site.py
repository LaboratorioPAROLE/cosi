import yaml
import json
import csv
from pathlib import Path
from example_builder import build_example
import shutil
from urllib.parse import quote
from datetime import date
from html import escape

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
COSI_IMGS_DIR = PROJECT_ROOT / "cosi" / "imgs"

# I grafici vivono in cosi/imgs; il sito pubblica solo docs/, quindi li copiamo
if COSI_IMGS_DIR.exists():
    shutil.copytree(COSI_IMGS_DIR, DOCS_IMGS_DIR, dirs_exist_ok=True)
else:
    print("ATTENZIONE: cosi/imgs non trovata, lancia prima 4_create_graphs.py")

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

# Dataset annotati su GitHub (pagina di visualizzazione e file grezzo)
GITHUB_TSV_VIEW = "https://github.com/LaboratorioPAROLE/cosi/blob/main/data/tsv/"
GITHUB_TSV_RAW = "https://raw.githubusercontent.com/LaboratorioPAROLE/cosi/main/data/tsv/"

# =========================
# CITAZIONE DELLE VOCI
# =========================
# URL pubblico del sito (GitHub Pages): da correggere se diverso
SITE_URL = "https://laboratorioparole.github.io/cosi/"

CITE_AUTHOR = "Laboratorio P.A.R.O.L.E."
CITE_WORK = "COSÌ. Catalogo Online dei Segnali discorsivi dell'Italiano"
CITE_PUBLISHER = "Università di Salerno"
CITE_PLACE = "Salerno"
CITE_YEAR = date.today().year

# COSÌ in BibTeX con l'accento in forma sicura per LaTeX
BIB_WORK = "COS\\`{I}. Catalogo Online dei Segnali discorsivi dell'Italiano"


def citation_html(nome_sd, name):
    """Riquadro 'Come citare questa voce': citazione a schermo + BibTeX da copiare.
    La data di consultazione è inserita dal browser (span .cite-date)."""
    url = f"{SITE_URL}segnali/{quote(name)}.html"
    voce = escape(str(nome_sd))

    text = (
        f'{escape(CITE_AUTHOR)} ({CITE_YEAR}). \u201c{voce}\u201d. In '
        f'<i>{escape(CITE_WORK)}</i>. {escape(CITE_PLACE)}: {escape(CITE_PUBLISHER)}. '
        f'<a href="{url}">{url}</a> '
        f'(ultima consultazione: <span class="cite-date"></span>).'
    )

    key = "cosi-" + "".join(c if c.isalnum() else "-" for c in name.lower())
    bibtex = (
        f"@misc{{{key},\n"
        f"  author       = {{{{{CITE_AUTHOR}}}}},\n"
        f"  title        = {{{{{nome_sd}}}}},\n"
        f"  howpublished = {{In \\emph{{{BIB_WORK}}}}},\n"
        f"  publisher    = {{{CITE_PUBLISHER}}},\n"
        f"  address      = {{{CITE_PLACE}}},\n"
        f"  year         = {{{CITE_YEAR}}},\n"
        f"  url          = {{{url}}},\n"
        f'  urldate      = {{<span class="cite-date-iso"></span>}},\n'
        f'  note         = {{Ultima consultazione: <span class="cite-date"></span>}}\n'
        f"}}"
    )
    # escape per l'HTML, poi ripristino degli span della data
    bib_html = escape(bibtex, quote=False)
    bib_html = (bib_html
        .replace('&lt;span class="cite-date-iso"&gt;&lt;/span&gt;', '<span class="cite-date-iso"></span>')
        .replace('&lt;span class="cite-date"&gt;&lt;/span&gt;', '<span class="cite-date"></span>'))

    return f"""
<div class="card cite-card" id="cita">
    <h3>Come citare questa voce</h3>
    <p class="cite-text" id="cite-text">{text}</p>
    <div class="cite-actions">
        <button type="button" class="cite-btn" onclick="copyCite('cite-text', this)">Copia citazione</button>
        <button type="button" class="cite-btn" onclick="copyCite('cite-bib', this)">Copia BibTeX</button>
        <button type="button" class="cite-btn cite-btn-ghost" onclick="toggleBib(this)">Mostra BibTeX</button>
    </div>
    <pre class="cite-bib" id="cite-bib" hidden>{bib_html}</pre>
</div>
"""

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

/* Titoli nelle card */
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

/* Link al dataset annotato */
.dataset-link {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    margin-top: 1rem;
    padding: 8px 14px;
    border: 1px solid #d5dcea;
    border-radius: 10px;
    background: #f9fbff;
    color: #095775;
    font-size: 0.92rem;
    font-weight: 500;
    text-decoration: none;
}}

.dataset-link:hover {{
    border-color: #b51700;
    color: #b51700;
}}

.dataset-link svg {{
    width: 18px;
    height: 18px;
    flex-shrink: 0;
}}

.dataset-links {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 1rem;
}}

.dataset-links .dataset-link {{
    margin-top: 0;
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

/* =========================================
   STILE ESEMPI (SCHEDA / KIPARLA)
   ========================================= */
.example-card {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.03);
    margin: 10px 0 14px 0;
    padding: 12px 16px;
}}

.example-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 8px;
    margin-bottom: 8px;
    border-bottom: 1px solid #edf2f7;
}}

/* Nome corpus + Conv_ID in testo normale con virgola */
.conv-id {{
    font-weight: 600;
    color: #334155;
    font-size: 0.92rem;
}}

.audio-btn {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background-color: #095775;
    color: #ffffff !important;
    font-size: 0.8rem;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 16px;
    text-decoration: none !important;
    transition: background-color 0.2s ease;
}}

.audio-btn:hover {{
    background-color: #b51700;
}}

/* Pulsanti accanto all'intestazione dell'esempio */
.example-actions {{
    display: inline-flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;
}}

.read-btn {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background-color: #ffffff;
    color: #095775 !important;
    border: 1px solid #095775;
    font-size: 0.8rem;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 16px;
    text-decoration: none !important;
    transition: color 0.2s ease, border-color 0.2s ease;
}}

.read-btn:hover {{
    color: #b51700 !important;
    border-color: #b51700;
}}

.transcript-table {{
    width: 100%;
    border-collapse: collapse;
}}

.transcript-table tr {{
    border-bottom: 1px solid #f8fafc;
}}

.transcript-table tr:last-child {{
    border-bottom: none;
}}

/* Evidenziazione del turno target: azzurrino leggero e sobrio */
.transcript-table tr.focus {{
    background-color: #f0f7ff !important;
    border-left: 3px solid #3182ce;
}}

.speaker-col {{
    width: 80px;
    min-width: 70px;
    font-weight: 700;
    font-size: 0.88rem;
    vertical-align: top;
    padding: 6px 10px 6px 8px;
}}

.text-col {{
    color: #2d3748;
    font-size: 0.95rem;
    line-height: 1.5;
    vertical-align: top;
    padding: 6px 8px;
}}

/* Parola target in rosso pulito: NO box, NO sfondi, NO bordi */
.text-col b {{
    font-weight: 700;
    color: #c53030;
    background: none;
    border: none;
    padding: 0;
}}

.example-card.error {{
    color: #e53e3e;
    background-color: #fff5f5;
    border-color: #fed7d7;
}}

/* =========================================
   HEADER E NAVBAR
   ========================================= */
.header {{
    background: #ffffff;
    border-bottom: 1px solid #e5e5e5;
}}

.brand {{
    --unisa-h: 100px;
    --dipsum-w: 130px;
    --stack-gap: 5px;
    --side-gap: clamp(16px, 6vw, 100px);
    --side-lift: 30px;
    --parole-scale: 1.08;

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

/* Titolo della voce + pulsante "Cita" */
.title-row {{
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
}}

.cite-jump {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
    margin-top: 4px;
    padding: 6px 12px;
    border: 1px solid #d5dcea;
    border-radius: 10px;
    background: #f9fbff;
    color: #095775;
    font-size: 0.88rem;
    font-weight: 500;
    text-decoration: none;
}}

.cite-jump:hover {{
    border-color: #b51700;
    color: #b51700;
}}

.cite-jump svg {{
    width: 16px;
    height: 16px;
}}

html {{
    scroll-behavior: smooth;
}}

#cita {{
    scroll-margin-top: 20px;
}}

/* Footer */
.footer {{
    background: #ffffff;
    border-top: 1px solid #e5e5e5;
    margin-top: 2rem;
}}

.footer-inner {{
    max-width: 1100px;
    margin: auto;
    padding: 1.2rem 2rem;
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    font-size: 0.88rem;
    color: #666;
}}

.footer-links {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 18px;
}}

.footer-links a {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #095775;
    text-decoration: none;
    font-weight: 500;
}}

.footer-links a:hover {{
    color: #b51700;
}}

.footer-links svg {{
    width: 16px;
    height: 16px;
}}

/* Come citare questa voce */
.cite-text {{
    font-size: 0.95rem;
    line-height: 1.6;
    color: #333;
    background: #f9fbff;
    border-left: 3px solid #095775;
    padding: 0.8rem 1rem;
    margin: 0 0 1rem 0;
    word-break: break-word;
}}

.cite-text a {{
    color: #095775;
}}

.cite-actions {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}}

.cite-btn {{
    display: inline-flex;
    align-items: center;
    padding: 8px 14px;
    border: 1px solid #d5dcea;
    border-radius: 10px;
    background: #f9fbff;
    color: #095775;
    font-family: inherit;
    font-size: 0.92rem;
    font-weight: 500;
    cursor: pointer;
}}

.cite-btn:hover {{
    border-color: #b51700;
    color: #b51700;
}}

.cite-btn.copied {{
    border-color: #2f855a;
    color: #2f855a;
}}

.cite-btn-ghost {{
    background: none;
    border-color: transparent;
}}

.cite-bib {{
    margin: 1rem 0 0 0;
    padding: 0.9rem 1rem;
    background: #1e293b;
    color: #e2e8f0;
    border-radius: 10px;
    font-size: 0.82rem;
    line-height: 1.5;
    overflow-x: auto;
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

// Data di consultazione nella citazione (oggi, in italiano e ISO)
document.addEventListener("DOMContentLoaded", () => {{
    const d = new Date();
    const it = d.toLocaleDateString("it-IT", {{day: "numeric", month: "long", year: "numeric"}});
    const iso = d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
    document.querySelectorAll(".cite-date").forEach(el => el.textContent = it);
    document.querySelectorAll(".cite-date-iso").forEach(el => el.textContent = iso);
}});

function copyCite(id, btn) {{
    const text = document.getElementById(id).textContent.trim();
    const label = btn.textContent;
    const done = () => {{
        btn.textContent = "Copiato ✓";
        btn.classList.add("copied");
        setTimeout(() => {{ btn.textContent = label; btn.classList.remove("copied"); }}, 1800);
    }};
    if (navigator.clipboard && window.isSecureContext) {{
        navigator.clipboard.writeText(text).then(done);
    }} else {{
        const ta = document.createElement("textarea");
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        ta.remove();
        done();
    }}
}}

function toggleBib(btn) {{
    const pre = document.getElementById("cite-bib");
    pre.hidden = !pre.hidden;
    btn.textContent = pre.hidden ? "Mostra BibTeX" : "Nascondi BibTeX";
}}

function loadPlot(divId, jsonPath) {{
    fetch(jsonPath, {{cache: "no-cache"}})
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

<footer class="footer">
  <div class="footer-inner">
    <span>© 2026 Laboratorio P.A.R.O.L.E. – Università di Salerno</span>
    <div class="footer-links">
      <a href="{base_path}chi_siamo.html">Chi siamo</a>
      <a href="{base_path}contatti.html">Contatti</a>
      <a href="https://github.com/LaboratorioPAROLE/cosi" target="_blank" rel="noopener" aria-label="GitHub">
        <svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>
        GitHub
      </a>
    </div>
  </div>
</footer>

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

    # Campione o estrazione completa?
    sampling = stats.get("sampling", {}) or {}
    if sampling.get("is_sample"):
        freq_line = (
            f"Occorrenze analizzate: {ntokens} (campione casuale su "
            f"{sampling['nOccTot']} totali) | Segnali Discorsivi: {nSD}"
        )
    else:
        freq_line = f"Occorrenze analizzate: {ntokens} | Segnali Discorsivi: {nSD}"

    macro = stats["macrofunctions_SD"]
    micro = stats["microfunctions_SD"]

    macro_sorted = sorted(macro.items(), key=lambda x: -x[1])

    macro_html = "<table><tr><th>Macrofunzione</th><th>Frequenza</th></tr>"
    for m, v in macro_sorted:
        color = COLOR_MAP.get(m, "white")
        macro_html += f'<tr style="background:{color}"><td>{m}</td><td>{v}</td></tr>'
    macro_html += "</table>"

    micro_flat = [(m, k, v) for m, vals in micro.items() for k, v in vals.items()]
    micro_sorted = sorted(micro_flat, key=lambda x: -x[2])

    micro_html = "<table><tr><th style='width:30px;'></th><th>Macrofunzione</th><th>Microfunzione</th><th>Frequenza</th></tr>"

    for i, (m, k, v) in enumerate(micro_sorted[:10]):

        color = COLOR_MAP.get(m, "white")
        examples = get_examples(tsv_path, k)

        examples_html = ""

        if examples:
            for ex in examples:
                # ex["html"] contiene già l'intera scheda completa stilizzata
                examples_html += ex["html"]
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
    <td colspan="4" style="padding: 10px 15px;">{examples_html}</td>
</tr>
"""

    micro_html += "</table>"

    tsv_name = quote(str(signal["file"]))
    tsv_view_url = GITHUB_TSV_VIEW + tsv_name
    tsv_raw_url = GITHUB_TSV_RAW + tsv_name

    type_json = f"../imgs/{name}/type.json"
    age_json = f"../imgs/{name}/age.json"
    region_json = f"../imgs/{name}/macroarea_map.json"

    # controllo: avvisa se i JSON dei grafici mancano in docs/imgs
    for p in ["type.json", "age.json", "macroarea_map.json"]:
        if not (DOCS_IMGS_DIR / name / p).exists():
            print(f"  manca imgs/{name}/{p}")

    body = f"""
<div class="card">

    <div class="title-row">
        <h2 style="font-size: 1.6rem; margin-bottom: 0.4rem;">
            {signal["nomeSD"]}
        </h2>
        <a class="cite-jump" href="#cita" title="Come citare questa voce" aria-label="Come citare questa voce">
            <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M9.5 6C6.5 6 4 8.5 4 11.5V18h6v-6H7c0-1.7 1.1-3 2.5-3V6zm10 0c-3 0-5.5 2.5-5.5 5.5V18h6v-6h-3c0-1.7 1.1-3 2.5-3V6z"/>
            </svg>
            Cita
        </a>
    </div>

    <div style="font-size: 1rem; color: #555; margin-bottom: 1rem;">
        da <b>{signal["source"]["lemma"]}</b>
        <span style="color:#888;">({signal["source"]["pos"]})</span>
    </div>

    <div style="font-size: 0.95rem; color: #666;">
        <b>Frequenza:</b>
        {freq_line}
    </div>
    <br>
    <div style="font-size: 0.95rem; color: #666;">
        <b>Varianti incluse:</b> <i>{varianti}</i>
    </div>

    <div class="dataset-links">
        <a class="dataset-link" href="{tsv_view_url}" target="_blank" rel="noopener">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <rect x="3" y="4" width="18" height="16" rx="2"/>
                <line x1="3" y1="10" x2="21" y2="10"/>
                <line x1="3" y1="15" x2="21" y2="15"/>
                <line x1="9" y1="4" x2="9" y2="20"/>
            </svg>
            Dataset annotato (.tsv)
        </a>
        <a class="dataset-link" href="{tsv_raw_url}" download>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M12 4v11"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="4" y1="20" x2="20" y2="20"/>
            </svg>
            Scarica .tsv
        </a>
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

{citation_html(signal["nomeSD"], name)}

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

const FREQ_ORDER = ["alta", "medio-alta", "medio-bassa", "bassa"];
const collator = new Intl.Collator("it", { sensitivity: "base" });

let sortKey = null;
let sortDir = "asc";

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
    return i === -1 ? FREQ_ORDER.length : i;
}

function compare(a, b) {
    let r;
    if (sortKey === "frequenza") {
        r = freqRank(a.frequenza) - freqRank(b.frequenza);
        if (r === 0) r = collator.compare(a.lemma, b.lemma);
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
    if (!open) {
        microInput.value = "";
        render();
    }
});

input.addEventListener("input", render);
microInput.addEventListener("input", render);
render();
</script>
"""


(DOCS_DIR / "search.html").write_text(
    base_html("Cerca nel database", index_body, base_path=""),
    encoding="utf-8"
)

(DOCS_DIR / "data.js").write_text(
    "const DATA = " + json.dumps(search_index, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("SITO GENERATO ✔")