library(dplyr)
library(purrr)
library(tidyr)
library(tibble)

# Define macrofunctions(group microfunctions labels)
interactional_cols <- c("Presa.di.turno", "Richiesta.di.accordo.conferma", "Conferma.dell.attenzione",
                        "Interruzione", "Cessione.del.turno", "Marcatura.della.conoscenza.condivisa",
                        "Richiesta.di.attenzione", "Strategie.di.cortesia")

metatextual_cols <- c("Introduzione.di.topic.passaggio.a.un.nuovo.topic.ripresa.di.un.topic.allora..quindi..dopo.di.che.ecc.",
                      "Chiusura.di.un.topic", "Riformulazione", "Digressione",
                      "Marcatura.di.citazione.discorso.riportato", "Esemplificazione")

cognitive_cols <- c("Marcatura.dell.inferenza", "Modulazione.del.grado.di.confidenza.del.parlante", "Intensificazione")

# assign labels (DM vs not_DM)
get_detection_label <- function(sd_value) {
  if (sd_value == "1") return("DM") else return("Not_DM")
}


# All valid micro-labels
valid_micro_labels <- c(
  "Presa.di.turno", "Richiesta.di.accordo.conferma", "Conferma.dell.attenzione",
  "Interruzione", "Cessione.del.turno", "Marcatura.della.conoscenza.condivisa",
  "Richiesta.di.attenzione", "Strategie.di.cortesia",
  "Introduzione.di.topic.passaggio.a.un.nuovo.topic.ripresa.di.un.topic.allora..quindi..dopo.di.che.ecc.",
  "Chiusura.di.un.topic", "Riformulazione", "Digressione",
  "Marcatura.di.citazione.discorso.riportato", "Esemplificazione",
  "Marcatura.dell.inferenza", "Modulazione.del.grado.di.confidenza.del.parlante", "Intensificazione"
)

# Assign Macrolabels
get_macro_label <- function(row, sd_value) {
  if (sd_value != "1") return(c("Not_DM"))  
  
  labels <- character()
  if (any(row[interactional_cols] == "1", na.rm = TRUE)) labels <- c(labels, "Interactional")
  if (any(row[metatextual_cols] == "1", na.rm = TRUE)) labels <- c(labels, "Meta-textual")
  if (any(row[cognitive_cols] == "1", na.rm = TRUE)) labels <- c(labels, "Cognitive")
  
  if (length(labels) == 0) return(c("Not_DM")) else return(labels)
}

# Assign micro-labels
get_micro_label <- function(row, sd_value) {
  if (sd_value != "1") return(c("Not_DM"))  
  
  labels <- names(row)[which(row == "1")]
  
  filtered_labels <- intersect(labels, valid_micro_labels)
  
  if (length(filtered_labels) == 0) return(c("Not_DM")) else return(filtered_labels)
}

# Filelist (Change path) and create dfs
folder_path <- "/Agreement/Task_1/direi"
file_list <- list.files(folder_path, pattern = "\\.csv$", full.names = TRUE)

annotator_dfs_detection <- list()
annotator_dfs_macro <- list()
annotator_dfs_micro <- list()

for (i in seq_along(file_list)) {
  ann_id <- paste0("Ann", i)
  df <- read.csv(file_list[[i]], sep = ";", header = TRUE)
  df[is.na(df)] <- "0"
  
  df <- df %>%
    rowwise() %>%
    mutate(
      !!ann_id := get_detection_label(SD),
      !!paste0(ann_id, "_macro") := list(get_macro_label(cur_data(), SD)),
      !!paste0(ann_id, "_micro") := list(get_micro_label(cur_data(), SD))
    ) %>%
    ungroup() %>%
    select(Token.number, !!ann_id, !!paste0(ann_id, "_macro"), !!paste0(ann_id, "_micro"))
  
  annotator_dfs_detection[[i]] <- df %>% select(Token.number, !!ann_id)
  annotator_dfs_macro[[i]] <- df %>% select(Token.number, !!paste0(ann_id, "_macro"))
  annotator_dfs_micro[[i]] <- df %>% select(Token.number, !!paste0(ann_id, "_micro"))
}

# merge dfs
merged_detection <- reduce(annotator_dfs_detection, full_join, by = "Token.number") %>% arrange(Token.number)
merged_macro <- reduce(annotator_dfs_macro, full_join, by = "Token.number") %>% arrange(Token.number)
merged_micro <- reduce(annotator_dfs_micro, full_join, by = "Token.number") %>% arrange(Token.number)


# compare annotations
compare_annotations <- function(annot1, annot2) {
  if (is.null(annot1) || is.null(annot2) || length(annot1) == 0 || length(annot2) == 0) {
    return(NA)
  }
  intersection <- length(intersect(annot1, annot2))
  union <- length(union(annot1, annot2))
  
  return(intersection / union)
}

# calculate pairwise agreement and mean pairwise agreement
calculate_pairwise_agreement <- function(df, annotator_cols) {
  pairwise_agreement <- matrix(NA, nrow = length(annotator_cols), ncol = length(annotator_cols))
  rownames(pairwise_agreement) <- annotator_cols
  colnames(pairwise_agreement) <- annotator_cols
  
  total_agreement <- 0  # Variabile per la somma totale degli accordi
  total_comparisons <- 0
  
  for (i in 1:(length(annotator_cols) - 1)) {
    for (j in (i + 1):length(annotator_cols)) {
      annot1_col <- annotator_cols[i]
      annot2_col <- annotator_cols[j]
      
      annot1_values <- df[[annot1_col]]
      annot2_values <- df[[annot2_col]]
      
      agreement_vector <- mapply(compare_annotations, annot1_values, annot2_values)
      
      pairwise_agreement[i, j] <- mean(agreement_vector)
      pairwise_agreement[j, i] <- pairwise_agreement[i, j]
      total_agreement <- total_agreement + sum(agreement_vector, na.rm = TRUE)
      total_comparisons <- total_comparisons + length(agreement_vector)
    }
  }
  
  ì
  mean_agreement <- total_agreement / total_comparisons
  cat("\n Valore medio dei confronti inter-annotatori:", round(mean_agreement, 3), "\n")
  
  
  return(pairwise_agreement)
}

#============= Detection Agreement =====#
df_detection <- merged_detection
annotator_cols_detection <- c("Ann1", "Ann2", "Ann3", "Ann4")
pairwise_detection <- calculate_pairwise_agreement(df_detection, annotator_cols_detection)

cat("\n Pairwise Agreement Matrix for Detection:\n")
print(pairwise_detection)


#============= Function Agreement ==#



df_macro <- merged_macro
annotator_cols_macro <- c("Ann1_macro", "Ann2_macro", "Ann3_macro", "Ann4_macro")
df_micro <- merged_micro
annotator_cols_micro <- c("Ann1_micro", "Ann2_micro", "Ann3_micro", "Ann4_micro")


# Compare annotation excluding Not_DM
compare_annotations_filtered <- function(annot1, annot2) {
  if ("Not_DM" %in% annot1 || "Not_DM" %in% annot2) {
    return(NA)
  }
  return(length(intersect(annot1, annot2)) > 0)
}

# number of valid comparisons
calculate_pairwise_agreement_filtered <- function(df, annotator_cols) {
  n <- length(annotator_cols)
  agreement_matrix <- matrix(NA, n, n)
  count_matrix <- matrix(0, n, n)
  rownames(agreement_matrix) <- colnames(agreement_matrix) <- annotator_cols
  rownames(count_matrix) <- colnames(count_matrix) <- annotator_cols
  
  for (i in 1:(n - 1)) {
    for (j in (i + 1):n) {
      a1 <- df[[annotator_cols[i]]]
      a2 <- df[[annotator_cols[j]]]
      
      comparisons <- mapply(compare_annotations_filtered, a1, a2)
      valid_comparisons <- !is.na(comparisons)
      count_matrix[i, j] <- count_matrix[j, i] <- sum(valid_comparisons)
      
      if (sum(valid_comparisons) > 0) {
        agreement_matrix[i, j] <- agreement_matrix[j, i] <- mean(comparisons[valid_comparisons])
      }
    }
  }
  
  diag(agreement_matrix) <- 1
  return(list(agreement_matrix = agreement_matrix, count_matrix = count_matrix))
}

# Calculate agreement (pairwise and mean)
calculate_partial_agreement_filtered <- function(df, annotator_cols) {
  n <- length(annotator_cols)
  partial_agreement_matrix <- matrix(NA, n, n)
  rownames(partial_agreement_matrix) <- colnames(partial_agreement_matrix) <- annotator_cols
  
  total_agreement <- 0
  total_comparisons <- 0
  
  for (i in 1:(n - 1)) {
    for (j in (i + 1):n) {
      
      filtered_df <- df %>%
        filter(!sapply(.data[[annotator_cols[i]]], function(x) "Not_DM" %in% x),
               !sapply(.data[[annotator_cols[j]]], function(x) "Not_DM" %in% x))
      
      if (nrow(filtered_df) > 0) {
        
        overlaps <- mapply(function(x, y) length(intersect(x, y)) / length(union(x, y)),
                           filtered_df[[annotator_cols[i]]],
                           filtered_df[[annotator_cols[j]]])
        
        mean_overlap <- mean(overlaps)
        partial_agreement_matrix[i, j] <- partial_agreement_matrix[j, i] <- mean_overlap
        
        
        total_agreement <- total_agreement + sum(overlaps)
        total_comparisons <- total_comparisons + length(overlaps)
      }
    }
  }
  
  diag(partial_agreement_matrix) <- 1
  
  
  mean_partial_agreement <- total_agreement / total_comparisons
  cat("\n Valore medio dell'accordo parziale (overlap ratio):", round(mean_partial_agreement, 3), "\n")
  
  return(partial_agreement_matrix)
}


result_macro <- calculate_pairwise_agreement_filtered(df_macro, annotator_cols_macro)
cat("\n Numero di confronti (macro):\n")
print(result_macro$count_matrix)


result_micro <- calculate_pairwise_agreement_filtered(df_micro, annotator_cols_micro)
cat("\n Numero di confronti (micro):\n")
print(result_micro$count_matrix)

partial_agreement_macro <- calculate_partial_agreement_filtered(df_macro, annotator_cols_macro)
partial_agreement_micro <- calculate_partial_agreement_filtered(df_micro, annotator_cols_micro)




#============= Partial match (at least one label) =====#


calculate_binary_agreement <- function(df, annotator_cols) {
  n <- length(annotator_cols)
  binary_agreement_matrix <- matrix(NA, n, n)
  rownames(binary_agreement_matrix) <- colnames(binary_agreement_matrix) <- annotator_cols
  
  for (i in 1:(n - 1)) {
    for (j in (i + 1):n) {
      filtered_df <- df %>%
        filter(!sapply(.data[[annotator_cols[i]]], function(x) "Not_DM" %in% x),
               !sapply(.data[[annotator_cols[j]]], function(x) "Not_DM" %in% x))
      
      if (nrow(filtered_df) > 0) {
        binary_agreement <- mapply(function(x, y) as.numeric(length(intersect(x, y)) > 0),
                                   filtered_df[[annotator_cols[i]]],
                                   filtered_df[[annotator_cols[j]]])
        
        binary_agreement_matrix[i, j] <- binary_agreement_matrix[j, i] <- mean(binary_agreement)
      }
    }
  }
  
  diag(binary_agreement_matrix) <- 1
  print(binary_agreement_matrix)
  cat("\n Media del binary agreement:", round(mean(binary_agreement_matrix[lower.tri(binary_agreement_matrix)], na.rm = TRUE), 3), "\n")
  return(binary_agreement_matrix)
}

binary_agreement_macro <- calculate_binary_agreement(df_macro, annotator_cols_macro)
binary_agreement_micro <- calculate_binary_agreement(df_micro, annotator_cols_micro)



