suppressWarnings(suppressMessages(library(stringr)))
suppressWarnings(suppressMessages(library(magrittr)))
suppressWarnings(suppressMessages(library(dplyr)))
suppressWarnings(suppressMessages(library(readr)))
# setwd('~/Desktop/temp_root/')

args = commandArgs(trailingOnly = TRUE)

plate <- args[1]
input <- args[2]
work <- args[3]
wells <- args[4:(length(args) - 3)] %>% stringr::str_remove_all(., '[,|\\[|\\]]')
well_site <- args[length(args) - 3]
wavelength <- as.numeric(args[length(args) - 2]) 
output_dir <- args[length(args) - 1] 
plate_short <- args[length(args)]

# plate <- '20220422-p06-EJG_1437'
# wells <- 'A01'

image_dir <- stringr::str_c(input, plate, sep = '/')
mask_dir <- stringr::str_c(work, 'cellprofiler', sep = '/')


# Construct a pattern that combines wells and wavelength label
wavelength_label <- wavelength + 1
pattern <- paste0(wells, ".*w", wavelength_label, ".*\\.TIF$")

# Filter input files matching the pattern
#input_raw <- list.files(path = image_dir, pattern = '.*TIF$', recursive = TRUE) %>% magrittr::extract(dplyr::matches(wells, vars = .))
input_raw <- list.files(path = image_dir, pattern = pattern, recursive = TRUE)
input_mask <- list.files(path = mask_dir, pattern = '.*png$', recursive = TRUE) %>% magrittr::extract(dplyr::matches(wells, vars = .)) %>% magrittr::extract(dplyr::matches(plate_short, vars = .))
mask <- 'well_mask.png'

wd <- getwd() %>% str_remove(., '^/')

load_csv <- dplyr::tibble(
  # requires well_site column for metadata_join_master.R
  well_site = well_site,
  Group_Number = 1,
  Group_Index = seq(1, length(input_raw)),
  URL_RawImage = stringr::str_c('file:', input, plate, input_raw, sep = '/'),
  URL_WormMasks = stringr::str_c('file:', work, 'cellprofiler', input_mask, sep = '/'),
  PathName_RawImage = stringr::str_remove(URL_RawImage, pattern = "/[^/]*$") %>% str_remove(., 'file:'),
  PathName_WormMasks = stringr::str_remove(URL_WormMasks, pattern = "/[^/]*$") %>% str_remove(., 'file:'),
  FileName_RawImage = input_raw,
  FileName_WormMasks = input_mask,
  Series_RawImage = 0,
  Series_WormMasks = 0,
  Frame_RawImage = 0,
  Frame_WormMasks = 0,
  Channel_RawImage = -1,
  Channel_WormMasks = -1,
  Metadata_Date = stringr::str_extract(plate, '202[0-9]{5}'),
  Metadata_FileLocation = 'nan',
  Metadata_Frame = 0,
  Metadata_Plate = stringr::str_extract(plate, '-p[0-9]*-') %>% stringr::str_remove_all(., '-'),
  Metadata_Researcher = stringr::str_extract(plate, '-[A-Z]{2,3}') %>% stringr::str_remove_all(., '-'),
  Metadata_Series = 0,
  Metadata_Well = stringr::str_extract(FileName_RawImage, '[A-H][0,1]{1}[0-9]{1}'),
  Metadata_Wavelength = stringr::str_extract(FileName_RawImage, '(?<=_w)[0-9]+')
)

#readr::write_csv(load_csv, file = stringr::str_c('/', wd, '/input', '/image_paths_wormsize_intensity_cellpose.csv', sep = ''))
# Generate a unique output CSV for each well_site
output_csv <- file.path(output_dir, paste0("image_paths_", plate_short, "_", well_site, "_w", wavelength + 1, ".csv"))

# Debug check for output path
print(paste("Writing CSV to:", output_csv))

# Write the CSV to the defined path
readr::write_csv(load_csv, file = output_csv)