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

df2 <- df[df$Cluster %in% c("diciamo_C2", "praticamente_C4"), ]

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

Call:  stats::glm(formula = sd_pair ~ 1 + type_recoded, family = binomial, data = df2)
'''


'''
> levels(factor(df2$sd_pair))
[1] "diciamo_C2"      "praticamente_C4"
'''
m <- glm(
    sd_pair ~ 
    type_recoded,
    data = df2,
    family = binomial)

'''
> summary(m)

Call:
  glm(formula = sd_pair ~ type_recoded, family = binomial, data = df2)

Coefficients:
  Estimate Std. Error z value Pr(>|z|)    
(Intercept)    -1.1514     0.2687  -4.285 1.83e-05 ***
  type_recoded1  -1.0999     0.5903  -1.863  0.06242 .  
type_recoded2   1.1514     0.4039   2.851  0.00436 ** 
  type_recoded3  -0.6404     0.5164  -1.240  0.21493    
---
  Signif. codes:  0 ‘***’ 0.001 ‘**’ 0.01 ‘*’ 0.05 ‘.’ 0.1 ‘ ’ 1

(Dispersion parameter for binomial family taken to be 1)

Null deviance: 251.44  on 198  degrees of freedom
Residual deviance: 237.81  on 195  degrees of freedom
AIC: 245.81

Number of Fisher Scoring iterations: 4
'''

library(emmeans)

# 1. Calcola le medie (usa il modello finale fittato con buildmer)
medie_type <- emmeans(m, ~ type_recoded)


contrast(medie_type, method = "eff", type = "response")

# Visualizza i risultati in termini di Odds Ratio (rispetto alla media globale)
contrast(medie_type, method = "eff", type = "response")

'''
> contrast(medie_type, method = "eff", type = "response")
contrast                          odds.ratio    SE  df null z.ratio p.value
(academic-interaction) effect          0.333 0.197 Inf    1  -1.863  0.0832
(free-conversation) effect             3.163 1.277 Inf    1   2.851  0.0174
lecture effect                         0.527 0.272 Inf    1  -1.240  0.2149
(semistructured-interview) effect      1.802 0.535 Inf    1   1.983  0.0832
                          
table(df2$sd_pair, df2$type_recoded)
                 
                  academic-interaction free-conversation lecture semistructured-interview
  diciamo_C2                        19                11      18                       86
  praticamente_C4                    2                11       3                       49
  
'''


### ------------------- effect plot (type) -----------------------------------
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
    title = "Probabilità stimata di 'praticamente_C4' per Contesto",
    subtitle = "Modello ad effetti principali (Valori medi ± IC 95%)",
    x = "Tipo di interazione",
    y = "Probabilità di occorrenza di praticamente"
  ) +
  theme_minimal(base_size = 13) +
  theme(
    legend.position = "none", # Nascondiamo la legenda perché i nomi sono già scritti sotto ogni barra
    axis.text.x = element_text(angle = 25, hjust = 1), # Leggermente inclinato per massima leggibilità
    panel.grid.major.x = element_blank(), # Rimuove le griglie verticali per far risaltare il distacco tra le barre
    panel.grid.minor = element_blank()
  )

