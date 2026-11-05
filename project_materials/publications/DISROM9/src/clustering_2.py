import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from glob import glob
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.patches import Patch
import matplotlib.patheffects as pe
import textwrap
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
    """MDS dei profili dei cluster (distanza coseno)."""
    sim_ = cosine_similarity(profiles[feature_cols].astype(float))
    dist_ = np.clip(1 - sim_, 0, 2)
    np.fill_diagonal(dist_, 0)
    out = profiles.copy()
    out[["Dim1", "Dim2"]] = mds_2d(dist_)
    return out


def etichette_testo(ax, plot_df, label_col="cluster_id", fontsize=8, line_color="grey"):
    testi = [
        ax.text(r["Dim1"], r["Dim2"], r[label_col], fontsize=fontsize,
                ha="center", va="center", zorder=4,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
        for _, r in plot_df.iterrows()
    ]
    adjust_text(testi, ax=ax, expand=(1.2, 1.4), force_text=(0.5, 0.8),
                arrowprops=dict(arrowstyle="-", color=line_color, lw=0.5, alpha=0.7))


# =====================================================
# 1. MDS DEI CENTROIDI DI TUTTI GLI SD
# =====================================================

def plot_centroidi(plot_df, title):
    fig, ax = plt.subplots(figsize=(17, 10))
    sns.scatterplot(data=plot_df, x="Dim1", y="Dim2", hue="SD", size="size",
                    sizes=(80, 500), alpha=0.8, ax=ax)
    etichette_testo(ax, plot_df)
    ax.axhline(0, color="grey", lw=0.5, alpha=0.5)
    ax.axvline(0, color="grey", lw=0.5, alpha=0.5)
    ax.set(title=title, xlabel="Dimensione MDS 1", ylabel="Dimensione MDS 2")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left",
              borderaxespad=0, fontsize=8, title="SD / dimensione")
    fig.subplots_adjust(right=0.76)
    plt.show()


centroidi = mds_centroidi(cluster_profiles)
plot_centroidi(centroidi, "Cluster funzionali dei segnali discorsivi (MDS)")


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
        top = prof.idxmax()
        etich[c] = f"C{c}\n{ALL_MAP[top]} {prof[top]:.0%}\n(n={int((cl_t == c).sum())})"

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
    etichette_testo(ax, cent, label_col="label", fontsize=8, line_color="black")

    ax.set_title(f"Occorrenze di $\\mathit{{{sd_target}}}$ proiettate "
                 f"nello spazio funzionale (MDS), colorate per cluster")
    ax.set(xlabel="Dim 1", ylabel="Dim 2")
    ax.legend(title="Cluster", bbox_to_anchor=(1.01, 1), loc="upper left")
    fig.tight_layout()
    plt.show()


plot_token_sd("diciamo")


# =====================================================
# 3. MDS DEI CENTROIDI CON SFONDO A GRADIENTE FUNZIONALE
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
    "Interazionali": {
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
    "Metatestuali": {
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
    "Cognitive": {
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
                     bandwidth_factor=0.28, peso_dimensione=True):
    """Prevalenza locale di ogni microfunzione su una griglia MDS
    (kernel gaussiano sui centroidi). bandwidth_factor più alto = mappa
    più morbida e omogenea."""
    xy = cent[["Dim1", "Dim2"]].to_numpy()
    F = cent[feature_cols].astype(float).to_numpy()

    (xmin, ymin), (xmax, ymax) = xy.min(axis=0), xy.max(axis=0)
    rx, ry = max(xmax - xmin, 1e-6), max(ymax - ymin, 1e-6)

    XX, YY = np.meshgrid(
        np.linspace(xmin - margine * rx, xmax + margine * rx, n_grid),
        np.linspace(ymin - margine * ry, ymax + margine * ry, n_grid),
    )
    griglia = np.column_stack([XX.ravel(), YY.ravel()])

    bw = max(bandwidth_factor * np.sqrt(np.mean(np.var(xy, axis=0))), 1e-6)
    W = np.exp(-0.5 * (cdist(griglia, xy) / bw) ** 2)
    if peso_dimensione:
        W *= cent["size"].to_numpy(dtype=float)[None, :]
    W /= np.maximum(W.sum(axis=1, keepdims=True), 1e-12)

    return XX, YY, W @ F


def plot_gradiente(cent, funzione=None, mostra_cluster="punti",
                   normalizza=True, intensita_min=0.15, intensita_max=0.90,
                   gamma=1.0, nitidezza=5.0, area_min=0.003,
                   larghezza_etichetta=16, **kw):
    """
    funzione=None        -> sfondo continuo: il colore è la miscela dei colori
                            delle famiglie (pesata sulla loro presenza locale),
                            l'intensità è la densità della funzione più
                            presente. Etichette sulle aree di ogni funzione.
    funzione='<colonna>' -> mappa di prevalenza di una sola microfunzione.

    mostra_cluster : "punti" (solo punti), "id" (punti + id dei cluster,
                     le etichette si spostano per non sovrapporsi), False
    normalizza     : True = intensità relativa al massimo; False = percentuale
    intensita_min/max : intervallo di intensità (più basso = più chiaro)
    nitidezza      : alto = transizioni tra famiglie più rapide;
                     basso = miscela più morbida (1 = molto sfumato)
    gamma          : <1 schiarisce il contrasto, >1 lo accentua
    area_min       : frazione minima della mappa perché una funzione
                     riceva un'etichetta
    **kw           : parametri di stima_prevalenza (es. bandwidth_factor)
    """
    XX, YY, prev = stima_prevalenza(cent, **kw)
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
                ha="center", va="center", fontsize=9, fontweight="semibold",
                color=tuple(0.28 * base_c), zorder=5,
                bbox=dict(boxstyle="round,pad=0.3,rounding_size=0.6",
                          fc=(1, 1, 1, 0.62), ec=tuple(0.75 * base_c) + (0.9,), lw=0.8)))

        ax.legend(
            handles=[Patch(facecolor=spec["colore"], label=fam)
                     for fam, spec in FAMIGLIE.items()],
            title="Macrofunzione", loc="upper left",
            bbox_to_anchor=(1.01, 1), fontsize=9, borderaxespad=0, frameon=False)
        titolo = (
    "Multi-Dimensional Scaling (MDS) dei cluster funzionali "
    "dei segnali discorsivi in COSÌ\n"
    "(punti = centroidi dei cluster; intensità del colore = "
    "prevalenza locale della microfunzione dominante)"
)
    else:
        j = feature_cols.index(funzione)
        im = ax.imshow(prev[:, j].reshape(ny, nx), origin="lower", extent=extent,
                       aspect="equal", cmap="YlOrRd", interpolation="bicubic", zorder=0)
        fig.colorbar(im, ax=ax, label="Prevalenza stimata", shrink=0.8)
        titolo = f"MDS: prevalenza locale di {ALL_MAP[funzione]}"

    if mostra_cluster:
        ax.scatter(cent["Dim1"], cent["Dim2"], c="#444444", s=14, alpha=0.8,
                   edgecolors="white", linewidths=0.3, zorder=3)
    if mostra_cluster == "id":
        testi += [ax.text(r["Dim1"], r["Dim2"], r["cluster_id"], fontsize=6,
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

    ax.set(title=titolo, xlabel="Dimensione MDS 1", ylabel="Dimensione MDS 2")
    fig.tight_layout()
    plt.show()


plot_gradiente(centroidi)                                   # sfondo continuo + punti
plot_gradiente(centroidi, mostra_cluster="id")            # con gli id dei cluster
# plot_gradiente(centroidi, mostra_cluster=False)           # solo sfondo ed etichette
plot_gradiente(centroidi, bandwidth_factor=0.4)           # ancora più omogeneo
plot_gradiente(centroidi, intensita_max=0.65, mostra_cluster="id")             # ancora più chiaro
# plot_gradiente(centroidi, funzione="Riformulazione")      # singola microfunzione