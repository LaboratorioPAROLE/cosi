import os
import pickle
import hashlib
import textwrap

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import seaborn as sns

from glob import glob
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from scipy.spatial.distance import cdist
from sklearn.cluster import AgglomerativeClustering
from sklearn.manifold import MDS
from sklearn.metrics import silhouette_score, pairwise_distances
from sklearn.metrics.pairwise import cosine_similarity
from adjustText import adjust_text

# =====================================================
# PARAMETRI
# =====================================================

path = r"C:/Users/fpisc/Documents/GitHub/cosi/data/csv"

K_MAX = 10       # tetto di sicurezza per la ricerca di k
MIN_SIZE = 50    # dimensione minima di un cluster (e di un SD)
SEED = 123
MDS_CACHE = "mds_cache.pkl"

ALL_MAP = {
    "Presa di turno": "Presa di turno",
    "Richiesta di accordo/conferma": "Richiesta di accordo/conferma",
    "Manifestazione di accordo": "Accordo",
    "Conferma dell'attenzione": "Conferma dell'attenzione",
    "Interruzione": "Interruzione",
    "Cessione del turno": "Cessione del turno",
    "Marcatura della conoscenza condivisa": "Marcatura della conoscenza condivisa",
    "Richiesta di attenzione": "Richiesta di attenzione",
    "Strategie di cortesia": "Strategia di cortesia",
    "Gestione del topic: introduzione o ripresa di topic": "Introduzione o ripresa del topic",
    "Chiusura di un topic": "Chiusura del topic",
    "Prolettico, marca di formulazione: ecco": "Prolettico",
    "Riformulazione": "Riformulazione",
    "Marcatura di citazione/discorso riportato": "Citazione/Discorso Riportato",
    "Esemplificazione": "Esemplificazione",
    "Filler, riempimento dei tempi di formulazione": "Filler",
    "General extenders e marche di generalizzazione": "Marca di generalizzazione",
    "Marcatura dell'inferenza": "Marcatura dell'inferenza",
    "Modulazione del grado di confidenza del parlante": "Modulazione del grado di confidenza",
    "Approssimazione": "Approssimazione",
    "Specificazione": "Specificazione",
    "Attenuazione": "Attenuazione",
    "Intensificazione": "Intensificazione",
}

# =====================================================
# CARICAMENTO DATI
# =====================================================

dfs = []
for f in glob(os.path.join(path, "*.csv")):
    d = pd.read_csv(f, sep=";")
    d = d[d["SD"] == 1].copy()          # solo SD annotati
    d["SD_name"] = os.path.splitext(os.path.basename(f))[0]
    dfs.append(d)

df = pd.concat(dfs, ignore_index=True)

# numero progressivo per singolo SD: diciamo_14 = 14° token di "diciamo"
df["tok_n"] = df.groupby("SD_name").cumcount() + 1

feature_cols = [c for c in df.columns if c in ALL_MAP]
X = df[feature_cols].notna().astype(int)

# =====================================================
# CLUSTERING PER OGNI SD (k scelto con la silhouette)
# =====================================================

df["cluster"] = np.nan
k_info = []

for sd in df["SD_name"].unique():

    idx = df["SD_name"] == sd
    X_sd = X.loc[idx]
    n = len(X_sd)

    if n < MIN_SIZE:
        continue

    k_max = max(2, min(K_MAX, n // MIN_SIZE))
    best = None

    for k in range(2, k_max + 1):
        labels = AgglomerativeClustering(n_clusters=k).fit_predict(X_sd)

        # scarta soluzioni con cluster sotto soglia
        if np.bincount(labels).min() < MIN_SIZE:
            continue

        s = silhouette_score(X_sd, labels)
        if best is None or s > best["sil"]:
            best = {"k": k, "sil": s, "labels": labels}

    # se nessun k rispetta la soglia, ripiega su k = 2
    if best is None:
        labels = AgglomerativeClustering(n_clusters=2).fit_predict(X_sd)
        best = {"k": 2, "sil": silhouette_score(X_sd, labels), "labels": labels}

    df.loc[idx, "cluster"] = best["labels"]
    k_info.append({"SD": sd, "n": n, "k": best["k"],
                   "silhouette": round(best["sil"], 3)})

k_info = pd.DataFrame(k_info)
print(k_info.to_string(index=False))

# =====================================================
# PROFILI DEI CLUSTER (centroidi)
# =====================================================

rows = []
for (sd, cl), g in df.dropna(subset=["cluster"]).groupby(["SD_name", "cluster"]):
    row = X.loc[g.index].mean().to_dict()
    row["cluster_id"] = f"{sd}_C{int(cl)}"
    row["SD"] = sd
    row["size"] = len(g)
    rows.append(row)

cluster_profiles = (
    pd.DataFrame(rows)
    .query("size >= @MIN_SIZE")
    .reset_index(drop=True)
)

M = cluster_profiles[feature_cols].astype(float)
sim = cosine_similarity(M)

# =====================================================
# CONFRONTO TRA CLUSTER DI SD DIVERSI
# =====================================================

pair_rows = []
for i in range(len(cluster_profiles)):
    for j in range(i + 1, len(cluster_profiles)):
        c1, c2 = cluster_profiles.iloc[i], cluster_profiles.iloc[j]
        if c1["SD"] == c2["SD"]:
            continue
        t1 = c1[feature_cols].astype(float).idxmax()
        t2 = c2[feature_cols].astype(float).idxmax()
        pair_rows.append([c1["cluster_id"], c2["cluster_id"], sim[i, j],
                          int(c1["size"]), int(c2["size"]),
                          t1, c1[t1], t2, c2[t2]])

pairs = pd.DataFrame(pair_rows, columns=[
    "cluster1", "cluster2", "similarity",
    "n_occ_cluster1", "n_occ_cluster2",
    "top_feature_cluster1", "top_weight_cluster1",
    "top_feature_cluster2", "top_weight_cluster2",
]).sort_values("similarity", ascending=False)

print(pairs.head(50).to_string(index=False))


def show_cluster(name, n=10):
    row = cluster_profiles[cluster_profiles["cluster_id"] == name]
    if row.empty:
        print(f"Cluster '{name}' non trovato. "
              f"Disponibili: {list(cluster_profiles['cluster_id'])}")
        return
    prof = row[feature_cols].T.reset_index()
    prof.columns = ["microfunzione", "weight"]
    print(prof.sort_values("weight", ascending=False).head(n))


# =====================================================
# SALVATAGGIO
# =====================================================

df["cluster_label"] = (df["SD_name"] + "_C"
                       + df["cluster"].astype("Int64").astype(str))
df.to_csv("sd_cluster.csv", index=False, sep=";")
k_info.to_csv("sd_cluster_k.csv", index=False, sep=";")


# =====================================================
# FUNZIONI DI SUPPORTO PER I GRAFICI
# =====================================================

def mds_2d(dist, n_init=4):
    """MDS 2D su matrice di distanze precalcolata."""
    return MDS(n_components=2, dissimilarity="precomputed",
               random_state=SEED, n_init=n_init).fit_transform(dist)


def mds_centroidi(profiles):
    """MDS dei soli profili dei cluster (distanza coseno). Veloce."""
    sim_ = cosine_similarity(profiles[feature_cols].astype(float))
    dist_ = np.clip(1 - sim_, 0, 2)
    np.fill_diagonal(dist_, 0)
    out = profiles.copy()
    out[["Dim1", "Dim2"]] = mds_2d(dist_)
    return out


def etichette_testo(ax, plot_df, label_col="cluster_id", fontsize=6, line_color="grey",
                    box_edge="none", pad=0.2):
    testi = [
        ax.text(r["Dim1"], r["Dim2"], r[label_col], fontsize=fontsize,
                ha="center", va="center", multialignment="left", zorder=4,
                bbox=dict(boxstyle=f"round,pad={pad}", fc="white", ec=box_edge,
                          lw=0.8, alpha=0.9))
        for _, r in plot_df.iterrows()
    ]
    adjust_text(testi, ax=ax, expand=(1.2, 1.4), force_text=(0.5, 0.8),
                arrowprops=dict(arrowstyle="-", color=line_color, lw=0.5, alpha=0.7))


# =====================================================
# SPAZIO MDS UNICO (centroidi + tutti i token) CON CACHE
# =====================================================

def mds_centroidi_e_tutti_token(profiles):
    """
    Proietta centroidi e TUTTI i token nello STESSO spazio MDS (distanza coseno).
    - usa solo token di cluster presenti in `profiles` (cioè >= MIN_SIZE)
    - scarta i token senza alcuna microfunzione (vettore nullo: coseno indefinito)
    I profili dei centroidi restano calcolati su TUTTE le occorrenze.
    """
    lab = df["SD_name"] + "_C" + df["cluster"].astype("Int64").astype(str)
    valido = lab.isin(profiles["cluster_id"]) & (X.sum(axis=1) > 0)
    token_idx = df.index[valido].to_numpy()

    comb = np.vstack([
        profiles[feature_cols].astype(float).to_numpy(),
        X.loc[token_idx, feature_cols].astype(float).to_numpy(),
    ])

    dist = pairwise_distances(comb, metric="cosine")
    dist = np.clip((dist + dist.T) / 2, 0, 2)
    np.fill_diagonal(dist, 0)

    xy = mds_2d(dist)
    n_c = len(profiles)

    cent = profiles.copy()
    cent[["Dim1", "Dim2"]] = xy[:n_c]

    tokens = pd.DataFrame({
        "token_id": token_idx,
        "SD": df.loc[token_idx, "SD_name"].to_numpy(),
        "tok_n": df.loc[token_idx, "tok_n"].to_numpy(),
        "cluster_id": lab.loc[token_idx].to_numpy(),
        "Dim1": xy[n_c:, 0],
        "Dim2": xy[n_c:, 1],
    })
    return cent, tokens


def mds_con_cache(profiles, cache=MDS_CACHE):
    """Calcola l'MDS una sola volta; ricalcola solo se cambiano dati, cluster o seed."""
    chiave = hashlib.md5(
        pd.util.hash_pandas_object(df[["SD_name", "cluster"]]).to_numpy().tobytes()
        + X.to_numpy().tobytes()
        + str(SEED).encode()
    ).hexdigest()

    if os.path.exists(cache):
        with open(cache, "rb") as f:
            salvato = pickle.load(f)
        if salvato.get("chiave") == chiave:
            print("MDS caricato dalla cache")
            return salvato["cent"], salvato["tokens"]

    print("MDS in calcolo (può richiedere tempo)...")
    cent, tokens = mds_centroidi_e_tutti_token(profiles)
    with open(cache, "wb") as f:
        pickle.dump({"chiave": chiave, "cent": cent, "tokens": tokens}, f)
    return cent, tokens


# =====================================================
# 1. MDS DEI CENTROIDI DI TUTTI GLI SD
# =====================================================

def plot_centroidi(plot_df, title):
    fig, ax = plt.subplots(figsize=(17, 10))
    sns.scatterplot(data=plot_df, x="Dim1", y="Dim2", hue="SD", size="size",
                    sizes=(15, 120), alpha=0.8, ax=ax)
    etichette_testo(ax, plot_df, fontsize=6)
    ax.axhline(0, color="grey", lw=0.5, alpha=0.5)
    ax.axvline(0, color="grey", lw=0.5, alpha=0.5)
    ax.set(title=title, xlabel="Dimensione MDS 1", ylabel="Dimensione MDS 2")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left",
              borderaxespad=0, fontsize=8, title="SD / dimensione")
    fig.subplots_adjust(right=0.76)
    plt.show()


# =====================================================
# 2. MDS DEI TOKEN DI UN SINGOLO SD
# =====================================================

def plot_token_sd(sd_target, n_max=1500, jitter=0.015):
    """Proietta le occorrenze (token) di un SD, colorate per cluster."""
    rng = np.random.default_rng(SEED)

    idx = (df["SD_name"] == sd_target) & df["cluster"].notna()
    X_t = X.loc[idx]
    cl_t = df.loc[idx, "cluster"].astype(int)

    if X_t.empty:
        raise ValueError(f"Nessuna occorrenza per '{sd_target}'. "
                         f"SD disponibili: {sorted(df['SD_name'].unique())}")

    # etichette dei cluster: profili calcolati su TUTTE le occorrenze
    etich = {}
    for c in sorted(cl_t.unique()):
        prof = X_t[cl_t == c].mean().astype(float)
        top3 = prof[prof > 0].sort_values(ascending=False).head(3)   # solo se presenti
        righe = [textwrap.fill(f"{ALL_MAP[f]} {w:.0%}", 30, initial_indent="• ",
                               subsequent_indent="   ", break_long_words=False)
                 for f, w in top3.items()]
        etich[c] = (f"Cluster C_{c} (n={int((cl_t == c).sum())})\n"
                    + "\n".join(righe))

    # campione se troppo grande (MDS è O(n²))
    if len(X_t) > n_max:
        keep = rng.choice(len(X_t), n_max, replace=False)
        X_s, cl_s = X_t.iloc[keep], cl_t.iloc[keep]
    else:
        X_s, cl_s = X_t, cl_t

    # distanza euclidea, coerente con il Ward del clustering
    xy = mds_2d(pairwise_distances(X_s.values, metric="euclidean"))

    # centroidi calcolati prima del jitter
    cent = pd.DataFrame(xy, columns=["Dim1", "Dim2"])
    cent["cluster"] = cl_s.values
    cent = cent.groupby("cluster", as_index=False)[["Dim1", "Dim2"]].mean()
    cent["label"] = cent["cluster"].map(etich)

    # jitter: i dati sono binari e molti profili coincidono
    span = xy.max(axis=0) - xy.min(axis=0)
    xy_j = xy + rng.normal(0, jitter, xy.shape) * span

    d = pd.DataFrame({"Dim1": xy_j[:, 0], "Dim2": xy_j[:, 1],
                      "cluster": cl_s.values.astype(str)})
    ordine = [str(c) for c in sorted(cl_t.unique())]

    fig, ax = plt.subplots(figsize=(13, 9))
    sns.scatterplot(data=d, x="Dim1", y="Dim2", hue="cluster", hue_order=ordine,
                    palette="tab10", s=30, alpha=0.6, linewidth=0, ax=ax)
    ax.scatter(cent["Dim1"], cent["Dim2"], c="black", s=60,
               edgecolors="white", linewidths=0.6, zorder=3)
    etichette_testo(ax, cent, label_col="label", fontsize=8, line_color="black",
                    box_edge="#444444", pad=0.5)

    ax.set_title(f"Occorrenze di $\\mathit{{{sd_target}}}$ proiettate "
                 f"nello spazio funzionale (MDS), colorate per cluster")
    ax.set(xlabel="Dim 1", ylabel="Dim 2")
    ax.legend(title="Cluster", bbox_to_anchor=(1.01, 1), loc="upper left")
    fig.tight_layout()
    plt.show()


# =====================================================
# 3. MDS CON SFONDO A GRADIENTE FUNZIONALE
# =====================================================
#
# - Colore = famiglia (un solo colore per famiglia): interazionali arancione,
#   metatestuali verde, cognitive azzurro.
# - Intensità del colore = densità, cioè la percentuale locale della
#   microfunzione dominante nei cluster (lisciata con un kernel gaussiano
#   e pesata per il numero di occorrenze di ogni cluster).
# - Nessun taglio netto: i colori delle famiglie si fondono con continuità;
#   il nome di ogni microfunzione è scritto sull'area dove è più concentrata.

FAMIGLIE = {
    "Interazionale": {
        "colore": "#F4A56A",                     # arancione tenue
        "cols": [
            "Presa di turno",
            "Richiesta di accordo/conferma",
            "Manifestazione di accordo",
            "Conferma dell'attenzione",
            "Interruzione",
            "Cessione del turno",
            "Marcatura della conoscenza condivisa",
            "Richiesta di attenzione",
            "Strategie di cortesia",
        ],
    },
    "Metatestuale": {
        "colore": "#8CC79B",                     # verde tenue
        "cols": [
            "Gestione del topic: introduzione o ripresa di topic",
            "Chiusura di un topic",
            "Prolettico, marca di formulazione: ecco",
            "Riformulazione",
            "Marcatura di citazione/discorso riportato",
            "Esemplificazione",
            "Filler, riempimento dei tempi di formulazione",
            "General extenders e marche di generalizzazione",
        ],
    },
    "Cognitiva": {
        "colore": "#86C5EC",                     # azzurro tenue
        "cols": [
            "Marcatura dell'inferenza",
            "Modulazione del grado di confidenza del parlante",
            "Approssimazione",
            "Specificazione",
            "Attenuazione",
            "Intensificazione",
        ],
    },
}

COLORE_FUNZIONE = {}
for fam, spec in FAMIGLIE.items():
    for col in spec["cols"]:
        COLORE_FUNZIONE[col] = to_rgb(spec["colore"])

mancanti = [c for c in feature_cols if c not in COLORE_FUNZIONE]
if mancanti:
    raise ValueError(f"Microfunzioni senza famiglia: {mancanti}")


def stima_prevalenza(cent, n_grid=300, margine=0.10,
                     bandwidth_factor=0.28, peso_dimensione=True, estensione=None):
    """Prevalenza locale di ogni microfunzione su una griglia MDS
    (kernel gaussiano sui centroidi). bandwidth_factor più alto = mappa
    più morbida e omogenea."""
    xy = cent[["Dim1", "Dim2"]].to_numpy()
    F = cent[feature_cols].astype(float).to_numpy()

    # la griglia copre i centroidi e, se dati, anche altri punti (es. token)
    ref = xy if estensione is None else np.vstack([xy, estensione])
    (xmin, ymin), (xmax, ymax) = ref.min(axis=0), ref.max(axis=0)
    rx, ry = max(xmax - xmin, 1e-6), max(ymax - ymin, 1e-6)

    XX, YY = np.meshgrid(
        np.linspace(xmin - margine * rx, xmax + margine * rx, n_grid),
        np.linspace(ymin - margine * ry, ymax + margine * ry, n_grid),
    )
    griglia = np.column_stack([XX.ravel(), YY.ravel()])

    bw = max(bandwidth_factor * np.sqrt(np.mean(np.var(xy, axis=0))), 1e-6)
    D = cdist(griglia, xy)
    W = np.exp(-0.5 * (D / bw) ** 2)
    # 1 sul centroide, ~0 lontano da tutti (kernel più largo, per una sfumatura dolce)
    vicinanza = np.exp(-0.5 * (D.min(axis=1) / (3.0 * bw)) ** 2)
    if peso_dimensione:
        W *= cent["size"].to_numpy(dtype=float)[None, :]
    W /= np.maximum(W.sum(axis=1, keepdims=True), 1e-12)

    return XX, YY, W @ F, vicinanza


def plot_gradiente(cent, funzione=None, mostra_cluster="punti", tokens=None,
                   normalizza=True, intensita_min=0.15, intensita_max=0.90,
                   gamma=1.0, nitidezza=5.0, dissolvenza=0.40, area_min=0.003,
                   larghezza_etichetta=16, **kw):
    """
    funzione=None        -> sfondo continuo: il colore è la miscela dei colori
                            delle famiglie (pesata sulla loro presenza locale),
                            l'intensità è la densità della funzione più
                            presente. Etichette sulle aree di ogni funzione.
    funzione='<colonna>' -> mappa di prevalenza di una sola microfunzione.

    tokens         : DataFrame con Dim1, Dim2 (da mds_con_cache):
                     disegnati come x grigie chiare sotto i centroidi
    mostra_cluster : "punti" (solo punti), "id" (punti + id dei cluster,
                     le etichette si spostano per non sovrapporsi), False
    normalizza     : True = intensità relativa al massimo; False = percentuale
    intensita_min/max : intervallo di intensità (più basso = più chiaro)
    nitidezza      : alto = transizioni tra famiglie più rapide;
                     basso = miscela più morbida (1 = molto sfumato)
    gamma          : <1 schiarisce il contrasto, >1 lo accentua
    dissolvenza    : intensità residua lontano dai centroidi (0 = sfuma
                     fino al bianco, 1 = nessuna dissolvenza)
    area_min       : frazione minima della mappa perché una funzione
                     riceva un'etichetta
    **kw           : parametri di stima_prevalenza (es. bandwidth_factor)
    """
    # la mappa copre anche i token (esclusi gli outlier oltre 1°-99° percentile)
    estensione = None
    if tokens is not None and len(tokens):
        t = tokens[["Dim1", "Dim2"]].to_numpy()
        lo, hi = np.percentile(t, 1, axis=0), np.percentile(t, 99, axis=0)
        estensione = t[((t >= lo) & (t <= hi)).all(axis=1)]

    XX, YY, prev, vic = stima_prevalenza(cent, estensione=estensione, **kw)
    ny, nx = XX.shape
    extent = (XX.min(), XX.max(), YY.min(), YY.max())

    fig, ax = plt.subplots(figsize=(17, 10))
    testi = []

    if funzione is None:
        # presenza locale di ogni famiglia = la sua microfunzione più presente
        idx_fam = [[feature_cols.index(c) for c in spec["cols"] if c in feature_cols]
                   for spec in FAMIGLIE.values()]
        S = np.column_stack([prev[:, ix].max(axis=1) for ix in idx_fam])
        colori_fam = np.array([to_rgb(spec["colore"]) for spec in FAMIGLIE.values()])

        # colore: miscela continua delle famiglie
        Wf = np.maximum(S, 1e-12) ** nitidezza
        Wf /= Wf.sum(axis=1, keepdims=True)
        mix = Wf @ colori_fam

        # intensità: densità locale
        pmax = S.max(axis=1)
        dens = pmax / max(pmax.max(), 1e-12) if normalizza else pmax
        inten = intensita_min + (intensita_max - intensita_min) * np.clip(dens, 0, 1) ** gamma

        # lontano dai centroidi la stima non è affidabile: il colore sfuma
        inten = inten * (dissolvenza + (1 - dissolvenza) * vic)

        rgb = 1 - inten[:, None] * (1 - mix)                # verso il bianco
        ax.imshow(rgb.reshape(ny, nx, 3), origin="lower", extent=extent,
                  aspect="auto", interpolation="bicubic", zorder=0)

        # etichette: sull'area in cui ogni funzione è la più presente
        dom = prev.argmax(axis=1)
        griglia = np.column_stack([XX.ravel(), YY.ravel()])
        for j in np.unique(dom):
            mask = dom == j
            if mask.mean() < area_min:
                continue
            pts = griglia[mask]
            w = prev[mask, j]
            centro = np.average(pts, axis=0, weights=w + 1e-12)
            pos = pts[np.argmin(((pts - centro) ** 2).sum(axis=1))]

            col = feature_cols[j]
            base_c = np.array(COLORE_FUNZIONE[col])
            testi.append(ax.text(
                pos[0], pos[1],
                textwrap.fill(ALL_MAP[col], larghezza_etichetta, break_long_words=False),
                ha="center", va="center", fontsize=8, fontweight="semibold",
                color=tuple(0.28 * base_c), zorder=5,
                bbox=dict(boxstyle="round,pad=0.3,rounding_size=0.6",
                          fc=(1, 1, 1, 0.62), ec=tuple(0.75 * base_c) + (0.9,), lw=0.8)))

        ax.legend(
            handles=[Patch(facecolor=spec["colore"], label=fam)
                     for fam, spec in FAMIGLIE.items()]
                    + ([Line2D([], [], marker="x", ls="", color="#8a8a8a",
                               label="Token")]
                       if tokens is not None else [])
                    + ([Line2D([], [], marker="o", ls="", color="#444444",
                               markersize=4, label="Centroide di un cluster")]
                       if mostra_cluster else []),
            title="Macrofunzione", loc="upper left",
            bbox_to_anchor=(1.01, 1), fontsize=9, borderaxespad=0, frameon=False)
        titolo = ("Multi-Dimensional Scaling (MDS) dei cluster funzionali "
                  "dei segnali discorsivi in COSÌ\n"
                  "(intensità del colore = "
                  "prevalenza locale di una microfunzione)")
    else:
        j = feature_cols.index(funzione)
        im = ax.imshow(prev[:, j].reshape(ny, nx), origin="lower", extent=extent,
                       aspect="auto", cmap="YlOrRd", interpolation="bicubic", zorder=0)
        fig.colorbar(im, ax=ax, label="Prevalenza stimata", shrink=0.8)
        titolo = f"MDS: prevalenza locale di {ALL_MAP[funzione]}"

    # token individuali: x chiare e trasparenti, sotto i centroidi
    if tokens is not None and len(tokens):
        ax.scatter(tokens["Dim1"], tokens["Dim2"], marker="x", s=12,
                   c="#8a8a8a", alpha=0.25, linewidths=0.55, zorder=2)

    if mostra_cluster:
        ax.scatter(cent["Dim1"], cent["Dim2"], c="#444444", s=25, alpha=0.8,
                   edgecolors="white", linewidths=0.3, zorder=3)
    if mostra_cluster == "id":
        testi += [ax.text(r["Dim1"], r["Dim2"], r["cluster_id"], fontsize=7,
                          color="#444444", ha="center", va="center", zorder=4)
                  for _, r in cent.iterrows()]

    # separa le etichette tra loro (e dai punti dei cluster)
    if testi:
        try:
            adjust_text(testi, x=cent["Dim1"].to_numpy(), y=cent["Dim2"].to_numpy(),
                        ax=ax, expand=(1.15, 1.3), force_text=(0.4, 0.6),
                        arrowprops=dict(arrowstyle="-", color="#777777", lw=0.4, alpha=0.6))
        except TypeError:
            adjust_text(testi, ax=ax)

    ax.set(title=titolo, xlabel="Dimensione MDS 1", ylabel="Dimensione MDS 2",
           xlim=extent[:2], ylim=extent[2:])
    fig.tight_layout()
    plt.show()


# =====================================================
# 4. SELEZIONE CAMPIONE DI TOKEN DISTANZIATI (~20 ETICHETTE)
# =====================================================

def seleziona_token_campione(tokens, n_tot=20,
                             sd_target=("diciamo", "immagino", "cioè", "ecco", "sai")):
    """
    Seleziona ~n_tot occorrenze garantendo che per gli SD target vengano presi
    punti tra loro il più possibile lontani nello spazio MDS.
    I punti rimanenti vengono scelti con Farthest Point Sampling per coprire
    in modo omogeneo tutto il grafico.
    """
    selected_indices = []

    # 1. Per ciascun SD in sd_target, le 2 occorrenze con la massima distanza euclidea
    for sd in sd_target:
        sub = tokens[tokens["SD"] == sd]
        if len(sub) >= 2:
            coords = sub[["Dim1", "Dim2"]].to_numpy()
            dists = pairwise_distances(coords, metric="euclidean")
            i, j = np.unravel_index(np.argmax(dists), dists.shape)
            selected_indices.extend([sub.index[i], sub.index[j]])
        elif len(sub) == 1:
            selected_indices.append(sub.index[0])

    selected_indices = list(dict.fromkeys(selected_indices))

    # 2. Farthest Point Sampling per i token rimanenti
    remaining = tokens.drop(index=selected_indices)
    while len(selected_indices) < n_tot and len(remaining) > 0:
        pts_sel = tokens.loc[selected_indices, ["Dim1", "Dim2"]].to_numpy()
        pts_rem = remaining[["Dim1", "Dim2"]].to_numpy()

        dists = cdist(pts_rem, pts_sel, metric="euclidean").min(axis=1)
        best_idx = remaining.index[np.argmax(dists)]

        selected_indices.append(best_idx)
        remaining = remaining.drop(index=best_idx)

    return tokens.loc[selected_indices].copy()


# =====================================================
# 5. GRAFICO GRADIENTE CON TOKEN ED ETICHETTE EVIDENZIATE
# =====================================================

def plot_gradiente_solo_token(cent, tokens, n_campioni=20,
                              intensita_min=0.15, intensita_max=0.65,
                              nitidezza=5.0, dissolvenza=0.40, area_min=0.003,
                              larghezza_etichetta=16, **kw):
    """
    Sfondo a gradiente funzionale, TUTTI i token come punti trasparenti e un
    campione di ~n_campioni token con etichetta `SD_n` (n = progressivo del
    token all'interno del suo SD), collegata al punto da una linea.
    I centroidi sono nascosti.
    """
    t_coords = tokens[["Dim1", "Dim2"]].to_numpy()
    lo, hi = np.percentile(t_coords, 0.5, axis=0), np.percentile(t_coords, 99.5, axis=0)
    estensione = t_coords[((t_coords >= lo) & (t_coords <= hi)).all(axis=1)]

    XX, YY, prev, vic = stima_prevalenza(cent, estensione=estensione, **kw)
    ny, nx = XX.shape
    extent = (XX.min(), XX.max(), YY.min(), YY.max())

    fig, ax = plt.subplots(figsize=(18, 11))
    testi_totali = []

    # 1. SFONDO A GRADIENTE FUNZIONALE
    idx_fam = [[feature_cols.index(c) for c in spec["cols"] if c in feature_cols]
               for spec in FAMIGLIE.values()]
    S = np.column_stack([prev[:, ix].max(axis=1) for ix in idx_fam])
    colori_fam = np.array([to_rgb(spec["colore"]) for spec in FAMIGLIE.values()])

    Wf = np.maximum(S, 1e-12) ** nitidezza
    Wf /= Wf.sum(axis=1, keepdims=True)
    mix = Wf @ colori_fam

    pmax = S.max(axis=1)
    dens = pmax / max(pmax.max(), 1e-12)
    inten = intensita_min + (intensita_max - intensita_min) * np.clip(dens, 0, 1)
    inten = inten * (dissolvenza + (1 - dissolvenza) * vic)

    rgb = 1 - inten[:, None] * (1 - mix)
    ax.imshow(rgb.reshape(ny, nx, 3), origin="lower", extent=extent,
              aspect="auto", interpolation="bicubic", zorder=0)

    # 2. ETICHETTE AREE FUNZIONALI DI SFONDO
    dom = prev.argmax(axis=1)
    griglia = np.column_stack([XX.ravel(), YY.ravel()])
    for j in np.unique(dom):
        mask = dom == j
        if mask.mean() < area_min:
            continue
        pts = griglia[mask]
        w = prev[mask, j]
        centro = np.average(pts, axis=0, weights=w + 1e-12)
        pos = pts[np.argmin(((pts - centro) ** 2).sum(axis=1))]

        col = feature_cols[j]
        base_c = np.array(COLORE_FUNZIONE[col])
        testi_totali.append(ax.text(
            pos[0], pos[1],
            textwrap.fill(ALL_MAP[col], larghezza_etichetta, break_long_words=False),
            ha="center", va="center", fontsize=7, fontweight="bold",
            color=tuple(0.25 * base_c), zorder=4,
            bbox=dict(boxstyle="round,pad=0.3,rounding_size=0.5",
                      fc=(1, 1, 1, 0.65), ec=tuple(0.70 * base_c) + (0.85,), lw=0.8)))

    # 3. TUTTI I TOKEN (punti neutri trasparenti di sfondo)
    ax.scatter(tokens["Dim1"], tokens["Dim2"], marker="o", s=8,
               c="#666666", alpha=0.18, linewidths=0, zorder=2)

    # 4. CAMPIONE ETICHETTATO: punto scuro + testo senza riquadro + linea
    campione = seleziona_token_campione(tokens, n_tot=n_campioni)
    ax.scatter(campione["Dim1"], campione["Dim2"], s=16, c="#222222",
               linewidths=0, zorder=5)

    stroke = [pe.withStroke(linewidth=2, foreground="white")]
    testi_tok = [
        ax.text(r["Dim1"], r["Dim2"], f"{r['SD']}_{int(r['tok_n'])}",
                fontsize=7, color="#111111", zorder=6, path_effects=stroke)
        for _, r in campione.iterrows()
    ]
    testi_totali += testi_tok

    adjust_text(testi_totali,
                x=campione["Dim1"].to_numpy(), y=campione["Dim2"].to_numpy(),
                ax=ax, expand=(1.2, 1.4), force_text=(0.5, 0.8),
                arrowprops=dict(arrowstyle="-", color="#333333", lw=0.5, alpha=0.8))

    ax.legend(
        handles=[Patch(facecolor=spec["colore"], label=fam) for fam, spec in FAMIGLIE.items()]
                + [Line2D([], [], marker="o", ls="", color="#888888", alpha=0.5,
                          markersize=4, label=f"Tutti i token (n={len(tokens)})")]
                + [Line2D([], [], marker="o", ls="", color="#222222",
                          markersize=4, label="Occorrenze etichettate")],
        title="Macrofunzioni / Dati", loc="upper left",
        bbox_to_anchor=(1.01, 1), fontsize=9, borderaxespad=0, frameon=False
    )

    ax.set(
        title="Spazio funzionale continuo (MDS) — Distribuzione di tutte le occorrenze e campioni etichettati",
        xlabel="Dimensione MDS 1", ylabel="Dimensione MDS 2",
        xlim=extent[:2], ylim=extent[2:]
    )
    fig.tight_layout()
    plt.show()


# =====================================================
# ESECUZIONE
# =====================================================

# MDS dei soli centroidi (veloce, serve solo al primo grafico)
centroidi = mds_centroidi(cluster_profiles)
plot_centroidi(centroidi, "Cluster funzionali dei segnali discorsivi (MDS)")

# singolo SD
plot_token_sd("immagino")

# spazio MDS unico (centroidi + tutti i token), calcolato una volta e messo in cache
centroidi_all, tokeni_all = mds_con_cache(cluster_profiles)

plot_gradiente(centroidi_all, intensita_max=0.65, tokens=tokeni_all)
plot_gradiente(centroidi_all, intensita_max=0.65, tokens=tokeni_all, mostra_cluster="id")
# plot_gradiente(centroidi_all, funzione="Riformulazione")

plot_gradiente_solo_token(centroidi_all, tokeni_all, n_campioni=20, intensita_max=0.65)