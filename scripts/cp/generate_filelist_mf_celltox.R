suppressWarnings(suppressMessages(library(tidyverse)))

# setwd('/Users/njwheeler/Desktop/temp_root')

args = commandArgs(trailingOnly = TRUE)

plate <- args[1]
# plate <- '20210917-p15-NJW_913'
wells <- args[2:length(args)] %>% stringr::str_remove_all(., '[,|\\[|\\]]')
# wells <- c('A01', 'A02')

# stitched images are in work
image_dir <- stringr::str_c(getwd(), 'work', plate, sep = '/')

input_files <- list.files(path = image_dir, pattern = '.*tif$', recursive = TRUE) %>% magrittr::extract(dplyr::matches(wells, vars = .))

wd <- getwd() %>% str_remove(., '^/')

load_csv <- dplyr::tibble(
  Group_Number = 1,
  Group_Index = seq(1, length(input_files)),
  URL_GFP = stringr::str_c('file:', wd, 'work', plate, input_files, sep = '/'),
  PathName_GFP = stringr::str_remove(input_files, 'file:'),
  FileName_GFP = input_files,
  Series_GFP = 0,
  Frame_GFP = 0,
  Channel_GFP = -1,
  Metadata_Date = stringr::str_extract(plate, '202[0-9]{5}'),
  Metadata_FileLocation = stringr::str_c(URL_GFP),
  Metadata_Frame = 0,
  Metadata_Plate = stringr::str_extract(plate, '-p[0-9]*-') %>% stringr::str_remove_all(., '-'),
  Metadata_Researcher = stringr::str_extract(plate, '-[A-Z]{2,3}') %>% stringr::str_remove_all(., '-'),
  Metadata_Series = 0,
  Metadata_Site = stringr::str_extract(plate, '_s[0-9]_') %>% stringr::str_remove_all(., 'Z'),
  Metadata_Well = stringr::str_extract(FileName_GFP, '[A-H][0,1]{1}[0-9]{1}')
)

readr::write_csv(load_csv, file = stringr::str_c('/', wd, '/input', '/image_paths_mf_celltox.csv', sep = ''))
