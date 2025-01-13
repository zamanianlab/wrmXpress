suppressWarnings(suppressMessages(library(stringr)))
suppressWarnings(suppressMessages(library(magrittr)))
suppressWarnings(suppressMessages(library(dplyr)))
suppressWarnings(suppressMessages(library(readr)))
options(readr.show_col_types = FALSE, dplyr.summarise.inform = FALSE)

args <- commandArgs(trailingOnly = TRUE)

input <- args[1]
work <- args[2]
output <- args[3]
plate <- args[4]
plate_short <- args[5]
filled_rows <- as.numeric(args[6])
cols <- as.numeric(args[7])
pipeline_list <- str_split(args[8], ",")[[1]]

# Get the paths to all the metadata files
metadata_dir <- stringr::str_c(str_remove(input, "/input"), "metadata", plate, sep = "/")

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
  tryCatch({
    df <- tibble(...)
    if (nrow(df) == 0) {
      warning("Empty input data frame")
      return(tibble())
    }
    
    data <- readr::read_csv(df$path,
                     col_names = sprintf("%02d", seq(1:cols)),
                     col_types = str_flatten(rep('c', cols)))
    
    if (nrow(data) == 0) {
      warning("Empty CSV file: ", df$path)
      return(tibble())
    }
    
    data %>%
      dplyr::mutate(row = LETTERS[1:n()], .before = `01`) %>%
      tidyr::pivot_longer(-row, names_to = 'col', values_to = df$category) %>%
      dplyr::mutate(well = stringr::str_c(row, col), plate = df$plate)
  }, error = function(e) {
    warning("Error processing file: ", e$message)
    return(tibble())
  })
}

collapse_rows <- function(x) {
  x <- na.omit(x)
  if (length(x) > 0) first(x) else NA
}

metadata <- tryCatch({
  metadata_files %>%
    purrr::pmap_dfr(get_metadata) %>%
    {if (nrow(.) > 0) 
      dplyr::select(., plate, well, row, col, everything()) %>%
      dplyr::group_by(plate, well, row, col) %>%
      dplyr::summarise(dplyr::across(everything(), collapse_rows))
     else 
      tibble()}
}, error = function(e) {
  warning("Error in metadata processing: ", e$message)
  return(tibble())
})


# Read in output files and join with metadata
for (pipeline in pipeline_list) {
  output_dir <- stringr::str_c(output, pipeline, sep = "/")
  work_dir <- stringr::str_c(work, pipeline, sep = "/")
  
  # List only CSV files that contain the plate name
  all_files <- list.files(
    path = work_dir,
    pattern = paste0(plate_short, ".*\\.csv$"),
    recursive = TRUE
  )
  
  
  output_files <- dplyr::tibble(
    base = work_dir,
    plate = plate,
    data_file = all_files
  ) %>% 
  dplyr::mutate(path = file.path(base, data_file)) %>%
  dplyr::filter(!str_detect(data_file, "image_paths"))
  
  # Print the CSV files being considered
  print(paste("Processing files for pipeline:", pipeline))
  print(output_files$data_file)
  
  # Proceed if there are any files left after filtering
  if (nrow(output_files) > 0) {
  output_data <- readr::read_csv(output_files$path) %>% 
    dplyr::rename_with( ~ case_when(
      . == 'Metadata_Well' ~ 'well_site',
      TRUE ~ .
    )) %>%
    tidyr::separate(well_site, c("well", "site"), sep = "_", remove = TRUE)

  # Try join, if fails write original output_data
  final_df <- tryCatch({
    suppressMessages(dplyr::left_join(metadata, output_data)) %>% 
      dplyr::select(plate, well, site, row, col, everything())
  }, error = function(e) {
    warning("Join failed: ", e$message, "\nWriting output_data without metadata")
    return(output_data)
  })
  
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
