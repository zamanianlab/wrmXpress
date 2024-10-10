suppressWarnings(suppressMessages(library(tidyverse)))
suppressWarnings(suppressMessages(library(tidymodels)))
options(readr.show_col_types = FALSE, dplyr.summarise.inform = FALSE)

args <- commandArgs(trailingOnly = TRUE)

plate <- args[1]
filled_rows <- as.numeric(args[2])
cols <- as.numeric(args[3])
pipeline_list <- str_split(args[4], ",")[[1]]

# Get the paths to all the metadata files
metadata_dir <- file.path('metadata', plate)
metadata_files <- dplyr::tibble(base = metadata_dir,
                         plate = plate,
                         category = list.files(path = metadata_dir,
                                               pattern = ".*.csv$",
                                               recursive = TRUE)) %>%
  dplyr::mutate(path = file.path(base, category),
         assay_date = stringr::str_extract(plate, "20[0-9]{6}"),
         category = stringr::str_remove(category, '.csv') %>% stringr::str_remove(., 'metadata/')) %>%
  dplyr::select(path, assay_date, plate, category)

# Function to read and tidy the metadata files
get_metadata <- function(...) {
  df <- tibble(...)
  data <- readr::read_csv(df$path,
                   col_names = sprintf("%02d", seq(1:cols)),
                   col_types = str_flatten(rep('c', cols))) %>%
    dplyr::mutate(row = LETTERS[1:n()], .before = `01`) %>%
    tidyr::pivot_longer(-row, names_to = 'col', values_to = df$category) %>%
    dplyr::mutate(well = stringr::str_c(row, col), plate = df$plate)
}

collapse_rows <- function(x) {
  x <- na.omit(x)
  if (length(x) > 0) first(x) else NA
}

metadata <- metadata_files %>%
  purrr::pmap_dfr(get_metadata) %>%
  dplyr::select(plate, well, row, col, everything()) %>%
  dplyr::group_by(plate, well, row, col) %>%
  dplyr::summarise(dplyr::across(everything(), collapse_rows))

# Read in output files and join with metadata
for (pipeline in pipeline_list) {
  output_dir <- file.path('output', pipeline)
  
  # List only CSV files that contain the plate name
  all_files <- list.files(
    path = output_dir,
    pattern = paste0(plate, ".*\\.csv$"),
    recursive = TRUE
  )
  
  # Filter out any files that contain '_tidy.csv'
  filtered_files <- all_files[!grepl("_tidy\\.csv$", all_files)]
  
  output_files <- dplyr::tibble(
    base = output_dir,
    plate = plate,
    data_file = filtered_files
  ) %>% dplyr::mutate(path = file.path(base, data_file))
  
  # Print the CSV files being considered
  print(paste("Processing files for pipeline:", pipeline))
  print(output_files$data_file)
  
  # Proceed if there are any files left after filtering
  if (nrow(output_files) > 0) {
  output_data <- readr::read_csv(output_files$path) %>% 
    tidyr::separate(well_site, c("well", "site"), sep = "_", remove = TRUE)

  # Join output data and metadata
  final_df <- suppressMessages(dplyr::left_join(metadata, output_data)) %>% 
    dplyr::select(plate, well, site, row, col, everything())
  
  final_csv_path <- file.path(output_dir, paste0(plate, '_tidy.csv'))
  readr::write_csv(final_df, final_csv_path)
    } else {
  # Handle the case where no files were found
  message(paste("No output files found for pipeline:", pipeline))
  }
}



# The commented-out section is for handling multiple CSVs and additional parsing
# Uncomment and modify as needed

# read_cp_data <- function(...) {
#   df <- tibble(...)
#   data <- readr::read_csv(df$path,
#                           col_types = cols(.default = "c")) %>%
#     dplyr::mutate(ObjectType = df$object) %>%
#     tidyr::pivot_longer(cols = !contains(c('Image', 'Metadata', 'FileName', 'PathName', 'Object')), names_to = 'measure', values_to = 'value')
# }
# 
# if (length(output_files$data_file) > 1) {
#   cp_output_files <- output_files %>%
#     dplyr::mutate(object = stringr::str_extract(data_file, "_[a-z]*_") %>% stringr::str_remove_all('_'))
# 
#   output_data <- cp_output_files %>%
#     purrr::pmap_dfr(read_cp_data) %>%
#     tidyr:::pivot_wider(names_from = c(ObjectType, measure), values_from = value) %>%
#     dplyr::rename(well = Metadata_Well)
# } else {
#   output_data <- readr::read_csv(output_files$path) %>%
#     dplyr::rename_with( ~ case_when(
#       . == 'Metadata_Well' ~ 'well',
#       TRUE ~ .
#     ))
# }
