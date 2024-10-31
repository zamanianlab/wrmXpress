suppressWarnings(suppressMessages(library(tidyverse)))

# setwd('~/Desktop/')

args = commandArgs(trailingOnly = TRUE)

plate <- args[1]
wells <- args[2:(length(args) - 3)] %>% stringr::str_remove_all(., '[,|\\[|\\]]')
well_site <- args[length(args) - 2]
wavelength <- as.numeric(args[length(args) - 1]) 
output_dir <- args[length(args)]  

#image_dir <- stringr::str_c(getwd(), 'input', plate, sep = '/')
image_dir <- getwd()

input_files <- list.files(path = image_dir, pattern = '.*TIF$', recursive = TRUE) %>% magrittr::extract(dplyr::matches(wells, vars = .))
mask <- 'well_mask.png'

wd <- getwd() %>% str_remove(., '^/')

load_csv <- dplyr::tibble(
  well_site = well_site,
  Group_Number = 1,
  Group_Index = seq(1, length(input_files)),
  URL_RawImage = stringr::str_c('file:', wd, 'input', plate, input_files, sep = '/'),
  URL_WellMask = stringr::str_c('file:', wd, 'wrmXpress', 'cp_pipelines', 'masks', mask, sep = '/'),
  PathName_RawImage = stringr::str_remove(URL_RawImage, pattern = "/[^/]*$") %>% str_remove(., 'file:'),
  PathName_WellMask = stringr::str_remove(URL_WellMask, mask) %>% str_remove(., 'file:') %>%  str_remove(., '/$'),
  FileName_RawImage = input_files,
  FileName_WellMask = mask,
  Series_RawImage = 0,
  Series_WellMask = 0,
  Frame_RawImage = 0,
  Frame_WellMask = 0,
  Channel_RawImage = -1,
  Channel_WellMask = -1,
  Metadata_Date = stringr::str_extract(plate, '202[0-9]{5}'),
  Metadata_FileLocation = URL_RawImage,
  Metadata_Frame = 0,
  Metadata_Plate = stringr::str_extract(plate, '-p[0-9]*-') %>% stringr::str_remove_all(., '-'),
  Metadata_Researcher = stringr::str_extract(plate, '-[A-Z]{2,3}') %>% stringr::str_remove_all(., '-'),
  Metadata_Series = 0,
  Metadata_Well = stringr::str_extract(FileName_RawImage, '[A-H][0,1]{1}[0-9]{1}')
)

#readr::write_csv(load_csv, file = stringr::str_c('/', wd, '/input', '/image_paths_wormsize.csv', sep = ''))

# Generate a unique output CSV for each well_site
output_csv <- file.path(output_dir, paste0("image_paths_", plate, "_", well_site, "_w", wavelength + 1, ".csv"))

# Debug check for output path
print(paste("Writing CSV to:", output_csv))

# Write the CSV to the defined path
readr::write_csv(load_csv, file = output_csv)