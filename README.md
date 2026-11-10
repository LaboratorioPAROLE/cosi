# COSÌ - Catalogo Online dei Segnali discorsivi dell'Italiano

## Membre e membri

Miriam Voghera (PI), Andrea Sansò (PI), Iolanda Alfano, Raffaele Annunziata, Alfonsina Buoniconto, Giovanni Di Paola, Pasquale Esposito, Flavio Pisciotta, Giuseppe Pisegna, Carmela Sammarco, Luisa Troncone

**Laboratorio PAROLE, DipSUm - Dipartimento di Studi Umanistici, Università di Salerno**


## Presentazione

**COSÌ** (Catalogo Online dei Segnali discorsivi dell'Italiano) è un progetto in corso al [Laboratorio P.A.R.O.L.E.](https://www.dipsum.unisa.it/dipartimento/strutture?id=75) del Dipartimento di Studi Umanistici (DipSUM) dell'Università di Salerno. Il progetto mira a costruire un catalogo online dei segnali discorsivi (= SD) dell'italiano. Esso consterà di una risorsa ampia e corpus-based per l'analisi, l'annotazione, e l'esplorazione dei SD nell'italiano contemporaneo. 

Per ogni segnale (*capito*, *comunque*, *diciamo*, *dunque*, *quindi*, *sai*…) il database raccoglie occorrenze estratte dai corpora KIParla, annotate manualmente per **macrofunzione** (interazionale, metatestuale, cognitiva) e **microfunzione**, e arricchite con i metadati della conversazione e del parlante. I dati sono consultabili sul sito generato in `docs/`.


COSÌ rientra nella filosofia dei **linked data**, ed è stato progettato per interagire con il corpus KIParla. Per ogni SD, si renderà disponibile:
- occorrenze del KIParla annotate e relativo cotesto;
- test di sostituzione adoperati per l'identificazione del SD;
- file con annotazione funzionale.


---

## Struttura della repository

```
cosi/
├── cosi/                   # schede dei segnali (una .yaml per SD)
│   ├── stats/              # statistiche calcolate (output script 3)
│   └── imgs/               # dati dei grafici in JSON (output script 4)
├── data/
│   ├── xlsm/               # schede di annotazione originali (Excel)
│   ├── csv/                # conversione intermedia (output script 1)
│   └── tsv/                # dataset annotati finali (output script 2)
├── docs/                   # sito web statico (GitHub Pages)
│   ├── segnali/            # una pagina per segnale (generata)
│   ├── imgs/               # copia di cosi/imgs usata dal sito
│   └── foto/               # foto del gruppo di ricerca
├── project_materials/
│   ├── corpus-data.yaml    # dimensioni del corpus per tipo, regione, età
│   ├── Agreement/          # esperimento su calcolo dell'accordo tra annotatori (R)
│   ├── Default_annotation_sheet/   # scheda di annotazione vuota + istruzioni
│   ├── Discourse_markers_starting_reference/  # liste di partenza (n-grammi KIParla)
│   ├── Ongoing_annotations/        # annotazioni in corso
│   └── publications/       # materiali per pubblicazioni
├── src/                    # pipeline di elaborazione (vedi sotto)
├── DATA-LICENSE
└── SOFTWARE-LICENSE
```

---

## Schede dei segnali (`cosi/<nome>.yaml`)

Ogni segnale ha una scheda YAML con i campi usati dalla pipeline e dal sito:

| Campo | Contenuto |
|---|---|
| `nomeSD` | forma del segnale mostrata nel sito |
| `source.lemma`, `source.pos` | lemma e parte del discorso di origine |
| `file` | nome del tsv in `data/tsv/` |
| `varianti` | varianti formali incluse nell'estrazione |
| `nOccTot` | numero totale di occorrenze del segnale nel corpus |
| `fascia_frequenza` | alta / medio-alta / medio-bassa / bassa |
| `descrizione_macro`, `descrizione_micro` | testo descrittivo delle funzioni |

---

## Pipeline (`src/`)

Gli script vanno lanciati **in ordine** dalla cartella `src/`:

```bash
cd src
python 1_convert_xlsm_to_csv.py
python 2_convert_csv_to_tsv.py
python 3_calculate_stats.py
python 4_create_graphs.py
python builder_site.py
```

### 1. `1_convert_xlsm_to_csv.py`
Converte le schede Excel di `data/xlsm/` in CSV (`data/csv/`). Ricostruisce l'intestazione a partire dalle prime due righe del foglio, scartando la riga delle macrocategorie quando presente.

### 2. `2_convert_csv_to_tsv.py`
Produce i dataset annotati finali in `data/tsv/`. Per ogni occorrenza:
- individua il token nel corpus KIParla di origine (`token_id`, `token_span`, `speaker_id`) confrontando KWIC e contesto sinistro/destro;
- aggiunge i metadati della conversazione (tipo, durata, partecipanti, argomento, anno…) e del parlante (occupazione, genere, regione, fascia d'età);
- converte le colonne di annotazione nelle tre colonne `Func:Interazionale`, `Func:Metatestuale`, `Func:Cognitiva` (etichette multiple separate da `|`) e nella colonna `SegnDisc` (`yes`/`no`).

Le occorrenze non allineate al corpus sono marcate `#CHECK`.

### 3. `3_calculate_stats.py`
Calcola, per ogni tsv, le statistiche in `cosi/stats/<nome>.yaml`:
- numero di occorrenze analizzate (`ntokens`) e di segnali discorsivi (`nSD`);
- frequenze di macro- e microfunzioni;
- distribuzione dei SD per metadato, con **frequenza normalizzata per milione di parole** (`fpmw`) rispetto alle dimensioni del corpus in `project_materials/corpus-data.yaml`;
- aggregazione per **macroarea** geografica.

### 4. `4_create_graphs.py`
Genera i dati dei grafici (formato JSON di Plotly) in `cosi/imgs/<nome>/`:
- `type.json` – distribuzione per tipo di interazione;
- `age.json` – distribuzione per fascia d'età;
- `region_map.json` – mappa per singola regione;
- `macroarea_map.json` – mappa per macroarea (usata dal sito).

### 5. `builder_site.py`
Genera il sito statico in `docs/`: copia `cosi/imgs` in `docs/imgs`, crea una pagina per ogni segnale in `docs/segnali/` (funzioni, esempi, grafici, link al dataset), la pagina di ricerca `search.html` con il relativo indice `data.js` e la home. Gli esempi sono costruiti da `example_builder.py`, che ricostruisce il contesto dai corpora KIParla con link alla conversazione e all'audio.

---

## Calcolo delle misure di frequenza

### Frequenze normalizzate
Per ogni valore di metadato:

```
fpmw = occorrenze SD / token del corpus con quel valore × 1.000.000
```

Le fasce d'età del corpus sono accorpate in decenni (16-20, 21-30, … , >71).

### Proiezioni per i segnali campionati
Per alcuni segnali molto frequenti non sono state annotate tutte le occorrenze, ma un **campione casuale** (circa 800). Il caso si riconosce quando `nOccTot` della scheda è maggiore del numero di righe del tsv. Per renderli confrontabili con i segnali estratti per intero, i conteggi sono proiettati:

```
fattore = nOccTot / occorrenze nel tsv
conteggio proiettato = conteggio × fattore
```

Le frequenze normalizzate si calcolano sul conteggio proiettato. Nei grafici questi segnali sono indicati come *proiezione*, e i tooltip riportano sia il conteggio reale sia quello proiettato. La proiezione assume che il campione rifletta la distribuzione dell'intera popolazione: sulle categorie con pochi casi l'incertezza è alta.

### Macroaree geografiche
Le regioni sono raggruppate in tre macroaree, seguendo la suddivisione utilizzata nel KIParla (si veda il modulo [KIPasti](https://github.com/KIParla/KIPasti)):

| Macroarea | Regioni |
|---|---|
| Nord | Emilia-Romagna, Friuli-Venezia Giulia, Liguria, Lombardia, Piemonte, Trentino-Alto Adige, Valle d'Aosta, Veneto |
| Centro | Lazio, Marche, Toscana, Umbria |
| Sud e Isole | Abruzzo, Basilicata, Calabria, Campania, Molise, Puglia, Sardegna, Sicilia |

La frequenza corrisponde a:

```
somma occorrenze SD delle regioni dell'area / somma token del corpus delle regioni dell'area × 1.000.000
```

Tutte le regioni concorrono al calcolo, anche quelle con pochi dati. Nella mappa regionale invece sono escluse (in grigio) le regioni con meno di 40.000 token nel corpus; nella mappa per macroarea sono incluse ma segnalate come poco affidabili nel tooltip.


---
 
## Come citare

### Citare il catalogo

Per citare il catalogo, è possibile citare la presentazione ([abstract](https://eventi.unibo.it/talkingdata2025/abstracts/voghera-et-al.pdf/@@download/file/Voghera%20et.%20al.pdf)):

Voghera, Miriam, Andrea Sansò, Iolanda Alfano, Alfonsina Buoniconto, Violetta Cataldo, Giovanni Di Paola, Pasquale Esposito, Flavio Pisciotta, Carmela Sammarco, Luisa Troncone. 2025. Così: an online repertoire of italian discourse markers. In _Talking Data - Methodological and theoretical challenges raised by spoken interaction data_, 8-10 Ottobre 2025. Università di Bologna, Bologna.

### Voci individuali

In fondo a ogni pagina c'è il riquadro **Come citare questa voce**, con la citazione pronta in stile Chicago con *s.v.* (*sub voce*) e con la versione corrente del catalogo. Esempio:
 
> *COSÌ. Catalogo Online dei Segnali discorsivi dell'Italiano*, versione 0.1 (Salerno: Laboratorio P.A.R.O.L.E., Università di Salerno, 2026), s.v. "dunque", consultato il gg mese aaaa, https://laboratorioparole.github.io/cosi/segnali/dunque.html.

## Requisiti

- Python 3.10+
- `pandas`, `openpyxl`, `pyyaml`, `plotly`

```bash
pip install pandas openpyxl pyyaml plotly
```

Il sito carica Plotly.js da CDN e la geometria delle regioni da [openpolis/geojson-italy](https://github.com/openpolis/geojson-italy).

---

## Licenze

- Dati: vedi [`DATA-LICENSE`](DATA-LICENSE)
- Software: vedi [`SOFTWARE-LICENSE`](SOFTWARE-LICENSE)


## Contatti


| Nome                 | Email                      |
|----------------------|----------------------------|
| Miriam Voghera       | voghera(@)unisa.it           |
| Andrea Sansò         | asanso(@)unisa.it            |
| Iolanda Alfano       | ialfano(@)unisa.it           |
| Alfonsina Buoniconto | abuoniconto(@)unisa.it       |
| Giovanni Di Paola    | gdipaola(@)unisa.it          |
| Pasquale Esposito    | pasesposito(@)unisa.it        |
| Flavio Pisciotta     | fpisciotta(@)unisa.it        |
| Giuseppe Pisegna     | gpisegna(@)unisa.it        |
| Carmela Sammarco     | csammarco(@)unisa.it         |
| Luisa Troncone       | ltroncone(@)unisa.it         |

---

COSÌ - Catalogo Online dei Segnali discorsivi dell’Italiano  © 2025 by Laboratorio PAROLE Unisa is licensed under Creative Commons Attribution 4.0 International. To view a copy of this license, visit https://creativecommons.org/licenses/by/4.0/
