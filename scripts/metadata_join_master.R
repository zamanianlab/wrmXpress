suppressWarnings(suppressMessages(library(tidyverse)))
suppressWarnings(suppressMessages(library(tidymodels)))
options(readr.show_col_types = FALSE,
        dplyr.summarise.inform = FALSE)
# setwd('~/Desktop/temp_root/')

args = commandArgs(trailingOnly = TRUE)

plate <- args[1]
rows <- args[2]
cols <- args[3]
# plate <- '20220929-p37-KTR_1809'
# rows <- '8'
# cols <- '12'

metadata_dir <- stringr::str_c('metadata', plate, sep = '/')
output_dir <- stringr::str_c('output', 'data/', sep = '/')

# get the paths to all the metadata files
metadata_files <- dplyr::tibble(base = metadata_dir,
                                plate = plate,
                                category = list.files(path = metadata_dir,
                                                      pattern = ".*.csv$",
                                                      recursive = TRUE)) %>%
  dplyr::mutate(path = stringr::str_c(base, category, sep = '/'),
                assay_date = stringr::str_extract(plate, "20[0-9]{6}"),
                category = stringr::str_remove(category, '.csv') %>% stringr::str_remove(., 'metadata/')) %>%
  dplyr::select(path, assay_date, plate, category)


# function to read and tidy the metadata files
get_metadata <- function(...) {

  df <- tibble(...)

  data <- readr::read_csv(df$path,
                          col_names = sprintf("%02d", seq(1:as.numeric(cols))),
                          col_types = str_flatten(rep('c', as.numeric(cols)))) %>%
    dplyr::mutate(row = LETTERS[1:as.numeric(rows)], .before = `01`) %>%
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

output_files <- dplyr::tibble(base = output_dir,
                              plate = plate,
                              data_file = list.files(path = output_dir,
                                                     pattern = ".*.csv$",
                                                     recursive = TRUE)) %>%
  dplyr::mutate(path = stringr::str_c(base, data_file))

read_cp_data <- function(...) {

  df <- tibble(...)

  data <- readr::read_csv(df$path,
                          col_types = cols(.default = "c")) %>%
    dplyr::mutate(ObjectType = df$object) %>%
    tidyr::pivot_longer(cols = !contains(c('Image', 'Metadata', 'FileName', 'PathName', 'Object')), names_to = 'measure', values_to = 'value')

}

if (length(output_files$data_file) > 1) {

  cp_output_files <- output_files %>%
    dplyr::mutate(object = stringr::str_extract(data_file, "_[a-z]*_") %>% stringr::str_remove_all('_'))

  output_data <- cp_output_files %>%
    purrr::pmap_dfr(read_cp_data) %>%
    tidyr:::pivot_wider(names_from = c(ObjectType, measure), values_from = value) %>%
    dplyr::rename(well = Metadata_Well)

} else {

  output_data <- readr::read_csv(output_files$path) %>%
    dplyr::rename_with( ~ case_when(
      . == 'Metadata_Well' ~ 'well',
      TRUE ~ .
    ))
    
}

final_df <- suppressMessages(dplyr::left_join(metadata, output_data)) %>%
  readr::write_csv(file = stringr::str_c(output_dir, '/', plate, '_tidy.csv'))

