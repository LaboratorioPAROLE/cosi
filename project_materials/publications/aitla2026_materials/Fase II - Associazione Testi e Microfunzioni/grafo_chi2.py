import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from scipy.stats import chi2_contingency


micro_macro = pd.DataFrame({
    'Microfunzione': [
        "Marcatura dell'inferenza",
        "Modulazione del grado di confidenza del parlante",
        "Approssimazione",
        "Specificazione",
        "Attenuazione",
        "Intensificazione",
        "Presa di turno",
        "Richiesta di accordo/conferma",
        "Manifestazione di accordo",
        "Conferma dell'attenzione",
        "Interruzione",
        "Cessione del turno",
        "Marcatura della conoscenza condivisa",
        "Richiesta di attenzione",
        "Strategie di cortesia",
        "Gestione del topic: introduzione o ripresa di topic",
        "Chiusura di un topic",
        "Prolettico, marca di formulazione: ecco",
        "Riformulazione",
        "Marcatura di citazione/discorso riportato",
        "Esemplificazione",
        "Filler, riempimento dei tempi di formulazione",
        "General extenders e marche di generalizzazione"
    ],
    'Macrofunzione': [
        "Cognitiva","Cognitiva","Cognitiva","Cognitiva","Cognitiva","Cognitiva",
        "Interazionale","Interazionale","Interazionale","Interazionale","Interazionale","Interazionale",
        "Interazionale","Interazionale","Interazionale",
        "Metatestuale","Metatestuale","Metatestuale","Metatestuale","Metatestuale","Metatestuale","Metatestuale","Metatestuale"
    ],
    'Label': [
        "Inferenza","Grado di confidenza","Approssimazione","Specificazione","Attenuazione","Intensificazione",
        "Presa di turno","Richiesta accordo","Accordo","Conf. attenzione","Interruzione","Cessione turno",
        "Conoscenza condivisa","Richiesta attenzione","Cortesia",
        "Introduzione/ripresa Topic","Chiusura Topic","Prolettico/Analettico","Riformulazione","Citazione",
        "Esemplificazione","Filler","General extender"
    ]
})


df = pd.read_csv("dataset.csv", sep=';', dtype=str, encoding='cp1252')
df.columns = [c.strip().replace('.', ' ').replace(' ', '_') for c in df.columns]

# Pulizia
df['Microfunzione'].replace(["", "#CALC!"], np.nan, inplace=True)
df['Macrofunzione'].replace(["", "#CALC!"], np.nan, inplace=True)
df['Tipo_di_interazione'].replace(["0"], np.nan, inplace=True)
df_clean = df.dropna(subset=['SegnaleDisc', 'type', 'Tipo_di_interazione', 'Microfunzione'])
df_clean = df_clean[df_clean['SegnaleDisc'] == 'SD']
df_clean = df_clean.assign(Microfunzione=df_clean['Microfunzione'].str.split(r'\s*&\s*')).explode('Microfunzione')

# -----------------------------
# Selezione SD
# -----------------------------
sd_focus = "dunque"
df_t = df_clean[df_clean['type'] == sd_focus]

# Seleziona solo microfunzioni ≥10 occorrenze
freq_micro = df_t['Microfunzione'].value_counts()
micro_validi = freq_micro[freq_micro >= 5].index
df_t_filt = df_t[df_t['Microfunzione'].isin(micro_validi)]


#"#1CA2D7"

df_t_filt = df_t_filt[
    df_t_filt['Tipo_di_interazione'].isin(
        df_t_filt['Tipo_di_interazione'].value_counts()
        .loc[lambda x: x >= 5].index
    )
]


# Tabella contingente e residui
contingency = pd.crosstab(df_t_filt['Microfunzione'], df_t_filt['Tipo_di_interazione'])
chi2, p, dof, expected = chi2_contingency(contingency)
print(sd_focus)
print(p)
print(contingency)
residui_std = (contingency - expected) / np.sqrt(expected)

# Long format
residui_long = residui_std.stack().reset_index()
residui_long.columns = ['Microfunzione','Tipo_di_interazione','Residuo_std']

# Mantieni solo residui positivi
residui_long = residui_long[residui_long['Residuo_std'] >= 0]

# Unione con label e macrofunzione
residui_long = residui_long.merge(micro_macro, on='Microfunzione', how='left')

# -----------------------------
# Costruzione grafo
# -----------------------------
G = nx.DiGraph()
for t in residui_long['Tipo_di_interazione'].unique():
    G.add_node(t, type='Genere testuale', label=t)
for _, row in residui_long.iterrows():
    G.add_node(row['Microfunzione'], type='Microfunzione', label=row['Label'], macro=row['Macrofunzione'])
    G.add_edge(row['Microfunzione'], row['Tipo_di_interazione'], weight=row['Residuo_std'])

edge_labels = {
    (u, v): f"{G[u][v]['weight']:.2f}"
    for u, v in G.edges()
    if G[u][v]['weight'] >= 1.64
}


weights = np.array([G[u][v]['weight'] for u,v in G.edges()])
weights_scaled = (weights / weights.max() + 0.5)  
for i, (u,v) in enumerate(G.edges()):
    G[u][v]['sc_weight'] =  G[u][v]['weight']/weights.max() *1.5 

pos = nx.spring_layout(G, weight="sc_weight", k=1.5, iterations=100, seed=42)  


color_map_macro = {
    "Cognitiva": "#A6CEE3E9",        
    "Interazionale": "#FFBD72FA",    
    "Metatestuale": "#8BD44BE1"      
}
color_map = []
for n,d in G.nodes(data=True):
    if d['type'] == 'Genere testuale':
        color_map.append("#FBEF1AF1") 
    else:
        color_map.append(color_map_macro.get(d['macro'], "#FBEF1AF1"))


plt.figure(figsize=(14,10))

fig, ax = plt.subplots(figsize=(12, 8))
fig.patch.set_alpha(0)  # figura trasparente
ax.patch.set_alpha(0) 

nodes_micro = [n for n,d in G.nodes(data=True) if d['type']=='Microfunzione']
nodes_genere = [n for n,d in G.nodes(data=True) if d['type']=='Genere testuale']

nx.draw_networkx_nodes(G, pos, nodelist=nodes_micro, node_color=[color_map[i] for i,n in enumerate(G.nodes()) if n in nodes_micro], node_size=500)
nx.draw_networkx_nodes(G, pos, nodelist=nodes_genere, node_color=[color_map[i] for i,n in enumerate(G.nodes()) if n in nodes_genere], node_size=700)

# Etichette
labels_dict = {n:d['label'] for n,d in G.nodes(data=True)}
nx.draw_networkx_labels(G, pos, labels=labels_dict, font_size=10)

# Archi senza frecce
weights = [G[u][v]['weight'] for u,v in G.edges()]
nx.draw_networkx_edges(G, pos, edge_color='grey', arrows=False, width=[max(0.5,w) for w in weights])
nx.draw_networkx_edge_labels(
    G,
    pos,
    edge_labels=edge_labels,
    font_size=9,
    font_color="red",
    label_pos = 0.3,
    bbox=dict(
        facecolor="white",
        edgecolor="white",
        alpha=0.7,
        pad=0.2
    )
)


import matplotlib.patches as mpatches
genere_color = "#FBEF1AF1"
legend_elements = []

# Macrofunzioni
for macro, col in color_map_macro.items():
    legend_elements.append(
        mpatches.Patch(facecolor=col, edgecolor='black', label=macro)
    )

# Genere testuale
legend_elements.append(
    mpatches.Patch(facecolor=genere_color, edgecolor='black', label="Genere testuale")
)




patch_genere = mpatches.Patch(
    facecolor=genere_color,
    edgecolor="black",
    label="Tipi di interazione"
)

# Funzioni (macrofunzioni)
patch_funzioni = [
    mpatches.Patch(
        facecolor=col,
        edgecolor="black",
        label=macro
    )
    for macro, col in color_map_macro.items()
]

legend_genere = plt.legend(
    handles=[patch_genere],
    title="Tipo di nodo",
    loc="upper left",
    frameon=False,
    title_fontsize=11,
    fontsize=10
)

# Manteniamo la legenda quando aggiungiamo la seconda
plt.gca().add_artist(legend_genere)

# -----------------------------
# LEGENDA 2: Funzioni
# -----------------------------
plt.legend(
    handles=patch_funzioni,
    title="Funzioni",
    loc="upper left",
    bbox_to_anchor=(0, 0.92),  # sotto "Genere testuale"
    frameon=False,
    title_fontsize=11,
    fontsize=10
)



if p < 0.0001:
    pv = "< 0.0001"

elif p < 0.001:
    pv = "< 0.001"
else:
    pv = "= " + str(np.round(p, 2))


plt.title("Associazione tra Microfunzioni (min. freq. = 5) e Tipi di interazione (min. freq. = 5)\n"
    r"(Residui positivi test $\chi^2$, p " + pv+ "): $\it{" + sd_focus + "}$",
    fontsize=14,
    loc="center")
plt.axis('off')
plt.show()


