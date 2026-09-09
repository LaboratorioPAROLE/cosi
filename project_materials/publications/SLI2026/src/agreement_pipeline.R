#######################################################################
# COSI - Inter-annotator agreement pipeline (allora / comunque)
#
#
#   PART A  - metric functions          (agreement, Gwet AC1, etc.)
#   PART B  - data loading & prep        (Module 0: CSV -> 3 levels)
#   PART C  - analyses                   (recomputed from the data)
#             C1 aggregate agreement (raw / Jaccard / alpha / kappa /
#                Brennan-Prediger / Gwet AC1, pairwise + overall)
#             C2 positive agreement + prevalence diagnostics per label
#             C3 confusion matrices, disagreement systematicity (entropy)
#             C4 individual style: label frequency, polyfunctionality,
#                detection rate, Hill numbers, leave-one-out agreement
#             C5 bias: individual (chi-square leave-one-out) + group
#                (naive vs expert chi-square), gold-standard agreement
#   PART D  - plots                      (mirror slides 15-28)
#   PART E  - run everything, one corpus at a time
#
# NOTE:  Gwet AC1 uses the multi-label
# "at-least-one shared label" variant
#
# To run on the other corpus, change CORPUS below and re-source.
#######################################################################

suppressPackageStartupMessages({
  library(dplyr); library(purrr); library(tidyr); library(tibble)
  library(irr);   library(irrCAC)
  library(ggplot2); library(forcats); library(scales); library(ggrepel)
})

set.seed(42)

NOT_DM        <- "Not_DM"
EXCLUDE_TOKEN <- "EXCLUDE_TOKEN"   # token never analysed by an annotator

# ---- WHICH CORPUS / WHERE ARE THE CSVs -------------------------------
# Expects one CSV per annotator (";"-separated) with a Token.number
# column, an SD column, an optional Non.SD column, and one column per
# micro-function (see valid_micro_labels below). Ann_EspCoppia is optional
# and, when present, is treated as the "gold" pair annotation.
CORPUS      <- "Allora"                          # "Allora" or "Comunque"
data_folder <- file.path("..", "data", CORPUS)   # adjust to your layout
out_dir     <- "grafici_output"


#######################################################################
# PART A - METRIC FUNCTIONS
#######################################################################

# Raw "at least one shared label" (Macro/Micro); exact match (Detection).
raw_at_least_one <- function(a, b, is_detection = FALSE) {
  if (is_detection) return(as.numeric(identical(a, b)))
  if (NOT_DM %in% a || NOT_DM %in% b) return(NA)
  as.numeric(length(intersect(a, b)) > 0)
}

# Jaccard overlap on the label sets (Macro/Micro); exact match (Detection).
jaccard_pair <- function(a, b, is_detection = FALSE) {
  if (is_detection) return(as.numeric(identical(a, b)))
  if (NOT_DM %in% a || NOT_DM %in% b) return(NA)
  u <- length(union(a, b)); if (u == 0) return(NA)
  length(intersect(a, b)) / u
}

# Jaccard distance on binary indicator vectors (for Krippendorff alpha).
jaccard_distance_vec <- function(a, b) {
  u <- sum(a | b); if (u == 0) return(0); 1 - sum(a & b) / u
}
to_binary_labels <- function(labels, label_set) as.integer(label_set %in% labels)

# Krippendorff alpha, 2 raters, De estimated from the LOCAL pool of the
# two columns only (not a shared global pool).
krippendorff_alpha_pair <- function(df_sub, col_a, col_b, label_set,
                                    max_exact_pairs = 200000, sample_pairs = 20000) {
  n <- nrow(df_sub); if (n == 0) return(list(alpha = NA, n = 0))
  bin_a <- lapply(df_sub[[col_a]], to_binary_labels, label_set = label_set)
  bin_b <- lapply(df_sub[[col_b]], to_binary_labels, label_set = label_set)
  Do <- mean(sapply(seq_len(n), function(i) jaccard_distance_vec(bin_a[[i]], bin_b[[i]])))
  pool <- c(bin_a, bin_b); N <- length(pool)
  n_pairs <- N * (N - 1) / 2
  idx <- if (n_pairs <= max_exact_pairs) combn(seq_len(N), 2) else replicate(sample_pairs, sample(seq_len(N), 2))
  De <- mean(sapply(seq_len(ncol(idx)), function(k) jaccard_distance_vec(pool[[idx[1, k]]], pool[[idx[2, k]]])), na.rm = TRUE)
  list(alpha = if (De == 0) NA else 1 - Do / De, n = n)
}

# Krippendorff alpha, multi-rater (m raters simultaneously), for the
# "overall" figure.
krippendorff_alpha_jaccard <- function(df, annotator_cols, label_set = NULL,
                                       max_exact_pairs = 200000, sample_pairs = 20000) {
  n <- nrow(df); m <- length(annotator_cols)
  if (n == 0) return(list(alpha = NA, Do = NA, De = NA, n = 0))
  if (is.null(label_set)) label_set <- unique(unlist(df[annotator_cols]))
  df_bin <- lapply(df[annotator_cols], function(col) lapply(col, to_binary_labels, label_set = label_set))
  Do_vals <- c()
  for (i in seq_len(n)) {
    vecs <- lapply(df_bin, `[[`, i)
    for (a in 1:(m - 1)) for (b in (a + 1):m)
      Do_vals <- c(Do_vals, jaccard_distance_vec(vecs[[a]], vecs[[b]]))
  }
  Do <- mean(Do_vals, na.rm = TRUE)
  pool <- unlist(df_bin, recursive = FALSE); N <- length(pool)
  n_pairs <- N * (N - 1) / 2
  idx <- if (n_pairs <= max_exact_pairs) combn(seq_len(N), 2) else replicate(sample_pairs, sample(seq_len(N), 2))
  De <- mean(sapply(seq_len(ncol(idx)), function(k) jaccard_distance_vec(pool[[idx[1, k]]], pool[[idx[2, k]]])), na.rm = TRUE)
  list(alpha = if (De == 0) NA else 1 - Do / De, Do = Do, De = De, n = n)
}

# Reduce a multi-label to a single tag (first non-Not_DM, alphabetical).
reduce_to_single_tag <- function(label_list) {
  if (NOT_DM %in% label_list || length(label_list) == 0) return(NOT_DM)
  sort(label_list)[1]
}

# Cohen's kappa, single-tag, on the same filtered subset.
cohen_kappa_pair <- function(df_sub, col_a, col_b) {
  if (nrow(df_sub) == 0) return(list(kappa = NA, n = 0))
  a <- sapply(df_sub[[col_a]], reduce_to_single_tag)
  b <- sapply(df_sub[[col_b]], reduce_to_single_tag)
  list(kappa = tryCatch(irr::kappa2(data.frame(a, b))$value, error = function(e) NA), n = nrow(df_sub))
}

# Brennan-Prediger S (fixed chance level 1/q), single-tag.
brennan_prediger_pair <- function(df_sub, col_a, col_b) {
  if (nrow(df_sub) == 0) return(list(S = NA, n = 0))
  a <- sapply(df_sub[[col_a]], reduce_to_single_tag)
  b <- sapply(df_sub[[col_b]], reduce_to_single_tag)
  q <- length(unique(c(a, b))); po <- mean(a == b)
  list(S = if (q <= 1) NA else (po - 1 / q) / (1 - 1 / q), n = nrow(df_sub))
}
brennan_prediger_overall <- function(df, annotator_cols) {
  d <- df; for (col in annotator_cols) d[[col]] <- sapply(df[[col]], reduce_to_single_tag)
  q <- length(unique(unlist(d[annotator_cols]))); m <- length(annotator_cols)
  props <- c()
  for (i in 1:(m - 1)) for (j in (i + 1):m)
    props <- c(props, mean(d[[annotator_cols[i]]] == d[[annotator_cols[j]]]))
  po <- mean(props, na.rm = TRUE)
  list(S = if (q <= 1) NA else (po - 1 / q) / (1 - 1 / q), po = po, q = q, n = nrow(df))
}

# Fleiss' kappa, multi-rater single-tag, for the "overall" figure.
fleiss_kappa_overall <- function(df, annotator_cols) {
  d <- df; for (col in annotator_cols) d[[col]] <- sapply(df[[col]], reduce_to_single_tag)
  fk <- tryCatch(irr::kappam.fleiss(as.matrix(d[annotator_cols])), error = function(e) NULL)
  list(kappa = if (!is.null(fk)) fk$value else NA, n = nrow(df))
}

# ---- Gwet's AC1, MULTI-LABEL "at-least-one" variant (talk methodology).
# Pa = observed proportion of rater pairs sharing >=1 label; Pe = chance
# probability of sharing >=1 label, assuming each label is included
# independently with probability equal to its pooled prevalence.
label_prevalence <- function(df, annotator_cols, label_set) {
  sapply(label_set, function(lab)
    mean(unlist(lapply(annotator_cols, function(col)
      sapply(df[[col]], function(x) as.integer(lab %in% x))))))
}
gwet_ac1_at_least_one <- function(df, annotator_cols, label_set = NULL) {
  n <- nrow(df); m <- length(annotator_cols)
  if (n == 0 || m < 2) return(list(ac1 = NA, Pa = NA, Pe = NA, n = n))
  if (is.null(label_set)) label_set <- setdiff(unique(unlist(df[annotator_cols])), NOT_DM)
  if (length(label_set) == 0) return(list(ac1 = NA, Pa = NA, Pe = NA, n = n))
  overlaps <- c()
  for (i in seq_len(n)) for (a in 1:(m - 1)) for (b in (a + 1):m)
    overlaps <- c(overlaps, as.integer(
      length(intersect(df[[annotator_cols[a]]][[i]], df[[annotator_cols[b]]][[i]])) > 0))
  Pa <- mean(overlaps, na.rm = TRUE)
  prevs <- label_prevalence(df, annotator_cols, label_set)
  Pe <- 1 - prod(1 - prevs^2)
  list(ac1 = if (is.na(Pe) || Pe == 1) NA else (Pa - Pe) / (1 - Pe), Pa = Pa, Pe = Pe, n = n)
}
# AC1 pairwise/overall on single-tag data (matches irrCAC), kept for the
# detection level and the summary table where a single-tag AC1 is wanted.
gwet_ac1_pair <- function(df_sub, col_a, col_b) {
  if (nrow(df_sub) == 0) return(list(ac1 = NA, n = 0))
  a <- sapply(df_sub[[col_a]], reduce_to_single_tag)
  b <- sapply(df_sub[[col_b]], reduce_to_single_tag)
  res <- tryCatch(irrCAC::gwet.ac1.raw(data.frame(A = a, B = b)), error = function(e) NULL)
  list(ac1 = if (!is.null(res)) res$est$coeff.val else NA, n = nrow(df_sub))
}
gwet_ac1_overall <- function(df, annotator_cols) {
  d <- df; for (col in annotator_cols) d[[col]] <- sapply(df[[col]], reduce_to_single_tag)
  res <- tryCatch(irrCAC::gwet.ac1.raw(as.data.frame(d[annotator_cols])), error = function(e) NULL)
  list(ac1 = if (!is.null(res)) res$est$coeff.val else NA, n = nrow(df))
}

# Prevalence-paradox diagnostics per label: PABAK, Byrt PI / BI.
prevalence_diagnostics_per_label <- function(df, annotator_cols, label_set) {
  m <- length(annotator_cols)
  bind_rows(lapply(label_set, function(lab) {
    a <- b <- c <- d <- 0
    for (i in 1:(m - 1)) for (j in (i + 1):m) {
      x <- sapply(df[[annotator_cols[i]]], function(v) lab %in% v)
      y <- sapply(df[[annotator_cols[j]]], function(v) lab %in% v)
      a <- a + sum(x & y); b <- b + sum(x & !y); c <- c + sum(!x & y); d <- d + sum(!x & !y)
    }
    n <- a + b + c + d; po <- (a + d) / n
    pe <- ((a + b) / n) * ((a + c) / n) + ((c + d) / n) * ((b + d) / n)
    tibble(Label = lab, Po = po, Kappa = if (pe == 1) NA else (po - pe) / (1 - pe),
           PABAK = 2 * po - 1, PI = abs(a - d) / n, BI = abs(b - c) / n, N_a = a)
  })) %>% arrange(desc(PI))
}

# Wrapper: full pairwise table + overall summary for one level.
compute_all_agreement <- function(df, annotator_cols, level_name, filter_notdm = FALSE) {
  m <- length(annotator_cols)
  label_set <- setdiff(unique(unlist(df[annotator_cols])), NOT_DM)
  is_det <- level_name == "Detection"

  filter_pair_dm <- function(d, ca, cb)
    d %>% filter(!sapply(.data[[ca]], function(x) NOT_DM %in% x),
                 !sapply(.data[[cb]], function(x) NOT_DM %in% x))

  pairwise_tbl <- bind_rows(lapply(1:(m - 1), function(i) bind_rows(lapply((i + 1):m, function(j) {
    ca <- annotator_cols[i]; cb <- annotator_cols[j]
    sub <- if (filter_notdm) filter_pair_dm(df, ca, cb) else df
    tibble(
      Livello = level_name, Coppia = paste(ca, "vs", cb), n = nrow(sub),
      Raw     = mean(mapply(function(a, b) raw_at_least_one(a, b, is_det), sub[[ca]], sub[[cb]]), na.rm = TRUE),
      Jaccard = mean(mapply(function(a, b) jaccard_pair(a, b, is_det),     sub[[ca]], sub[[cb]]), na.rm = TRUE),
      Alpha   = krippendorff_alpha_pair(sub, ca, cb, label_set)$alpha,
      Kappa   = cohen_kappa_pair(sub, ca, cb)$kappa,
      BP_S    = brennan_prediger_pair(sub, ca, cb)$S,
      AC1     = gwet_ac1_at_least_one(sub, c(ca, cb), label_set)$ac1
    )
  }))))

  df_global <- if (filter_notdm)
    df %>% filter(!pmap_lgl(across(all_of(annotator_cols)), ~ any(c(...) %in% NOT_DM))) else df

  alpha_o <- krippendorff_alpha_jaccard(df_global, annotator_cols, label_set)
  kappa_o <- fleiss_kappa_overall(df_global, annotator_cols)
  bp_o    <- brennan_prediger_overall(df_global, annotator_cols)
  ac1_o   <- gwet_ac1_at_least_one(df_global, annotator_cols, label_set)

  summary_tbl <- tibble(
    Livello = level_name,
    Metrica = c("Raw (pairwise mean)", "Jaccard (pairwise mean)",
                "Alpha overall (m raters)", "Fleiss kappa overall (single-tag)",
                "Brennan-Prediger S overall", "Gwet AC1 overall (at-least-one)"),
    Media   = c(mean(pairwise_tbl$Raw, na.rm = TRUE), mean(pairwise_tbl$Jaccard, na.rm = TRUE),
                alpha_o$alpha, kappa_o$kappa, bp_o$S, ac1_o$ac1),
    n       = c(NA, NA, alpha_o$n, kappa_o$n, bp_o$n, ac1_o$n)
  )

  prevalence_tbl <- if (length(label_set) > 0)
    prevalence_diagnostics_per_label(df_global, annotator_cols, label_set) else NULL

  list(summary = summary_tbl, pairwise_tbl = pairwise_tbl, prevalence_tbl = prevalence_tbl)
}


#######################################################################
# PART B - DATA LOADING & PREP (Module 0)
# CSV -> Detection (DM / Not_DM) + Macro (3 macrofunctions) + Micro
# (20 microfunctions). Multi-label lists are kept as list-columns.
#######################################################################

interactional_cols <- c("Presa.di.turno", "Richiesta.di.accordo.conferma",
                        "Manifestazione.di.accordo", "Conferma.dell.attenzione",
                        "Interruzione", "Cessione.del.turno",
                        "Marcatura.della.conoscenza.condivisa",
                        "Richiesta.di.attenzione", "Strategie.di.cortesia")
metatextual_cols <- c("Gestione.del.topic..introduzione.o.ripresa.di.topic",
                      "Chiusura.di.un.topic", "Prolettico..marca.di.formulazione..ecco",
                      "Riformulazione", "Marcatura.di.citazione.discorso.riportato",
                      "Esemplificazione", "General.extenders.e.marche.di.generalizzazione")
cognitive_cols <- c("Marcatura.dell.inferenza",
                    "Filler..riempimento.dei.tempi.di.formulazione",
                    "Modulazione.del.grado.di.confidenza.del.parlante",
                    "Approssimazione", "Specificazione", "Attenuazione", "Intensificazione")
valid_micro_labels <- c(interactional_cols, metatextual_cols, cognitive_cols)

get_macro_label <- function(row, det_status) {
  if (det_status != "DM") return(det_status)
  labs <- character()
  if (any(row[interactional_cols] == "1", na.rm = TRUE)) labs <- c(labs, "Interactional")
  if (any(row[metatextual_cols]  == "1", na.rm = TRUE)) labs <- c(labs, "Meta-textual")
  if (any(row[cognitive_cols]    == "1", na.rm = TRUE)) labs <- c(labs, "Cognitive")
  if (length(labs) == 0) NOT_DM else labs
}
get_micro_label <- function(row, det_status) {
  if (det_status != "DM") return(det_status)
  f <- intersect(names(row)[which(row == "1")], valid_micro_labels)
  if (length(f) == 0) NOT_DM else f
}

load_corpus <- function(data_folder) {
  file_map <- c(
    Ann_Tir1      = file.path(data_folder, "Ann_Tir1.csv"),
    Ann_Tir2      = file.path(data_folder, "Ann_Tir2.csv"),
    Ann_Esp1      = file.path(data_folder, "Ann_Esp1.csv"),
    Ann_Esp2      = file.path(data_folder, "Ann_Esp2.csv"),
    Ann_EspCoppia = file.path(data_folder, "Ann_EspCoppia.csv")  # optional
  )
  file_map <- file_map[file.exists(file_map)]
  if (length(file_map) < 2)
    stop("Fewer than 2 annotator files found in '", data_folder, "'. Check the working directory.")
  annotator_ids <- names(file_map)

  detection_list <- macro_list <- micro_list <- list()
  for (ann_id in annotator_ids) {
    df_raw <- read.csv(file_map[[ann_id]], sep = ";", header = TRUE)

    non_sd_col <- intersect(c("Non.SD", "NonSD", "Non_SD", "non.SD"), colnames(df_raw))
    df_raw$Non_SD_val <- if (length(non_sd_col) == 0) "0" else trimws(as.character(df_raw[[non_sd_col[1]]]))
    df_raw$SD_val <- trimws(as.character(df_raw$SD))
    df_raw$SD_val[is.na(df_raw$SD_val) | df_raw$SD_val == ""] <- "0"
    df_raw$Non_SD_val[is.na(df_raw$Non_SD_val) | df_raw$Non_SD_val == ""] <- "0"

    func_cols <- intersect(valid_micro_labels, colnames(df_raw))
    has_any <- apply(df_raw[func_cols], 1, function(r) any(trimws(as.character(r)) == "1", na.rm = TRUE))

    # Prevalent classification:
    # SD==1 -> DM; NonSD==1 -> Not_DM; both 0 & a function -> DM (inferred);
    # both 0 & no function -> EXCLUDE_TOKEN (never analysed).
    df_raw <- df_raw %>% mutate(det_status = case_when(
      SD_val == "1" ~ "DM",
      Non_SD_val == "1" ~ NOT_DM,
      SD_val == "0" & Non_SD_val == "0" & has_any ~ "DM",
      TRUE ~ EXCLUDE_TOKEN))
    df_raw[is.na(df_raw)] <- "0"

    df_out <- df_raw %>% rowwise() %>% mutate(
      !!ann_id := det_status,
      !!paste0(ann_id, "_macro") := list(get_macro_label(cur_data(), det_status)),
      !!paste0(ann_id, "_micro") := list(get_micro_label(cur_data(), det_status))
    ) %>% ungroup()

    detection_list[[ann_id]] <- df_out %>% select(Token.number, !!ann_id)
    macro_list[[ann_id]]     <- df_out %>% select(Token.number, !!paste0(ann_id, "_macro"))
    micro_list[[ann_id]]     <- df_out %>% select(Token.number, !!paste0(ann_id, "_micro"))
  }

  df_detection <- reduce(detection_list, full_join, by = "Token.number") %>% arrange(Token.number)
  df_macro     <- reduce(macro_list,     full_join, by = "Token.number") %>% arrange(Token.number)
  df_micro     <- reduce(micro_list,     full_join, by = "Token.number") %>% arrange(Token.number)

  core_ids <- setdiff(annotator_ids, "Ann_EspCoppia")

  # Drop tokens that are EXCLUDE_TOKEN / NA for any core annotator.
  token_esclusi <- df_detection$Token.number[
    apply(as.matrix(df_detection[core_ids]), 1, function(x) any(is.na(x) | x == EXCLUDE_TOKEN))]
  if (length(token_esclusi) > 0) {
    df_detection <- df_detection %>% filter(!Token.number %in% token_esclusi)
    df_macro     <- df_macro     %>% filter(!Token.number %in% token_esclusi)
    df_micro     <- df_micro     %>% filter(!Token.number %in% token_esclusi)
  }
  cat(sprintf("Loaded %d annotators; %d tokens; %d excluded.\n",
              length(annotator_ids), nrow(df_detection), length(token_esclusi)))

  list(df_detection = df_detection, df_macro = df_macro, df_micro = df_micro,
       annotator_ids = annotator_ids, core_ids = core_ids)
}


#######################################################################
# PART C - ANALYSES (all recomputed from the loaded data)
#######################################################################

# ---- C2. Positive/specific agreement per label (Cicchetti & Feinstein).
positive_agreement_per_label <- function(df, annotator_cols, label_set) {
  m <- length(annotator_cols)
  bind_rows(lapply(label_set, function(lab) {
    n11 <- n10 <- n01 <- 0
    for (i in 1:(m - 1)) for (j in (i + 1):m) {
      a <- sapply(df[[annotator_cols[i]]], function(x) lab %in% x)
      b <- sapply(df[[annotator_cols[j]]], function(x) lab %in% x)
      n11 <- n11 + sum(a & b); n10 <- n10 + sum(a & !b); n01 <- n01 + sum(!a & b)
    }
    n_occ <- 2 * n11 + n10 + n01
    tibble(Label = lab,
           Positive_Agreement = if (n_occ == 0) NA else 2 * n11 / n_occ,
           N_occorrenze = sum(sapply(df[annotator_cols], function(col) sum(sapply(col, function(x) lab %in% x)))))
  })) %>% arrange(Positive_Agreement)
}

# ---- C3. Label confusion matrix for a single pair (non-shared labels).
pairwise_confusion <- function(df, col_a, col_b, label_set, include_not_dm = FALSE) {
  full <- if (include_not_dm) c(NOT_DM, label_set) else label_set
  n <- length(full); mat <- matrix(0, n, n, dimnames = list(full, full))
  A <- df[[col_a]]; B <- df[[col_b]]
  for (k in seq_along(A)) {
    a <- A[[k]]; b <- B[[k]]
    if (!include_not_dm) { a <- setdiff(a, NOT_DM); b <- setdiff(b, NOT_DM) }
    only_a <- setdiff(a, b); only_b <- setdiff(b, a)
    if (length(only_a) > 0 && length(only_b) > 0)
      for (la in only_a) for (lb in only_b)
        if (la %in% full && lb %in% full) mat[la, lb] <- mat[la, lb] + 1
  }
  mat
}
confusion_all_pairs <- function(df, annotator_cols, label_set, include_not_dm = FALSE) {
  m <- length(annotator_cols); out <- list()
  for (i in 1:(m - 1)) for (j in (i + 1):m)
    out[[paste(annotator_cols[i], "vs", annotator_cols[j])]] <-
      pairwise_confusion(df, annotator_cols[i], annotator_cols[j], label_set, include_not_dm)
  out
}
# Aggregated top confusions across all pairs.
confusion_aggregate <- function(df, annotator_cols, label_set) {
  m <- length(annotator_cols)
  conf <- expand.grid(Label_A = label_set, Label_B = label_set, stringsAsFactors = FALSE) %>% mutate(count = 0)
  for (i in 1:(m - 1)) for (j in (i + 1):m) {
    mat <- pairwise_confusion(df, annotator_cols[i], annotator_cols[j], label_set)
    long <- as.data.frame(as.table(mat))
    for (r in which(long$Freq > 0)) {
      idx <- which(conf$Label_A == as.character(long$Var1[r]) & conf$Label_B == as.character(long$Var2[r]))
      conf$count[idx] <- conf$count[idx] + long$Freq[r]
    }
  }
  conf %>% filter(count > 0) %>% arrange(desc(count))
}
# Disagreement systematicity: normalised entropy + share of the top cell.
confusion_consistency <- function(mat) {
  vals <- as.vector(mat); vals <- vals[vals > 0]
  if (length(vals) == 0) return(tibble(n_confusioni = 0, entropia_norm = NA, quota_top1 = NA))
  p <- vals / sum(vals); H <- -sum(p * log2(p)); Hmax <- log2(length(vals))
  tibble(n_confusioni = sum(vals),
         entropia_norm = if (Hmax == 0) NA else H / Hmax,  # ~0 concentrated, ~1 spread
         quota_top1 = max(p))
}

# ---- C4. Individual style metrics.
label_frequency_by_annotator <- function(df, annotator_cols, label_set) {
  bind_rows(lapply(annotator_cols, function(col) {
    counts <- sapply(label_set, function(lab) sum(sapply(df[[col]], function(x) lab %in% x)))
    tibble(Annotatore = col, Label = label_set, Count = counts) %>% mutate(Proporzione = Count / sum(Count))
  }))
}
polifunzionalita_by_annotator <- function(df, annotator_cols) {
  bind_rows(lapply(annotator_cols, function(col) {
    cards <- sapply(df[[col]], function(x) length(setdiff(x, NOT_DM)))
    cards <- cards[cards > 0]
    tibble(Annotatore = col, Cardinalita_media = mean(cards), Prop_multitag = mean(cards > 1))
  }))
}
sd_detection_rate <- function(df_detection, annotator_cols)
  sapply(annotator_cols, function(col) mean(df_detection[[col]] == "DM", na.rm = TRUE))

# Hill numbers q0/q1/q2 (richness, exp-Shannon, inverse-Simpson).
hill_number <- function(p, q) {
  p <- p[p > 0]; if (length(p) == 0) return(NA)
  if (abs(q - 1) < 1e-8) return(exp(-sum(p * log(p))))
  sum(p^q)^(1 / (1 - q))
}
hill_numbers_by_annotator <- function(freq_tbl, qs = c(0, 1, 2)) {
  bind_rows(lapply(unique(freq_tbl$Annotatore), function(ann) {
    p <- freq_tbl %>% filter(Annotatore == ann) %>% pull(Proporzione)
    vals <- setNames(sapply(qs, function(q) hill_number(p, q)), paste0("Hill_q", qs))
    tibble(Annotatore = ann) %>% bind_cols(as_tibble(as.list(vals)))
  }))
}
leave_one_out_agreement <- function(pairwise_tbl, annotator_cols)
  sapply(annotator_cols, function(ann)
    mean(pairwise_tbl %>% filter(grepl(ann, Coppia, fixed = TRUE)) %>% pull(Jaccard), na.rm = TRUE))

# ---- C5. Bias analyses.
# Individual signature: each annotator vs the pooled others (chi-square
# goodness-of-fit); standardised residuals flag over/under-used labels.
individual_bias_test <- function(df, annotator_cols, label_set) {
  freq_tbl <- label_frequency_by_annotator(df, annotator_cols, label_set)
  bind_rows(lapply(annotator_cols, function(ann) {
    others <- setdiff(annotator_cols, ann)
    observed <- freq_tbl %>% filter(Annotatore == ann) %>% arrange(Label) %>% pull(Count)
    pooled <- freq_tbl %>% filter(Annotatore %in% others) %>%
      group_by(Label) %>% summarise(Count = sum(Count), .groups = "drop") %>% arrange(Label)
    expected_p <- pooled$Count / sum(pooled$Count)
    chisq <- tryCatch(suppressWarnings(chisq.test(x = observed, p = expected_p)), error = function(e) NULL)
    tibble(Annotatore = ann, Label = sort(label_set), Osservato = observed,
           Atteso_prop = expected_p,
           Residuo_standardizzato = if (!is.null(chisq)) chisq$stdres else rep(NA, length(observed)),
           p_value_globale = if (!is.null(chisq)) chisq$p.value else NA)
  }))
}
# Group bias naive vs expert (chi-square), restricted to tokens marked DM
# by all annotators in the comparison so the denominator is common.
filter_common_dm <- function(df, annotator_cols) {
  keep <- apply(sapply(annotator_cols, function(col) !sapply(df[[col]], function(x) NOT_DM %in% x)), 1, all)
  df[keep, ]
}
group_bias_test <- function(df, annotator_cols, group_map, label_set, common = TRUE) {
  if (common) df <- filter_common_dm(df, annotator_cols)
  freq_tbl <- label_frequency_by_annotator(df, annotator_cols, label_set) %>%
    mutate(Gruppo = group_map[Annotatore]) %>%
    group_by(Gruppo, Label) %>% summarise(Count = sum(Count), .groups = "drop") %>%
    pivot_wider(names_from = Gruppo, values_from = Count, values_fill = 0)
  if (ncol(freq_tbl) - 1 < 2) return(list(tabella = freq_tbl, chisq = NULL, n = nrow(df)))
  m <- as.matrix(freq_tbl[, -1]); rownames(m) <- freq_tbl$Label
  list(tabella = freq_tbl, chisq = tryCatch(chisq.test(m), error = function(e) NULL), n = nrow(df))
}
# Gold-standard agreement: each annotator vs Ann_EspCoppia (micro).
gold_agreement <- function(df_micro, annotator_cols, gold_col = "Ann_EspCoppia_micro") {
  if (!gold_col %in% colnames(df_micro)) return(NULL)
  tibble(Annotatore = annotator_cols,
         Jaccard_vs_gold = sapply(annotator_cols, function(col)
           mean(mapply(jaccard_pair, df_micro[[col]], df_micro[[gold_col]]), na.rm = TRUE)))
}

# ---- run all analyses for a loaded corpus -----------------------------
run_analyses <- function(dat) {
  cols_det   <- dat$core_ids
  cols_macro <- paste0(dat$core_ids, "_macro")
  cols_micro <- paste0(dat$core_ids, "_micro")

  label_macro <- setdiff(unique(unlist(dat$df_macro[cols_macro])), NOT_DM)
  label_micro <- setdiff(unique(unlist(dat$df_micro[cols_micro])), NOT_DM)

  res_det   <- compute_all_agreement(dat$df_detection, cols_det,   "Detection")
  res_macro <- compute_all_agreement(dat$df_macro,     cols_macro, "Macro", filter_notdm = TRUE)
  res_micro <- compute_all_agreement(dat$df_micro,     cols_micro, "Micro", filter_notdm = TRUE)

  pa_macro <- positive_agreement_per_label(dat$df_macro, cols_macro, label_macro)
  pa_micro <- positive_agreement_per_label(dat$df_micro, cols_micro, label_micro)

  conf_by_pair    <- confusion_all_pairs(dat$df_micro, cols_micro, label_micro, include_not_dm = TRUE)
  conf_aggregate  <- confusion_aggregate(dat$df_micro, cols_micro, label_micro)
  consistency     <- bind_rows(lapply(names(conf_by_pair), function(nm)
    bind_cols(Coppia = nm, confusion_consistency(conf_by_pair[[nm]])))) %>% arrange(entropia_norm)

  freq_micro <- label_frequency_by_annotator(dat$df_micro, cols_micro, label_micro)
  poly_micro <- polifunzionalita_by_annotator(dat$df_micro, cols_micro)
  det_rate   <- sd_detection_rate(dat$df_detection, cols_det)
  hill_micro <- hill_numbers_by_annotator(freq_micro)
  loo_micro  <- leave_one_out_agreement(res_micro$pairwise_tbl, cols_micro)

  bias_ind_micro <- individual_bias_test(dat$df_micro, cols_micro, label_micro)
  bias_grp_micro <- if (length(dat$core_ids) == 4) {
    gm <- setNames(ifelse(grepl("Tir", cols_micro), "naive", "expert"), cols_micro)
    group_bias_test(dat$df_micro, cols_micro, gm, label_micro, common = TRUE)
  } else NULL
  gold <- gold_agreement(dat$df_micro, cols_micro)

  list(res_det = res_det, res_macro = res_macro, res_micro = res_micro,
       pa_macro = pa_macro, pa_micro = pa_micro,
       conf_by_pair = conf_by_pair, conf_aggregate = conf_aggregate, consistency = consistency,
       freq_micro = freq_micro, poly_micro = poly_micro, det_rate = det_rate,
       hill_micro = hill_micro, loo_micro = loo_micro,
       bias_ind_micro = bias_ind_micro, bias_grp_micro = bias_grp_micro, gold = gold)
}


#######################################################################
# PART D - PLOTS (mirror slides 15-28)
# Every plot takes its data from the analysis objects computed above.
#######################################################################

invisible(suppressWarnings(tryCatch(Sys.setlocale("LC_ALL", "C.UTF-8"), error = function(e) "")))
base_family <- "DejaVu Sans"
if (!dir.exists(out_dir)) dir.create(out_dir)

col_cat <- c("Tirocinante" = "#C97F7F", "Esperto" = "#3C7F63", "Coppia" = "#7FB59B")
col_mds <- c("Naive" = "#C97F7F", "Esperto" = "#3C7F63", "Coppia" = "#7FB59B")
livelli_ord <- c("Detection", "Macro", "Micro")
ord_annot   <- c("Esp1", "Esp2", "Coppia", "Tir1", "Tir2")

# Short annotator code ("Ann_Esp1_micro" -> "Esp1").
short_ann <- function(x) {
  x <- gsub("_(micro|macro)$", "", x); x <- gsub("^Ann_", "", x)
  ifelse(x == "EspCoppia", "Coppia", x)
}
cat_annot <- function(a) case_when(a %in% c("Tir1", "Tir2") ~ "Tirocinante",
                                    a == "Coppia" ~ "Coppia", TRUE ~ "Esperto")

tema_slide <- theme_minimal(base_size = 15, base_family = base_family) +
  theme(panel.grid.minor = element_blank(), panel.grid.major.x = element_blank(),
        plot.title = element_text(face = "bold", size = 17),
        plot.subtitle = element_text(color = "grey35", size = 12),
        axis.title.x = element_blank(), legend.title = element_blank(), legend.position = "top")

salva <- function(p, nome, w = 8, h = 5.5) {
  dev <- if (requireNamespace("ragg", quietly = TRUE)) ragg::agg_png else NULL
  ggsave(file.path(out_dir, paste0(nome, ".png")), p, width = w, height = h, dpi = 300, bg = "white", device = dev)
}

# Slide 15: SD detection rate per annotator (from det_rate).
plot_detection_rate <- function(det_rate, corpus_name) {
  df <- tibble(annotatore = short_ann(names(det_rate)), tasso = as.numeric(det_rate)) %>%
    mutate(categoria = cat_annot(annotatore), annotatore = factor(annotatore, levels = ord_annot))
  ggplot(df, aes(annotatore, tasso, fill = categoria)) +
    geom_col(width = .66) +
    geom_text(aes(label = percent(tasso, accuracy = .1)), vjust = -.5, size = 4.6, fontface = "bold") +
    scale_fill_manual(values = col_cat, breaks = names(col_cat)) +
    scale_y_continuous(labels = percent, expand = expansion(mult = c(0, .15))) +
    labs(title = paste("Detection rate -", corpus_name),
         subtitle = "% of tokens classified as discourse marker", y = NULL) + tema_slide
}

# Slide 26: Hill diversity numbers (from hill_micro).
plot_hill <- function(hill_micro, corpus_name) {
  df <- hill_micro %>% mutate(annotatore = short_ann(Annotatore)) %>%
    mutate(annotatore = factor(annotatore, levels = ord_annot)) %>%
    pivot_longer(c(Hill_q0, Hill_q1, Hill_q2), names_to = "ordine", values_to = "valore") %>%
    mutate(ordine = recode(ordine, Hill_q0 = "q0 richness", Hill_q1 = "q1 exp-Shannon", Hill_q2 = "q2 inv-Simpson"),
           ordine = factor(ordine, levels = c("q0 richness", "q1 exp-Shannon", "q2 inv-Simpson")))
  ggplot(df, aes(annotatore, valore, fill = ordine)) +
    geom_col(position = position_dodge(.8), width = .72) +
    geom_text(aes(label = sprintf("%.1f", valore)), position = position_dodge(.8), vjust = -.4, size = 3.6) +
    scale_fill_manual(values = c("q0 richness" = "#2F4858", "q1 exp-Shannon" = "#3C7F63", "q2 inv-Simpson" = "#B8336A")) +
    scale_y_continuous(expand = expansion(mult = c(0, .15))) +
    labs(title = paste("Hill numbers -", corpus_name),
         subtitle = "Diversity in microfunction use per annotator", y = NULL) + tema_slide
}

# Slide 39: polyfunctionality rate (from poly_micro).
plot_polifunzionalita <- function(poly_micro, corpus_name) {
  df <- poly_micro %>% mutate(annotatore = short_ann(Annotatore)) %>%
    mutate(categoria = cat_annot(annotatore), annotatore = factor(annotatore, levels = ord_annot))
  ggplot(df, aes(annotatore, Prop_multitag, fill = categoria)) +
    geom_col(width = .66) +
    geom_text(aes(label = sprintf("%s\ncard. %.2f", percent(Prop_multitag, accuracy = .1), Cardinalita_media)),
              vjust = -.35, size = 3.9, lineheight = .95) +
    scale_fill_manual(values = col_cat, breaks = names(col_cat)) +
    scale_y_continuous(labels = percent, expand = expansion(mult = c(0, .22))) +
    labs(title = paste("Polyfunctionality rate -", corpus_name),
         subtitle = "% of double-labelled tokens . card. = mean labels per token", y = NULL) + tema_slide
}

# Slide 21: Positive Agreement per microfunction (from pa_micro).
plot_top_pa <- function(pa_micro, corpus_name, top_n = 10) {
  df <- pa_micro %>% rename(microfunzione = Label, pa = Positive_Agreement, n = N_occorrenze) %>%
    filter(!is.na(pa)) %>% arrange(desc(pa)) %>% slice_head(n = top_n) %>%
    mutate(microfunzione = fct_reorder(microfunzione, pa))
  ggplot(df, aes(microfunzione, pa)) +
    geom_col(fill = "#2F4858", width = .7) +
    geom_text(aes(label = sprintf("%.2f  (n=%d)", pa, n)), hjust = -.08, size = 3.8) +
    coord_flip() +
    scale_y_continuous(limits = c(0, max(df$pa) * 1.22), expand = expansion(mult = c(0, .02))) +
    labs(title = paste("Positive Agreement per microfunction -", corpus_name),
         subtitle = "Micro level . n = occurrences of the microfunction", x = NULL, y = "Positive Agreement") +
    theme_minimal(base_size = 14, base_family = base_family) +
    theme(panel.grid.major.y = element_blank(), plot.title = element_text(face = "bold", size = 16),
          axis.title.y = element_blank())
}

# Build the pairwise-by-level object the experience/MDS plots need.
build_pairwise_long <- function(res_list) {
  bind_rows(lapply(res_list, function(res) res$pairwise_tbl %>%
    mutate(level = recode(Livello, Detection = "Detection", Macro = "Macro", Micro = "Micro")) %>%
    separate(Coppia, into = c("ann_a", "ann_b"), sep = " vs ") %>%
    mutate(ann_a = short_ann(ann_a), ann_b = short_ann(ann_b),
           is_coppia = ann_a == "Coppia" | ann_b == "Coppia") %>%
    rename(raw = Raw, jaccard = Jaccard, ac1 = AC1)))
}

# Slide 23: agreement by experience (Tir x Tir / Esp x Esp / cross).
plot_naive_expert_cross <- function(pairwise, corpus_name, metrica = "ac1") {
  calc <- function(d) tibble(
    Gruppo = c("Tir\u00d7Tir", "Esp\u00d7Esp", "Cross"),
    valore = c(d %>% filter(ann_a == "Tir1", ann_b == "Tir2") %>% pull(.data[[metrica]]),
               d %>% filter(ann_a == "Esp1", ann_b == "Esp2") %>% pull(.data[[metrica]]),
               d %>% filter(!is_coppia, xor(ann_a %in% c("Tir1","Tir2"), ann_b %in% c("Tir1","Tir2"))) %>%
                 pull(.data[[metrica]]) %>% mean()))
  dati <- pairwise %>% filter(!is_coppia) %>% group_by(level) %>% group_modify(~ calc(.x)) %>% ungroup() %>%
    mutate(level = factor(level, levels = livelli_ord),
           Gruppo = factor(Gruppo, levels = c("Tir\u00d7Tir", "Esp\u00d7Esp", "Cross")))
  nl <- length(livelli_ord); bw <- .8 / nl
  dati <- dati %>% mutate(x = as.numeric(Gruppo) + (as.numeric(level) - (nl + 1) / 2) * bw)
  ggplot(dati, aes(x, valore, fill = level)) +
    geom_col(width = bw * .92) +
    geom_text(aes(label = sprintf("%.2f", valore)), vjust = -.6, size = 3.4) +
    scale_x_continuous(breaks = 1:3, labels = levels(dati$Gruppo)) +
    scale_fill_manual(values = c(Detection = "#2F4858", Macro = "#E3A73E", Micro = "#B8336A"), name = "Level") +
    scale_y_continuous(expand = expansion(mult = c(0, .18))) +
    labs(title = corpus_name, subtitle = "Agreement by annotator experience level", y = NULL) + tema_slide
}

# Slide 24: 2D MDS of annotator similarity, one panel per level.
plot_mds_panel <- function(pairwise, corpus_name, metrica = "ac1") {
  annot <- c("Tir1", "Tir2", "Esp1", "Esp2", "Coppia")
  build <- function(lv) {
    sub <- pairwise %>% filter(level == lv)
    M <- matrix(1, 5, 5, dimnames = list(annot, annot))
    for (i in seq_len(nrow(sub))) M[sub$ann_a[i], sub$ann_b[i]] <- M[sub$ann_b[i], sub$ann_a[i]] <- sub[[metrica]][i]
    diss <- 1 - M; diag(diss) <- 0
    fit <- cmdscale(as.dist(diss), k = 2)
    tibble(annotatore = rownames(fit), dim1 = fit[, 1], dim2 = fit[, 2], level = lv)
  }
  dati <- bind_rows(lapply(livelli_ord, build)) %>%
    mutate(level = factor(level, levels = livelli_ord),
           gruppo = case_when(annotatore %in% c("Tir1","Tir2") ~ "Naive",
                              annotatore == "Coppia" ~ "Coppia", TRUE ~ "Esperto"))
  ggplot(dati, aes(dim1, dim2, fill = gruppo)) +
    geom_point(size = 6, shape = 21, colour = "black", stroke = 1.1) +
    geom_label_repel(aes(label = annotatore), size = 4.2, fontface = "bold", colour = "black", fill = "white",
                     segment.color = "black", show.legend = FALSE, family = base_family) +
    facet_wrap(~level, nrow = 1, scales = "free") +
    scale_fill_manual(values = col_mds, breaks = c("Naive", "Esperto", "Coppia")) +
    labs(title = paste("2D annotator similarity (MDS) -", corpus_name),
         subtitle = "Classical MDS on 1 - pairwise AC1, per level", x = NULL, y = NULL) +
    theme_minimal(base_size = 14, base_family = base_family) +
    theme(axis.text = element_blank(), axis.ticks = element_blank(), panel.grid = element_blank(),
          panel.border = element_rect(colour = "black", fill = NA, linewidth = 1),
          plot.title = element_text(face = "bold", size = 17), legend.title = element_blank(),
          legend.position = "top", strip.text = element_text(face = "bold", size = 13))
}

# Slide 27: over/under-used labels per annotator (bias bubble),
# from the individual-bias standardised residuals (top |res| per annotator).
plot_bias_bubble <- function(bias_ind_micro, corpus_name, top_k = 3, tetto = 20) {
  df <- bias_ind_micro %>% filter(!is.na(Residuo_standardizzato)) %>%
    mutate(annotatore = short_ann(Annotatore),
           residuo_capped = pmin(pmax(Residuo_standardizzato, -tetto), tetto)) %>%
    group_by(Annotatore) %>% slice_max(abs(Residuo_standardizzato), n = top_k) %>% ungroup() %>%
    mutate(label = fct_reorder(Label, residuo_capped),
           annotatore = factor(annotatore, levels = ord_annot))
  ggplot(df, aes(annotatore, label)) +
    geom_point(aes(size = abs(residuo_capped), color = residuo_capped)) +
    geom_text(aes(label = Osservato), size = 3.2, color = "white", fontface = "bold") +
    scale_color_gradient2(low = "#C1443A", mid = "grey90", high = "#3C7F63", midpoint = 0, name = "std. res.") +
    scale_size_continuous(range = c(7, 15), guide = "none") +
    labs(title = corpus_name, subtitle = "Over/under-used labels per annotator (chi-square leave-one-out)",
         x = NULL, y = NULL) +
    theme_minimal(base_size = 13) +
    theme(panel.grid.major.x = element_blank(), plot.title = element_text(face = "bold", size = 16),
          plot.subtitle = element_text(color = "grey35", size = 11), legend.position = "right")
}


#######################################################################
# PART E - RUN EVERYTHING
#######################################################################

run_corpus <- function(corpus_name = CORPUS, folder = data_folder) {
  dat <- load_corpus(folder)
  res <- run_analyses(dat)
  pairwise_long <- build_pairwise_long(list(res$res_det, res$res_macro, res$res_micro))

  # --- console report (everything except the "dubbi" analysis) ---
  cat("\n=========================== ", corpus_name, " ===========================\n")
  cat("\n--- Overall agreement per level ---\n")
  print(bind_rows(res$res_det$summary, res$res_macro$summary, res$res_micro$summary), n = Inf)
  cat("\n--- Pairwise (Detection) ---\n"); print(res$res_det$pairwise_tbl, n = Inf)
  cat("\n--- Pairwise (Macro) ---\n");     print(res$res_macro$pairwise_tbl, n = Inf)
  cat("\n--- Pairwise (Micro) ---\n");     print(res$res_micro$pairwise_tbl, n = Inf)
  cat("\n--- Positive agreement (macro) ---\n"); print(res$pa_macro, n = Inf)
  cat("\n--- Positive agreement (micro) ---\n"); print(res$pa_micro, n = Inf)
  cat("\n--- Prevalence diagnostics (micro) ---\n"); print(res$res_micro$prevalence_tbl, n = Inf)
  cat("\n--- Top aggregated confusions (micro) ---\n"); print(head(res$conf_aggregate, 15))
  cat("\n--- Disagreement systematicity (entropy, micro) ---\n"); print(res$consistency, n = Inf)
  cat("\n--- Hill numbers (micro) ---\n"); print(res$hill_micro, n = Inf)
  cat("\n--- Polyfunctionality (micro) ---\n"); print(res$poly_micro, n = Inf)
  cat("\n--- Detection rate ---\n"); print(res$det_rate)
  cat("\n--- Leave-one-out agreement (micro, Jaccard) ---\n"); print(res$loo_micro)
  cat("\n--- Individual bias p-values (micro) ---\n")
  print(res$bias_ind_micro %>% distinct(Annotatore, p_value_globale))
  if (!is.null(res$bias_grp_micro)) {
    cat("\n--- Group bias naive vs expert (micro, common tokens) ---\n")
    print(res$bias_grp_micro$tabella); if (!is.null(res$bias_grp_micro$chisq)) print(res$bias_grp_micro$chisq)
  }
  if (!is.null(res$gold)) { cat("\n--- Gold-standard agreement (micro) ---\n"); print(res$gold) }

  # --- plots ---
  tag <- tolower(corpus_name)
  salva(plot_detection_rate(res$det_rate, corpus_name),      paste0("01_detection_rate_", tag))
  salva(plot_hill(res$hill_micro, corpus_name),              paste0("02_hill_", tag))
  salva(plot_polifunzionalita(res$poly_micro, corpus_name),  paste0("03_polyfunctionality_", tag))
  salva(plot_top_pa(res$pa_micro, corpus_name, 10),          paste0("04_top10_positive_agreement_", tag), w = 9)
  salva(plot_naive_expert_cross(pairwise_long, corpus_name), paste0("05_experience_cross_", tag), w = 9)
  salva(plot_mds_panel(pairwise_long, corpus_name),          paste0("06_mds_", tag), w = 11, h = 4.5)
  salva(plot_bias_bubble(res$bias_ind_micro, corpus_name),   paste0("07_bias_bubble_", tag), w = 8, h = 7)

  cat("\nDone. Plots saved in:", normalizePath(out_dir), "\n")
  invisible(res)
}

# Run the currently selected corpus. To do both, set CORPUS/data_folder
# and call run_corpus() again (e.g. run_corpus("Comunque", file.path("..","data","Comunque"))).
res <- run_corpus()
