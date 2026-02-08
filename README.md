# Materiali aggiuntivi

In questa cartella troverete alcuni materiali di appendice al poster "Segnali discorsivi e tipi di interazione", da presentare all'AItLA 2026 a Forlì.
Per tutti i grafici, si veda la cartella aitla2026_materials

## Calcolo del peso delle macro- e microfunzioni

Per un calcolo pesato delle micro- e macrofunzioni che ogni occorrenza di un SD ricopre abbiamo utilizzato il seguente metodo: il peso della singola microfunzione è calcolato tramite 

            w_ijk=1/(M_i× m_ij )

dove (i) è l'occorrenza, M_i è il numero di macrofunzioni (M) ricoperte dal SD in quell'occorrenza (i), e m_ij è il numero di microfunzioni (m) di una certa macrofunzione (j) che l'SD ricopre nell'occorrenza i.

La sommatoria dei pesi per ogni occorenza è pari a 1: in questo modo, non solo le macrofunzioni hanno tutte lo stesso peso, evitando così che macrofunzioni con meno suddivisioni interne siano svantaggiate, ma anche le microfunzioni ricevono tutte un peso proporzionato sulla base della loro appartenenza all'una o all'altra macrofunzione.

In questo modo, le occorrenze delle microfunzioni sono state ottenute tramite la somma dei pesi di cui sopra:

            F_micro=∑w_ijk 

e lo stesso è stato fatto per le macrofunzioni:

            F_macro=∑(1/M_i)

Questo metodo, pur non ricalcandolo del tutto, riprende quello del "factorial counting" già usato in letteratura allo scopo di attribuire pesi uniformi nel caso di annotazioni multi-etichetta.

# Bibliografia
