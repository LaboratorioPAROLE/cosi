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

- Bazzanella, C. 2010. Segnali discorsivi. In R. Simone (a c. di), Enciclopedia dell’Italiano. Roma: Treccani. https://www.treccani.it/enciclopedia/segnali-discorsivi_(Enciclopedia-dell'Italiano)/
- Fedriani C. & A. Sansò. 2017. Pragmatic markers, discourse markers and modal particles: What do we know and where do we go from here? In C. Fedriani & A. Sansò (eds.), Pragmatic markers, discourse markers and modal particles. New perspectives, 1-33. Amsterdam: John Benjamins.
- Jucker, A.H. & Ziv, Y. (1998). Discourse markers. Descriptions and theory. Amsterdam: John Benjamins.
- Mauri, C., S. Ballarè, E. Goria, M. Cerruti & F. Suriano. 2019. KIParla corpus: a new resource for spoken Italian. In Proceedings of the 6th Italian Conference on Computational Linguistics (CLiC-it 2019). https://kiparla.it/
- Molinelli, P. 2018. Different sensitivity to variation and change: Italian pragmatic marker “dai” vs. discourse marker “allora”. In S. Pons Bordería, Ó. Loureda Lamas (eds.), Beyond grammaticalization and discourse markers: New issues in the study of language change, 271-303. Brill: Leiden.
- Perianes-Rodriguez, A., Waltman, L., van Eck, N. J. 2016. Constructing bibliometric networks:
A comparison between full and fractional counting. Journal of Infometrics, 10(4), 1178-1195.
- Sansò A. 2020. I segnali discorsivi. Roma: Carocci.
- Schiffrin, D. (1987). Discourse Markers. Cambridge: Cambridge University Press.
- Voghera, M., I. Alfano, F. Cutugno, A. De Rosa, C. Iacobini & R. Savy. 2014. VOLIP: A Corpus of Spoken Italian and a Virtuous Example of Reuse of Linguistic Resources. In Proceedings of the Ninth International Conference on Language Resources and Evaluation (LREC’14), 3897–3901.
- Voghera. M. 2017. Dal parlato alla grammatica. Roma: Carocci.

