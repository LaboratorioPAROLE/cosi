import os
import numpy as np
import pandas as pd

from glob import glob

from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity

path = r"C:/Users/fpisc/Documents/GitHub/cosi/data/csv"
files = glob(os.path.join(path, "*.csv"))

dfs = []

for f in files:

    sd_name = os.path.splitext(
        os.path.basename(f)
    )[0]

    df = pd.read_csv(f, sep=";")

    # tieni solo SD annotati
    df = df[df["SD"] == 1].copy()

    df["SD_name"] = sd_name

    dfs.append(df)

df = pd.concat(dfs, ignore_index=True)

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
    "Intensificazione": "Intensificazione"
}


feature_cols = [c for c in df.columns if c in ALL_MAP]

X = (
    df[feature_cols]
    .notna()
    .astype(int)
)

df["cluster"] = np.nan

for sd in df["SD_name"].unique():

    idx = df["SD_name"] == sd

    X_sd = X.loc[idx]

    n = len(X_sd)

    if n < 20:
        continue

    n_clusters = min(5, max(2, n // 50))

    cl = AgglomerativeClustering(
        n_clusters=n_clusters
    )

    labels = cl.fit_predict(X_sd)

    df.loc[idx, "cluster"] = labels

cluster_profiles = []

for sd in df["SD_name"].unique():

    sub = df[df["SD_name"] == sd]

    for cl in sorted(sub["cluster"].dropna().unique()):

        idx = (
            (df["SD_name"] == sd)
            &
            (df["cluster"] == cl)
        )

        profile = X.loc[idx].mean()

        row = profile.to_dict()

        row["cluster_id"] = f"{sd}_C{int(cl)}"
        row["SD"] = sd
        row["size"] = idx.sum()

        cluster_profiles.append(row)

cluster_profiles = pd.DataFrame(cluster_profiles)

cluster_profiles = (
    cluster_profiles
    [cluster_profiles["size"] >= 20]
)

feature_cols = [
    c for c in cluster_profiles.columns
    if c in ALL_MAP
]

M = cluster_profiles[feature_cols]

sim = cosine_similarity(M)


rows = []

for i in range(len(cluster_profiles)):

    for j in range(i + 1, len(cluster_profiles)):

        sd1 = cluster_profiles.iloc[i]["SD"]
        sd2 = cluster_profiles.iloc[j]["SD"]

        if sd1 == sd2:
            continue

        rows.append([
            cluster_profiles.iloc[i]["cluster_id"],
            cluster_profiles.iloc[j]["cluster_id"],
            sim[i, j]
        ])

pairs = pd.DataFrame(
    rows,
    columns=[
        "cluster1",
        "cluster2",
        "similarity"
    ]
)


pairs = pairs.sort_values(
    "similarity",
    ascending=False
)

print(
    pairs.head(50)
)

def show_cluster(name):

    row = cluster_profiles[
        cluster_profiles["cluster_id"] == name
    ]

    prof = (
        row[feature_cols]
        .T
        .reset_index()
    )

    prof.columns = [
        "microfunzione",
        "weight"
    ]

    print(
        prof.sort_values(
            "weight",
            ascending=False
        ).head(10)
    )

show_cluster("comunque_C3")

show_cluster("quindi_C2")

# =====================================================
# PLOT CLUSTER NELLO SPAZIO FUNZIONALE
# =====================================================

from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import seaborn as sns

X_plot = cluster_profiles[feature_cols]

pca = PCA(n_components=2)

coords = pca.fit_transform(X_plot)

plot_df = cluster_profiles.copy()

plot_df["Dim1"] = coords[:, 0]
plot_df["Dim2"] = coords[:, 1]

plt.figure(figsize=(14,10))

sns.scatterplot(
    data=plot_df,
    x="Dim1",
    y="Dim2",
    hue="SD",
    size="size",
    sizes=(80,500)
)

for _, row in plot_df.iterrows():

    plt.text(
        row["Dim1"],
        row["Dim2"],
        row["cluster_id"],
        fontsize=8
    )

plt.axhline(0, color="grey", lw=.5)
plt.axvline(0, color="grey", lw=.5)

plt.title("Cluster funzionali dei segnali discorsivi")
plt.tight_layout()
plt.show()


from sklearn.manifold import MDS

dist = 1 - cosine_similarity(M)

mds = MDS(
    n_components=2,
    dissimilarity="precomputed",
    random_state=123
)

coords = mds.fit_transform(dist)

plot_df["Dim1"] = coords[:,0]
plot_df["Dim2"] = coords[:,1]

plt.figure(figsize=(14,10))

sns.scatterplot(
    data=plot_df,
    x="Dim1",
    y="Dim2",
    hue="SD",
    size="size",
    sizes=(80,500)
)

for _, row in plot_df.iterrows():

    plt.text(
        row["Dim1"],
        row["Dim2"],
        row["cluster_id"],
        fontsize=8
    )

plt.axhline(0, color="grey", lw=.5)
plt.axvline(0, color="grey", lw=.5)

plt.title("Cluster funzionali dei segnali discorsivi")
plt.tight_layout()
plt.show()


import prince

ca = prince.CA(
    n_components=2,
    random_state=123
)

ca = ca.fit(X_plot)

coords = ca.row_coordinates(X_plot)

plot_df = cluster_profiles.copy()

plot_df["Dim1"] = coords.iloc[:,0].values
plot_df["Dim2"] = coords.iloc[:,1].values

plt.figure(figsize=(14,10))

sns.scatterplot(
    data=plot_df,
    x="Dim1",
    y="Dim2",
    hue="SD",
    size="size",
    sizes=(80,500)
)

for _, row in plot_df.iterrows():

    plt.text(
        row["Dim1"],
        row["Dim2"],
        row["cluster_id"],
        fontsize=8
    )

plt.axhline(0, color="grey", lw=.5)
plt.axvline(0, color="grey", lw=.5)

plt.title("Cluster funzionali dei segnali discorsivi")
plt.tight_layout()
plt.show()

df["cluster_label"] = (
    df["SD_name"]
    + "_C"
    + df["cluster"].astype("Int64").astype(str)
)

df.to_csv(
    "sd_cluster.csv",
    index=False,
    sep=";"
)