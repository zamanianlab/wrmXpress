suppressWarnings(suppressMessages(library(stringr)))
suppressWarnings(suppressMessages(library(magrittr)))
suppressWarnings(suppressMessages(library(dplyr)))
suppressWarnings(suppressMessages(library(readr)))

# setwd('/Users/njwheeler/Desktop/')

args = commandArgs(trailingOnly = TRUE)

plate <- args[1]
input <- args[2]
work <- args[3]
wells <- args[4:(length(args) - 3)] %>% stringr::str_remove_all(., '[,|\\[|\\]]')
well_site <- args[length(args) - 3]
wavelength <- as.numeric(args[length(args) - 2]) 
output_dir <- args[length(args) - 1] 
plate_short <- args[length(args)]

image_dir <- stringr::str_c(input, plate, sep = '/')

input_files <- list.files(path = image_dir, pattern = '.*TIF$', recursive = TRUE) %>% magrittr::extract(dplyr::matches(wells, vars = .))
tl <- input_files %>% magrittr::extract(dplyr::matches("w1", vars = .))
gfp <- input_files %>% magrittr::extract(dplyr::matches("w2", vars = .))
txrd <- input_files %>% magrittr::extract(dplyr::matches("w3", vars = .))
mask <- 'well_mask.png'

wd <- getwd() %>% str_remove(., '^/')

load_csv <- dplyr::tibble(
  Group_Number = 1,
  Group_Index = seq(1, length(tl)),
  URL_GFP = stringr::str_c('file:', input, plate, gfp, sep = '/'),
  URL_TransmittedLight = stringr::str_c('file:', input, plate, tl, sep = '/'),
  URL_TxRed = stringr::str_c('file:', input, plate, txrd, sep = '/'),
  URL_wellmask = stringr::str_c('file:', 'root', 'wrmXpress', 'pipelines', 'cellprofiler', 'masks', mask, sep = '/'),
  PathName_GFP = stringr::str_remove(URL_GFP, 'file:'),
  PathName_TransmittedLight = stringr::str_remove(URL_TransmittedLight, 'file:'),
  PathName_TxRed = stringr::str_remove(URL_TxRed, 'file:'),
  PathName_wellmask = stringr::str_remove(URL_wellmask, 'file:'),
  FileName_GFP = gfp,
  FileName_TransmittedLight = tl,
  FileName_TxRed = txrd,
  FileName_wellmask = mask,
  Series_GFP = 0,
  Series_TransmittedLight = 0,
  Series_TxRed = 0,
  Series_wellmask = 0,
  Frame_GFP = 0,
  Frame_TransmittedLight = 0,
  Frame_TxRed = 0,
  Frame_wellmask = 0,
  Channel_GFP = -1,
  Channel_TransmittedLight = -1,
  Channel_TxRed = -1,
  Channel_wellmask = -1,
  Metadata_Date = stringr::str_extract(plate, '202[0-9]{5}'),
  Metadata_FileLocation = 'nan',
  Metadata_Frame = 0,
  Metadata_Plate = stringr::str_extract(plate, '-p[0-9]*-') %>% stringr::str_remove_all(., '-'),
  Metadata_Researcher = stringr::str_extract(plate, '-[A-Z]{2,3}') %>% stringr::str_remove_all(., '-'),
  Metadata_Series = 0,
  Metadata_Site = stringr::str_extract(plate, '_s[0-9]_') %>% stringr::str_remove_all(., 'Z'),
  Metadata_Wavelength = 'nan',
  Metadata_Well = stringr::str_extract(FileName_TransmittedLight, '[A-P]([0-1][0-9]|2[0-4])')
)

# Generate a unique output CSV for each well_site
output_csv <- file.path(output_dir, paste0("image_paths_", plate_short, "_", well_site, "_w", wavelength + 1, ".csv"))

# Debug check for output path
print(paste("Writing CSV to:", output_csv))

# Write the CSV to the defined path
readr::write_csv(load_csv, file = output_csv)
