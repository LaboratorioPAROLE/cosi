import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from scipy.stats import chi2_contingency

# -----------------------------
# DATI (UGUALE)
# -----------------------------
micro_macro = pd.DataFrame({
    'Microfunzione': [
        "Marcatura dell'inferenza","Modulazione del grado di confidenza del parlante",
        "Approssimazione","Specificazione","Attenuazione","Intensificazione",
        "Presa di turno","Richiesta di accordo/conferma","Manifestazione di accordo",
        "Conferma dell'attenzione","Interruzione","Cessione del turno",
        "Marcatura della conoscenza condivisa","Richiesta di attenzione","Strategie di cortesia",
        "Gestione del topic: introduzione o ripresa di topic","Chiusura di un topic",
        "Prolettico, marca di formulazione: ecco","Riformulazione",
        "Marcatura di citazione/discorso riportato","Esemplificazione",
        "Filler, riempimento dei tempi di formulazione",
        "General extenders e marche di generalizzazione"
    ],
    'Macrofunzione': [
        "Cognitiva","Cognitiva","Cognitiva","Cognitiva","Cognitiva","Cognitiva",
        "Interazionale","Interazionale","Interazionale","Interazionale","Interazionale","Interazionale",
        "Interazionale","Interazionale","Interazionale",
        "Metatestuale","Metatestuale","Metatestuale","Metatestuale","Metatestuale",
        "Metatestuale","Metatestuale","Metatestuale"
    ],
    'Label': [
        "Inferenza","Grado di confidenza","Approssimazione","Specificazione","Attenuazione","Intensificazione",
        "Presa di turno","Richiesta accordo","Accordo","Conf. attenzione","Interruzione","Cessione turno",
        "Conoscenza condivisa","Richiesta attenzione","Cortesia",
        "Introduzione/ripresa Topic","Chiusura Topic","Prolettico/Analettico",
        "Riformulazione","Citazione","Esemplificazione","Filler","General extender"
    ]
})

df = pd.read_csv("C:/Users/fpisc/Documents/GitHub/cosi/aitla2026_materials/dataset.csv", sep=';', dtype=str, encoding='cp1252')
df.columns = [c.strip().replace('.', ' ').replace(' ', '_') for c in df.columns]

df['Microfunzione'].replace(["", "#CALC!"], np.nan, inplace=True)
df['Macrofunzione'].replace(["", "#CALC!"], np.nan, inplace=True)
df['Tipo_di_interazione'].replace(["0"], np.nan, inplace=True)

df_clean = df.dropna(subset=['SegnaleDisc', 'type', 'Tipo_di_interazione', 'Microfunzione'])
df_clean = df_clean[df_clean['SegnaleDisc'] == 'SD']
df_clean = df_clean.assign(Microfunzione=df_clean['Microfunzione'].str.split(r'\s*&\s*')).explode('Microfunzione')

# -----------------------------
sd_focus = "praticamente"
df_t = df_clean[df_clean['type'] == sd_focus]

freq_micro = df_t['Microfunzione'].value_counts()
micro_validi = freq_micro[freq_micro >= 5].index
df_t_filt = df_t[df_t['Microfunzione'].isin(micro_validi)]

df_t_filt = df_t_filt[
    df_t_filt['Tipo_di_interazione'].isin(
        df_t_filt['Tipo_di_interazione'].value_counts().loc[lambda x: x >= 5].index
    )
]

# -----------------------------
# CHI QUADRO
# -----------------------------
contingency = pd.crosstab(df_t_filt['Microfunzione'], df_t_filt['Tipo_di_interazione'])
chi2, p, dof, expected = chi2_contingency(contingency)

residui_std = (contingency - expected) / np.sqrt(expected)
residui_long = residui_std.stack().reset_index()
residui_long.columns = ['Microfunzione','Tipo_di_interazione','Residuo_std']

# 🔥 QUI CAMBIA: TENIAMO POSITIVI E NEGATIVI
soglia = 0
residui_long = residui_long[abs(residui_long['Residuo_std']) >= soglia]

residui_long = residui_long.merge(micro_macro, on='Microfunzione', how='left')

# -----------------------------
# GRAFO SIGNED
# -----------------------------
G = nx.Graph()

for t in residui_long['Tipo_di_interazione'].unique():
    G.add_node(t, type='Genere testuale', label=t)

for _, row in residui_long.iterrows():
    sign = 1 if row['Residuo_std'] > 0 else -1
    G.add_node(row['Microfunzione'], type='Microfunzione',
               label=row['Label'], macro=row['Macrofunzione'])

    G.add_edge(row['Microfunzione'], row['Tipo_di_interazione'],
               weight=abs(row['Residuo_std']),
               sign=sign)

# -----------------------------
# 🔥 SIGNED FORCE LAYOUT
# -----------------------------
def signed_layout(G, iterations=200, area=1.0, lambda_neg=2.0):
    nodes = list(G.nodes())
    n = len(nodes)
    k = np.sqrt(area / n)
    T = 0.1
    
    pos = {v: np.random.rand(2) for v in nodes}
    
    for _ in range(iterations):
        disp = {v: np.zeros(2) for v in nodes}
        
        # repulsione globale
        for u in nodes:
            for v in nodes:
                if u == v:
                    continue
                delta = pos[u] - pos[v]
                dist = max(np.linalg.norm(delta), 0.01)
                disp[u] += (delta / dist) * (k**2 / dist)
        
        # archi signed
        for u, v, data in G.edges(data=True):
            delta = pos[u] - pos[v]
            dist = max(np.linalg.norm(delta), 0.01)
            w = data['weight']
            
            if data['sign'] == 1:
                force = (dist**2 / k) * w
                disp[u] -= (delta / dist) * force
                disp[v] += (delta / dist) * force
            else:
                force = (k**2 / dist) * w * lambda_neg
                disp[u] += (delta / dist) * force
                disp[v] -= (delta / dist) * force
        
        for v in nodes:
            norm = np.linalg.norm(disp[v])
            if norm > 0:
                pos[v] += (disp[v] / norm) * min(norm, T)
        
        T *= 0.95
    
    return pos

pos = signed_layout(G)

# -----------------------------
# COLORI
# -----------------------------
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

# -----------------------------
# DISEGNO
# -----------------------------
plt.figure(figsize=(12,8))
fig, ax = plt.subplots(figsize=(12,8))
fig.patch.set_alpha(0)
ax.patch.set_alpha(0)

nodes_micro = [n for n,d in G.nodes(data=True) if d['type']=='Microfunzione']
nodes_genere = [n for n,d in G.nodes(data=True) if d['type']=='Genere testuale']

nx.draw_networkx_nodes(G, pos, nodelist=nodes_micro,
                       node_color=[color_map[list(G.nodes()).index(n)] for n in nodes_micro],
                       node_size=500)

nx.draw_networkx_nodes(G, pos, nodelist=nodes_genere,
                       node_color=[color_map[list(G.nodes()).index(n)] for n in nodes_genere],
                       node_size=700)

labels_dict = {n:d['label'] for n,d in G.nodes(data=True)}
nx.draw_networkx_labels(G, pos, labels=labels_dict, font_size=10)

# 🔥 EDGES SIGNED
pos_edges = [(u,v) for u,v,d in G.edges(data=True) if d['sign']==1]
neg_edges = [(u,v) for u,v,d in G.edges(data=True) if d['sign']==-1]

nx.draw_networkx_edges(G, pos, edgelist=pos_edges,
                       edge_color="green",
                       width=[G[u][v]['weight'] for u,v in pos_edges])

nx.draw_networkx_edges(G, pos, edgelist=neg_edges,
                       edge_color="red",
                       style="dashed",
                       width=[G[u][v]['weight'] for u,v in neg_edges])

# labels edge
edge_labels = {(u,v): f"{G[u][v]['weight']:.2f}" for u,v in G.edges()}
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)

plt.title(f"Signed graph (χ², p={p:.4f}) — {sd_focus}")
plt.axis('off')
plt.show()