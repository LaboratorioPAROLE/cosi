library(dplyr)
library(lme4)
library(buildmer)

# =====================================================
# LOAD
# =====================================================

df <- read.delim("C:/Users/fpisc/Downloads/oviedo_cosi/OviedoCOSi/data/tsv/sd_cluster.tsv", sep = "\t")

# =====================================================
# CLEAN
# =====================================================

df <- df %>%
  mutate(across(where(is.character), ~ trimws(.))) %>%
  mutate(across(where(is.character), ~ na_if(.x, ""))) %>%
  filter(!is.na(sd))

# =====================================================
# GEO AREA
# =====================================================

geo_area <- function(x) {
  
  if (is.na(x)) return(NA)
  
  x <- tolower(trimws(x))
  
  nord <- c("piemonte","valle-d-aosta","lombardia","trentino-alto-adige",
            "veneto","friuli-venezia-giulia","liguria","emilia-romagna")
  
  centro <- c("toscana","umbria","marche","lazio")
  
  sud <- c("abruzzo","molise","campania","puglia","basilicata","calabria",
           "sicilia","sardegna")
  
  if (x %in% nord) return("Nord")
  if (x %in% centro) return("Centro")
  if (x %in% sud) return("Sud e Isole")
  if (x == "estero") return("Estero")
  
  return(NA)
}

df$geo_area <- sapply(df$region, geo_area)

df <- df %>% 
  filter(geo_area != "Estero" | is.na(geo_area))

# =====================================================
# AGE
# =====================================================

age_map <- c(
  "16-20"=1, "21-25"=2, "26-30"=3, "31-35"=4,
  "36-40"=5, "41-45"=6, "46-50"=7, "51-55"=8,
  "56-60"=9, "61-65"=10, "66-70"=11, "71-75"=12,
  "76-80"=13, "81-85"=14, "over 85"=15
)

df$eta_ordinale <- age_map[as.character(df$`age.range`)]

df

df2 <- df[df$Cluster %in% c("comunque_C3", "quindi_C2"), ]

df2$sd_pair <- df2$Cluster
df2$sd_pair <- factor(df2$sd_pair)

df2 <- df2[complete.cases(df2[, c(
  "sd_pair",
  "gender",
  "geo_area",
  "topic",
  "eta_ordinale",
  "participants.relationship",
  "type",
  "speaker_id"
)]), ]

options(contrasts = c("contr.sum", "contr.poly"))

df2$type <- factor(df2$type)
df2$gender <- factor(df2$gender)
df2$participants.relationship <- factor(df2$participants.relationship)


library(tidyverse)

df2 <- df2 %>%
  mutate(type_recoded = fct_collapse(type,
                                     "academic-interaction" = c("exam", "office-hours"),
                                     "free-conversation"    = "free-conversation",
                                     "lecture"              = "lecture",
                                     "semistructured-interview" = "semistructured-interview"
  ))


table(df2$type_recoded, df2$sd_pair)

m <- buildmer(
  sd_pair ~ gender +
    geo_area +
    topic +
    eta_ordinale +
    participants.relationship +
    type_recoded +
    (1 | speaker_id),
  data = df2,
  family = binomial,
  buildmerControl = buildmerControl(direction = "backward")
)

m <- buildmer(
  sd_pair ~ gender +
    geo_area +
    topic +
    eta_ordinale +
    participants.relationship +
    type_recoded +
    (1 | speaker_id),
  data = df2,
  family = binomial,
  buildmerControl = buildmerControl(direction = "forward")
)


'''
> m@model

Call:  stats::glm(formula = sd_pair ~ 1 + type_recoded + eta_ordinale, family = binomial, 
    data = df2)
'''


'''
> levels(factor(df2$sd_pair))
[1] "comunque_C3" "quindi_C2"
'''
m <- glm(
  sd_pair ~ 
    eta_ordinale +
    type_recoded,
  data = df2,
  family = binomial
)

'''
Call:
glm(formula = sd_pair ~ eta_ordinale + type_recoded, family = binomial, 
    data = df2)

Coefficients:
              Estimate Std. Error z value Pr(>|z|)    
(Intercept)   -0.03772    0.30083  -0.125 0.900210    
eta_ordinale   0.09635    0.04504   2.139 0.032403 *  
type_recoded1 -0.15365    0.48889  -0.314 0.753305    
type_recoded2 -1.06977    0.30070  -3.558 0.000374 ***
type_recoded3  1.30648    0.50404   2.592 0.009542 ** 
---
Signif. codes:  0 ‘***’ 0.001 ‘**’ 0.01 ‘*’ 0.05 ‘.’ 0.1 ‘ ’ 1

(Dispersion parameter for binomial family taken to be 1)

    Null deviance: 398.36  on 287  degrees of freedom
Residual deviance: 367.00  on 283  degrees of freedom
AIC: 377

Number of Fisher Scoring iterations: 4
'''

library(emmeans)

# 1. Calcola le medie (usa il modello finale fittato con buildmer)
medie_type <- emmeans(m, ~ type_recoded)


contrast(medie_type, method = "eff", type = "response")

# Visualizza i risultati in termini di Odds Ratio (rispetto alla media globale)
contrast(medie_type, method = "eff", type = "response")

'''
 contrast                          odds.ratio    SE  df null z.ratio p.value
 (academic-interaction) effect          0.858 0.419 Inf    1  -0.314  0.7533
 (free-conversation) effect             0.343 0.103 Inf    1  -3.558  0.0015
 lecture effect                         3.693 1.862 Inf    1   2.592  0.0191
 (semistructured-interview) effect      0.920 0.234 Inf    1  -0.327  0.7533

P value adjustment: fdr method for 4 tests 
Tests are performed on the log odds ratio scale 

contrast(medie_type, method = "eff", type = "response")
 contrast                          odds.ratio    SE  df null z.ratio p.value
 (academic-interaction) effect          0.858 0.419 Inf    1  -0.314  0.7533
 (free-conversation) effect             0.343 0.103 Inf    1  -3.558  0.0015
 lecture effect                         3.693 1.862 Inf    1   2.592  0.0191
 (semistructured-interview) effect      0.920 0.234 Inf    1  -0.327  0.7533
                          
                           comunque_C3 quindi_C2
  academic-interaction               5         6
  free-conversation                 47        21
  lecture                            3        20
  semistructured-interview          81       105
'''

### ------------------- effect plot (type_recoded) -----------------------------------

library(emmeans)
library(ggplot2)

# 1. Convertiamo l'output di emmeans in un dataframe
df_effects <- as.data.frame(emmeans(m, ~ type_recoded, type = "response"))

# 2. Definiamo l'ordine specifico forzando i livelli del fattore
# Nota: assicurati che i nomi corrispondano esattamente a quelli nel tuo df_effects$type_recoded
ordine_scelto <- c("free-conversation", "semistructured-interview", "academic-interaction", "lecture")

df_effects$type_recoded <- factor(df_effects$type_recoded, levels = ordine_scelto)

# 3. Generiamo il grafico a colonne distinte e ordinate
ggplot(df_effects, aes(x = type_recoded, y = prob, fill = type_recoded)) +
  geom_col(color = "black", alpha = 0.8, width = 0.5) + # width stringe le barre per separarle visivamente
  geom_errorbar(aes(ymin = asymp.LCL, ymax = asymp.UCL), width = 0.15, color = "gray20", linewidth = 0.7) +
  geom_hline(yintercept = 0.5, linetype = "dashed", color = "red", alpha = 0.6) + # Linea di neutralità (50%)
  scale_fill_brewer(palette = "Set2") + # Assegna un colore diverso a ogni barra distanziata
  scale_y_continuous(labels = scales::percent, limits = c(0, 1)) + # Mostra l'asse Y in comode percentuali (0-100%)
  labs(
    title = "Probabilità stimata di 'quindi_C2' per Contesto",
    subtitle = "Modello ad effetti principali (Valori medi ± IC 95%)",
    x = "Tipo di interazione",
    y = "Probabilità di occorrenza di quindi"
  ) +
  theme_minimal(base_size = 13) +
  theme(
    legend.position = "none", # Nascondiamo la legenda perché i nomi sono già scritti sotto ogni barra
    axis.text.x = element_text(angle = 25, hjust = 1), # Leggermente inclinato per massima leggibilità
    panel.grid.major.x = element_blank(), # Rimuove le griglie verticali per far risaltare il distacco tra le barre
    panel.grid.minor = element_blank()
  )

#########--------- grafico età --------###

library(tidyverse)

# 1. Definiamo la mappa inversa (dal numero alla stringa)
age_labels <- c(
  "1" = "16-20", "2" = "21-25", "3" = "26-30", "4" = "31-35",
  "5" = "36-40", "6" = "41-45", "7" = "46-50", "8" = "51-55",
  "9" = "56-60", "10" = "61-65", "11" = "66-70", "12" = "71-75",
  "13" = "76-80", "14" = "81-85", "15" = "over 85"
)

# 2. Prepariamo il dataset per il grafico
df_plot <- df2 %>%
  # Trasformiamo il numero in stringa e poi in fattore ordinato usando la mappa
  mutate(
    eta_string = as.character(round(eta_ordinale)), # round per sicurezza se ci sono decimali
    age_group = factor(age_labels[eta_string], levels = age_labels)
  ) %>%
  # Rimuoviamo eventuali NA se un numero non trova corrispondenza nella mappa
  filter(!is.na(age_group)) 

# 3. Generiamo il Barplot con barre affiancate
ggplot(df_plot, aes(x = age_group, fill = sd_pair)) +
  geom_bar(position = position_dodge(preserve = "single"), color = "black", alpha = 0.8) +
  geom_text(
    stat = "count", 
    aes(label = after_stat(count)), 
    position = position_dodge(width = 0.9), 
    vjust = -0.5, 
    size = 3.5
  ) +
  scale_fill_brewer(palette = "Set2") + # Colori coordinati e sobri
  labs(
    title = "Distribuzione di sd_pair per Fascia d'Età",
    x = "Fascia d'Età",
    y = "Numero di Occorrenze (Conteggio)",
    fill = "Variante (sd_pair)"
  ) +
  theme_minimal(base_size = 13) +
  theme(
    axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), # Ruota le etichette per non sovrapporle
    panel.grid.major.x = element_blank(),
    legend.position = "top"
  )

###########à ---------------effect plot ------

library(emmeans)
library(ggplot2)

# 1. Generiamo una griglia di valori per l'età (da 1 a 15, passo 0.5 per avere una curva fluida)
eta_grid <- seq(1, 15, by = 0.5)

# 2. Chiediamo a emmeans le probabilità predette lungo questa griglia
df_eta_effect <- as.data.frame(
  emmeans(m, ~ eta_ordinale, at = list(eta_ordinale = eta_grid), type = "response")
)

# 3. Definiamo i punti di interruzione (breaks) e le etichette per l'asse X
# Usiamo le tue fasce d'età reali per rendere il grafico leggibile a colpo d'occhio
age_labels <- c(
  "1" = "16-20", "3" = "26-30", "5" = "36-40", "7" = "46-50",
  "9" = "56-60", "11" = "66-70", "13" = "76-80", "15" = "over 85"
)

# 4. Creiamo il grafico ad effetto continuo
ggplot(df_eta_effect, aes(x = eta_ordinale, y = prob)) +
  # Banda di confidenza al 95% (sfumata)
  geom_ribbon(aes(ymin = asymp.LCL, ymax = asymp.UCL), fill = "blue", alpha = 0.15) +
  # Linea del trend centrale stimato dal modello
  geom_line(color = "darkblue", linewidth = 1.2) +
  # Linea tratteggiata di neutralità al 50%
  geom_hline(yintercept = 0.5, linetype = "dashed", color = "gray50", alpha = 0.7) +
  # Forza l'asse Y da 0 a 1 (percentuali)
  scale_y_continuous(labels = scales::percent, limits = c(0, 1)) +
  # Mappiamo l'asse X numerico sulle tue reali fasce d'età
  scale_x_continuous(breaks = as.numeric(names(age_labels)), labels = age_labels) +
  labs(
    title = "Effetto dell'Età sulla scelta della variante",
    subtitle = "Probabilità stimata di 'quindi_C2' (Linee di trend ± IC 95%)",
    x = "Fascia d'Età (Ricodificata)",
    y = "Probabilità di occorrenza di quindi"
  ) +
  theme_minimal(base_size = 13) +
  theme(
    axis.text.x = element_text(angle = 35, hjust = 1),
    panel.grid.minor = element_blank()
  )

