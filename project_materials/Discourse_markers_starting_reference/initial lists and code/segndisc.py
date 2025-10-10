import pandas as pd

# Caricamento dei dati in dataframe
sd_df = pd.read_csv('unigrams.csv', sep=';', encoding='utf-8')
bigrams_df = pd.read_csv('bigrams.csv', sep=';', encoding='utf-8')
trigrams_df = pd.read_csv('trigrams.csv', sep=';', encoding='utf-8')

# 1. Creazione del dizionario SegnaliDisc
SegnaliDisc = {}

# Popoliamo SegnaliDisc con le parole di sd
for _, row in sd_df.iterrows():
    word = row['word']
    frequency = row['Frequency']
    SegnaliDisc[word] = {
        'frequency': frequency,
        'ngrams': {}
    }

# 2. Aggiungi bigrammi a SegnaliDisc
for _, row in bigrams_df.iterrows():
    bigram = row['word']
    bigram_frequency = row['Frequency']
    word1, word2 = bigram.split()  # Dividi il bigramma in due parole

    # Controlla se il bigramma è presente in uno dei ngrammi delle parole di sd
    added_to_sd = False
    for word in sd_df['word']:
        if word in [word1, word2]:  # Se la parola di sd è presente nel bigramma
            SegnaliDisc[word]['ngrams'][bigram] = bigram_frequency
            added_to_sd = True
    
    # Se il bigramma non è stato aggiunto a nessuna parola di sd, aggiungilo come nuova entrata
    if not added_to_sd:
        SegnaliDisc[bigram] = {
            'frequency': bigram_frequency,
            'ngrams': {}
        }

# 3. Aggiungi trigrammi a SegnaliDisc
for _, row in trigrams_df.iterrows():
    trigram = row['word']
    trigram_frequency = row['Frequency']
    word1, word2, word3 = trigram.split()
    trigram_words = trigram.split()  # Dividi il trigramma in tre parole

    # Controlla se il trigramma corrisponde a un bigramma in SegnaliDisc
    added_to_bi = False
    for bigram, bigram_data in SegnaliDisc.items():
        if isinstance(bigram, str) and len(bigram.split()) == 2:  # Se è un bigramma
            b_word1, b_word2 = bigram.split()
            
            # Controlla se le parole del bigramma appaiono nell'ordine corretto nel trigramma
            if b_word1 in trigram_words and b_word2 in trigram_words:
                # Verifica se le parole sono nell'ordine giusto, anche se separate da altre parole
                b_index1 = trigram_words.index(b_word1)
                b_index2 = trigram_words.index(b_word2)
                
                # Se le parole appaiono nell'ordine corretto (b_word1 prima di b_word2)
                if b_index1 < b_index2:
                    SegnaliDisc[bigram]['ngrams'][trigram] = trigram_frequency
                    added_to_bi = True

    # Se il trigramma non corrisponde a un bigramma ma contiene una parola di sd, aggiungilo a sd
    added_to_sd_tri = False
    for word in sd_df['word']:
        if word in [word1, word2, word3]:
            SegnaliDisc[word]['ngrams'][trigram] = trigram_frequency
            added_to_sd_tri = True

    # Se il trigramma non è stato associato né a un bigramma né a una parola di sd, aggiungilo come nuova entrata
    if not added_to_bi and not added_to_sd_tri:
        SegnaliDisc[trigram] = {
            'frequency': trigram_frequency,
            'ngrams': {}
        }

# Creiamo il dataframe per il risultato finale con un numero dinamico di colonne per i ngram
final_data = []
for key, value in SegnaliDisc.items():
    row = {'SegnaleDiscorsivo': key, 'frequenza': value['frequency']}
    
    # Raccogli tutti gli ngramm
    ngram_columns = list(value['ngrams'].keys())
    ngram_frequencies = list(value['ngrams'].values())
    
    # Aggiungi ogni ngram e la sua frequenza alla riga
    for i, (ngram, freq) in enumerate(zip(ngram_columns, ngram_frequencies)):
        row[f'ngram{i + 1}'] = ngram
        row[f'ngram{i + 1}_freq'] = freq
    
    # Se ci sono meno ngram di quelli possibili, inserisci NaN
    for i in range(len(ngram_columns),3):  # Limitiamo a massimo 3 ngram
        row[f'ngram{i + 1}'] = pd.NA
        row[f'ngram{i + 1}_freq'] = pd.NA
    
    final_data.append(row)

# Creiamo il dataframe finale
final_df = pd.DataFrame(final_data)

# Salva il dataframe finale in un CSV
final_df.to_csv('SegnaliDiscorsivi.csv', encoding = "utf-8", index=False)

# Mostra il risultato
print(final_df)
