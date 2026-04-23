


library(tidyverse)
library(scales)

micro_macro <- tribble(
  ~Microfunzione, ~Macrofunzione,
  "Marcatura dell'inferenza", "Cognitiva",
  "Modulazione del grado di confidenza del parlante", "Cognitiva",
  "Approssimazione", "Cognitiva",
  "Specificazione", "Cognitiva",
  "Attenuazione", "Cognitiva",
  "Intensificazione", "Cognitiva",
  "Presa di turno", "Interazionale",
  "Richiesta di accordo/conferma", "Interazionale",
  "Manifestazione di accordo", "Interazionale",
  "Conferma dell'attenzione", "Interazionale",
  "Interruzione", "Interazionale",
  "Cessione del turno", "Interazionale",
  "Marcatura della conoscenza condivisa", "Interazionale",
  "Richiesta di attenzione", "Interazionale",
  "Strategie di cortesia", "Interazionale",
  "Gestione del topic: introduzione o ripresa di topic", "Metatestuale",
  "Chiusura di un topic", "Metatestuale",
  "Prolettico, marca di formulazione: ecco", "Metatestuale",
  "Riformulazione", "Metatestuale",
  "Marcatura di citazione/discorso riportato", "Metatestuale",
  "Esemplificazione", "Metatestuale",
  "Filler, riempimento dei tempi di formulazione", "Metatestuale",
  "General extenders e marche di generalizzazione", "Metatestuale"
)

df <- read.csv2("dataset.csv",
 stringsAsFactors = FALSE)

norm_genere <- function(x){
  case_when(
    x == "intervista semistrutturata" ~ "intervista",
    x == "conversazione libera" ~ "conversazione",
    x %in% c("ricevimento studenti", "ricevimento") ~ "ricev.",
    TRUE ~ x
  )
}

df_clean <- df %>%
  mutate(
    Microfunzione = na_if(Microfunzione, ""),
    Microfunzione = na_if(Microfunzione, "#CALC!"),
    Tipo.di.interazione = na_if(Tipo.di.interazione, "0"),
    Macrofunzione = na_if(Macrofunzione, ""),
    Macrofunzione = na_if(Macrofunzione, "#CALC!"),
    Tipo.di.interazione = norm_genere(Tipo.di.interazione)
  ) %>%
  filter(
    SegnaleDisc == "SD",
    !is.na(type),
    !is.na(Tipo.di.interazione),
    !is.na(Microfunzione)
  ) %>%
  separate_rows(Microfunzione, sep = "\\s*&\\s*") %>%
  separate_rows(Macrofunzione, sep = "\\s*&\\s*")

df_mapped <- df_clean %>%
  left_join(micro_macro, by = "Microfunzione", suffix = c(".orig", ".map")) %>%
  select(-Macrofunzione.orig) %>%
  rename(Macrofunzione = Macrofunzione.map)

df_unique <- df_mapped %>%
  distinct(token, Microfunzione, Macrofunzione, Tipo.di.interazione, .keep_all = TRUE)

df_pesi <- df_unique %>%
  group_by(token) %>%
  mutate(n_macro = n_distinct(Macrofunzione)) %>%
  group_by(token, Macrofunzione) %>%
  mutate(n_micro_in_macro = n()) %>%
  ungroup() %>%
  mutate(peso = 1 / (n_macro * n_micro_in_macro))

gen_ord <- c("lezione", "esame", "intervista", "ricev.", "conversazione", "pasto")

macro_cols <- c(
  "Cognitiva" = "#095775",
  "Interazionale" = "#B41500",
  "Metatestuale" = "#005000"
)

out_dir <- "output_SD"
dir.create(out_dir, showWarnings = FALSE)

subcorpora_plot <- subcorpora %>%
  mutate(Tipo.di.interazione = norm_genere(Tipo.di.interazione))

gen_rank <- tibble(
  Tipo.di.interazione = gen_ord,
  rank = seq_along(gen_ord)
)

types <- unique(df_clean$type)

spearman_df <- map_dfr(types, function(t){
  
  df_t <- df_clean %>%
    filter(type == t)
  
  freq_pmw <- df_t %>%
    distinct(token, Tipo.di.interazione) %>%
    count(Tipo.di.interazione, name = "freq") %>%
    left_join(subcorpora_plot, by = "Tipo.di.interazione") %>%
    mutate(
      pmw = freq / parole * 1e6,
      Tipo.di.interazione = factor(Tipo.di.interazione, levels = gen_ord)
    )
  
  p1 <- ggplot(freq_pmw, aes(x = Tipo.di.interazione, y = pmw)) +
    geom_col(fill = "#095775") +
    geom_text(aes(label = round(pmw, 1)), vjust = -0.5, size = 4) +
    scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +
    labs(
      title = bquote(italic(.(t)) ~ "- freq pMw"),
      x = "Genere testuale",
      y = "pMw"
    ) +
    theme_minimal(base_size = 14) +
    theme(
      panel.background = element_rect(fill = "transparent", color = NA),
      plot.background  = element_rect(fill = "transparent", color = NA)
    )
  
  ggsave(
    filename = file.path(out_dir, paste0(t, "_pmw.png")),
    plot = p1,
    width = 8,
    height = 4.5,
    bg = "transparent"
  )
  
  df_mapped <- df_t %>%
    left_join(micro_macro, by = "Microfunzione") %>%
    rename(Macrofunzione = Macrofunzione.y) %>%
    distinct(token, Microfunzione, Macrofunzione, Tipo.di.interazione, .keep_all = TRUE)
  
  generi_validi <- df_mapped %>%
    distinct(token, Tipo.di.interazione) %>%
    count(Tipo.di.interazione) %>%
    filter(n >= 10) %>%
    pull(Tipo.di.interazione)
  
  df_mapped <- df_mapped %>%
    filter(Tipo.di.interazione %in% generi_validi)
  
  df_pesi <- df_mapped %>%
    group_by(token) %>%
    mutate(n_macro = n_distinct(Macrofunzione)) %>%
    group_by(token, Macrofunzione) %>%
    mutate(n_micro_in_macro = n()) %>%
    ungroup() %>%
    mutate(peso = 1 / (n_macro * n_micro_in_macro))
  
  df_macro_freq <- df_pesi %>%
    group_by(Tipo.di.interazione, Macrofunzione) %>%
    summarise(freq = sum(peso), .groups = "drop") %>%
    group_by(Tipo.di.interazione) %>%
    mutate(p = freq / sum(freq)) %>%
    ungroup() %>%
    mutate(Tipo.di.interazione = factor(Tipo.di.interazione, levels = gen_ord))
  
  p2 <- ggplot(df_macro_freq, aes(x = Tipo.di.interazione, y = p, fill = Macrofunzione)) +
    geom_col() +
    scale_y_continuous(labels = percent_format(), expand = expansion(mult = c(0, 0.1))) +
    scale_fill_manual(values = macro_cols) +
    labs(
      title = bquote(italic(.(t)) ~ "- % delle macrofunzioni"),
      x = "Genere testuale",
      y = "Percentuale",
      fill = "Macrofunzione"
    ) +
    theme_minimal(base_size = 14) +
    theme(
      panel.background = element_rect(fill = "transparent", color = NA),
      plot.background  = element_rect(fill = "transparent", color = NA)
    )
  
  ggsave(
    filename = file.path(out_dir, paste0(t, "_macro_percent.png")),
    plot = p2,
    width = 8,
    height = 4.5,
    bg = "transparent"
  )
  
  freq_pmw %>%
    left_join(gen_rank, by = "Tipo.di.interazione") %>%
    filter(!is.na(pmw), !is.na(rank)) %>%
    summarise(
      SD = t,
      rho = cor(pmw, rank, method = "spearman"),
      p_value = cor.test(pmw, rank, method = "spearman", exact = FALSE)$p.value
    )
})

spearman_df <- spearman_df %>%
  mutate(
    rho = round(rho, 3),
    p_value = signif(p_value, 3)
  )

