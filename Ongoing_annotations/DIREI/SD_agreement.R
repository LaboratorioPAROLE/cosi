library(readxl)
library(dplyr)
library(purrr)
library(irr)
library(tidyr)

# path with files
folder_path <- "path/to/your/folder"  # <-- cambia con il tuo path
file_list <- list.files(folder_path, pattern = "\\.xlsx$", full.names = TRUE)

# group columns by macro-function
interactional_cols <- c(
  "Presa di turno", "Richiesta di accordo/conferma", "Conferma dell'attenzione",
  "Interruzione", "Cessione del turno", "Marcatura della conoscenza condivisa",
  "Richiesta di attenzione", "Strategie di cortesia"
)

metatextual_cols <- c(
  "Introduzione di topic/passaggio a un nuovo topic/ripresa di un topic allora, quindi, dopo di che ecc.",
  "Chiusura di un topic", "Riformulazione", "Digressione",
  "Marcatura di citazione/discorso riportato", "Esemplificazione"
)

cognitive_cols <- c(
  "Marcatura dell'inferenza", "Modulazione del grado di confidenza del parlante", "Intensificazione"
)

# annotation of functions in one column
get_dm_label <- function(row, sd_value) {
  if (sd_value != "1") return("Not_DM")
  
  labels <- character()
  # Controllo per Interactional
  if (any(row[interactional_cols] == "1", na.rm = TRUE)) labels <- c(labels, "Interactional")
  # Controllo per Meta-textual
  if (any(row[metatextual_cols] == "1", na.rm = TRUE)) labels <- c(labels, "Meta-textual")
  # Controllo per Cognitive
  if (any(row[cognitive_cols] == "1", na.rm = TRUE)) labels <- c(labels, "Cognitive")
  # Se nessun gruppo è attivo
  if (length(labels) == 0) return("Unclassified") else return(labels)
}

# process files
annotator_dfs <- map2(
  file_list,
  paste0("Ann", seq_along(file_list)),
  function(file, ann_id) {
    df <- read_excel(file)
    
    # check for needed columns
    all_needed_cols <- c("Token number", "SD", interactional_cols, metatextual_cols, cognitive_cols)
    missing_cols <- setdiff(all_needed_cols, names(df))
    if (length(missing_cols) > 0) df[missing_cols] <- ""
    
    df %>%
      rowwise() %>%
      mutate(!!ann_id := list(get_dm_label(cur_data(), SD))) %>%  # assegna DM label come lista
      ungroup() %>%
      select(`Token number`, !!ann_id)
  }
)

# merge by token number
merged_df <- reduce(annotator_dfs, full_join, by = "Token number") %>%
  arrange(`Token number`)

# Calculate agreement (Also partial agreement)
check_agreement <- function(...) {
  vals <- list(...)
  ref <- vals[[1]]
  all(sapply(vals[-1], function(v) any(v %in% ref) || any(ref %in% v)))
}

# agreement column
merged_df <- merged_df %>%
  rowwise() %>%
  mutate(agreement = check_agreement(!!!cur_data()[starts_with("Ann")])) %>%
  ungroup()

# Krippendorf (with Not_DM as valid value)
calculate_krippendorf <- function(data) {
  kripp.alpha(as.matrix(data))$value
}

# Krippendorf (with Not_DM as NA)
calculate_krippendorf_no_NA <- function(data) {
  data_no_NA <- data
  data_no_NA[data_no_NA == "Not_DM"] <- NA  # Imposta Not_DM come NA
  kripp.alpha(as.matrix(data_no_NA))$value
}

# Print results
print_step_report <- function(merged_df, step_name, columns) {
  step_data <- merged_df %>%
    select(c("Token number", columns))
  
  # Calcolo percentuale di accordo
  agreement_pct <- mean(step_data$agreement, na.rm = TRUE) * 100
  num_annotators <- length(columns)
  
  # Krippendorff's Alpha
  step_data_numeric <- step_data %>%
    mutate(across(everything(), ~ as.integer(. %in% "Interactional")))  # Esegui numerizzazione
  kripp_value <- calculate_krippendorf(step_data_numeric)
  
  # Krippendorff's Alpha ( Not_DM as na)
  step_data_no_NA <- step_data_numeric
  step_data_no_NA[step_data_no_NA == 0] <- NA  # Consideriamo 0 come "Not_DM"
  kripp_no_NA_value <- calculate_krippendorf_no_NA(step_data_no_NA)
  
  cat(sprintf("📊 %s:\n", step_name))
  cat(sprintf("Number of annotators: %d\n", num_annotators))
  cat(sprintf("Agreement percentage: %.2f%%\n", agreement_pct))
  cat(sprintf("Krippendorff's Alpha: %.2f\n", kripp_value))
  cat(sprintf("Krippendorff's Alpha (Not_DM as NA): %.2f\n", kripp_no_NA_value))
  cat("\n")
}

# 11. Step 1 - Agreement and Krippendorff for SD
print_step_report(merged_df, "Step 1: Agreement on DM/Not_DM", starts_with("Ann"))

# 12. Step 2 - Agreement and Krippendorff for Macro-Functions
print_step_report(merged_df, "Step 2: Agreement on DM's Macro-Functions", starts_with("Ann"))

# 13. Step 3 - Agreement and Krippendorff for Micro-Functions
print_step_report(merged_df, "Step 3: Agreement on DM's Micro-Functions", starts_with("Ann"))
