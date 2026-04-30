import yaml
import json
import csv
from pathlib import Path
from example_builder import build_example

# =========================
# PATH
# =========================
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

SIGNALS_DIR = PROJECT_ROOT / "cosi"
STATS_DIR = PROJECT_ROOT / "cosi" / "stats"
TSV_DIR = PROJECT_ROOT / "data" / "tsv"

SITE_DIR = PROJECT_ROOT / "site"
SIGNAL_PAGES_DIR = SITE_DIR / "segnali"

SITE_DIR.mkdir(parents=True, exist_ok=True)
SIGNAL_PAGES_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# COLORI
# =========================
COLOR_MAP = {
    "Interazionale": "#ffe0cc",
    "Metatestuale": "#d4f5d4",
    "Cognitiva": "#d6eaff"
}

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

<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap" rel="stylesheet">

<style>
body {{
    margin: 0;
    font-family: 'Inter', sans-serif;
    background: #f5f7fa;
    color: #1a1a1a;
}}

header {{
    background: linear-gradient(120deg, #1e3c72, #2a5298);
    color: white;
    padding: 2rem;
    text-align: center;
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

iframe {{
    width: 100%;
    height: 400px;
    border: none;
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

.brand {{
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0.6rem 1rem 0 1rem;
    text-align: center;
}}

.brand img {{
    height:250px;
    width: auto;
    margin-bottom: 8;
    display: block;
}}

.navbar {{
    display: flex;
    justify-content: center;
    gap: 24px;
    padding: 6px 0 10px 0;
    background: white;
    margin-top: 6;
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

</style>

<script>
function toggle(id) {{
    const el = document.getElementById(id);
    el.style.display = (el.style.display === "none") ? "table-row" : "none";
}}
</script>

<header class="header">

    <div class="brand">
        <img src="{base_path}logo_cosi.png" alt="COSÌ logo">
    </div>

    <nav class="navbar">
        <a href="{base_path}index.html">Home</a>
        <a href="#">Chi siamo</a>
        <div class="dropdown">
            <a href="#">Progetto ▾</a>
            <div class="dropdown-content">
                <a href="#">Obiettivi del progetto</a>
                <a href="#">Architettura del database</a>
                <a href="#">Schema di annotazione</a>
            </div>
        </div>
        <a href="{base_path}search.html">Cerca nel database</a>
        <a href="#">Prodotti della ricerca</a>
        <a href="#">Contatti</a>
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

    micro_html = "<table><tr><th>Macro</th><th>Micro</th><th>Freq</th></tr>"

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
    <td>{m}</td>
    <td>{k}</td>
    <td>{v}</td>
</tr>

<tr id="ex{i}" style="display:none; background:#fafafa">
    <td colspan="3">{examples_html}</td>
</tr>
"""

    micro_html += "</table>"

    body = f"""
<div class="card">

    <h2 style="font-size: 1.6rem; margin-bottom: 0.4rem;">
        {signal["nomeSD"]}
    </h2>

    <div style="font-size: 1rem; color: #555; margin-bottom: 1rem;">
        <b>{signal["source"]["lemma"]}</b>
        <span style="color:#888;">({signal["source"]["pos"]})</span>
    </div>

    <div style="font-size: 0.95rem; color: #666;">
        <b>Frequenza:</b>
        Occorrenze analizzate: {ntokens} | Segnali Discorsivi: {nSD}
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
    <iframe src="../../cosi/imgs/{name}/type.html"></iframe>
</div>

<div class="card">
    <h3>Età</h3>
    <iframe src="../../cosi/imgs/{name}/age.html"></iframe>
</div>

<div class="card">
    <h3>Regioni</h3>
    <iframe src="../../cosi/imgs/{name}/region_map.html"></iframe>
</div>
"""

    # base_path per file dentro /segnali
    html = base_html(name, body, base_path="../")
    (SIGNAL_PAGES_DIR / f"{name}.html").write_text(html, encoding="utf-8")

    search_index.append({
        "lemma": signal["nomeSD"],
        "frequenza": signal["fascia_frequenza"],
        #"macro": ", ".join([m[0] for m in macro_sorted[:3]]),
        "micro": ", ".join([k for _, k, _ in micro_sorted[:5]]),
        "link": f"segnali/{name}.html"
    })

# =========================
# INDEX HTML
# =========================
index_body = """
<div class="card">
  <h2>Ricerca per segnale discorsivo</h2>
  <input id="search" placeholder="Cerca segnale...">
</div>

<div class="card">
<table>
<thead>
<tr>
<th>Segnale</th>
<th>Fascia di frequenza</th>
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

function render(filter="") {
    tableBody.innerHTML = "";

    DATA
    .filter(x =>
        x.lemma.toLowerCase().includes(filter.toLowerCase()) ||
        x.micro.toLowerCase().includes(filter.toLowerCase())
    )
    .forEach(x => {
        tableBody.innerHTML += `
        <tr onclick="window.location='${x.link}'" style="cursor:pointer">
            <td><b>${x.lemma}</b></td>
            <td><span class="badge">${x.frequenza}</span></td>
            
            <td>${x.micro || "-"}</td>
        </tr>`;
    });
}

input.addEventListener("input", e => render(e.target.value));
render();
</script>
"""
home_body = """
<div class="card">
  <h2>Benvenuto in COSÌ</h2>

  <p>
    COSÌ è una risorsa dedicata allo studio dei segnali discorsivi nell’italiano parlato.
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

(SITE_DIR / "index.html").write_text(
    base_html("Home", home_body, base_path=""),
    encoding="utf-8"
)

(SITE_DIR / "search.html").write_text(base_html("Home", index_body, base_path=""), encoding="utf-8")

(SITE_DIR / "data.js").write_text(
    "const DATA = " + json.dumps(search_index, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("SITO GENERATO ✔")