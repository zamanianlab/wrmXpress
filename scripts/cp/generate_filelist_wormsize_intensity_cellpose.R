suppressWarnings(suppressMessages(library(tidyverse)))

# setwd('~/Desktop/temp_root/')

args = commandArgs(trailingOnly = TRUE)

plate <- args[1]
wells <- args[2:length(args)] %>% stringr::str_remove_all(., '[,|\\[|\\]]')

# plate <- '20220422-p06-EJG_1437'
# wells <- 'A01'

image_dir <- stringr::str_c(getwd(), 'input', plate, sep = '/')

input_raw <- list.files(path = image_dir, pattern = '.*tif$', recursive = TRUE) %>% magrittr::extract(dplyr::matches(wells, vars = .))
input_mask <- list.files(path = image_dir, pattern = '.*png$', recursive = TRUE) %>% magrittr::extract(dplyr::matches(wells, vars = .))
mask <- 'well_mask.png'

wd <- getwd() %>% str_remove(., '^/')

load_csv <- dplyr::tibble(
  Group_Number = 1,
  Group_Index = seq(1, length(input_raw)),
  URL_RawImage = stringr::str_c('file:', wd, 'input', plate, input_raw, sep = '/'),
  URL_WormMasks = stringr::str_c('file:', wd, 'input', plate, input_mask, sep = '/'),
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
  Metadata_Well = stringr::str_extract(FileName_RawImage, '[A-H][0,1]{1}[0-9]{1}')
)

readr::write_csv(load_csv, file = stringr::str_c('/', wd, '/input', '/image_paths_wormsize_intensity_cellpose.csv', sep = ''))
