suppressWarnings(suppressMessages(library(stringr)))
suppressWarnings(suppressMessages(library(magrittr)))
suppressWarnings(suppressMessages(library(dplyr)))
suppressWarnings(suppressMessages(library(readr)))

# setwd('/Users/njwheeler/Desktop/temp_root')

args = commandArgs(trailingOnly = TRUE)

plate <- args[1]  # Plate identifier
# plate <- '20210917-p15-NJW_913'
input <- args[2]  # Input directory
work <- args[3]   # Work directory
wells <- args[4:(length(args) - 3)] %>% stringr::str_remove_all(., '[,|\\[|\\]]')  # Wells
# wells <- c('A01', 'A02')
well_site <- args[length(args) - 3]  # Well site
wavelength <- as.numeric(args[length(args) - 2])  # Wavelength
output_dir <- args[length(args) - 1]  # Output directory
plate_short <- args[length(args)]  # Short plate identifier

# stitched images are in work
image_dir <- stringr::str_c(input, plate, sep = '/')

# Construct a pattern that combines wells and wavelength label
wavelength_label <- wavelength + 1
pattern <- paste0(wells, ".*w", wavelength_label, ".*\\.TIF$")

# Filter input files matching the pattern
input_files <- list.files(path = image_dir, pattern = pattern, recursive = TRUE)

wd <- getwd() %>% str_remove(., '^/')

load_csv <- dplyr::tibble(
  # requires well_site column for metadata_join_master.R
  well_site = well_site,
  Group_Number = 1,
  Group_Index = seq(1, length(input_files)),
  URL_GFP = stringr::str_c('file:', input, plate, input_files, sep = '/'),
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
  Metadata_Well = stringr::str_extract(FileName_GFP, '[A-H][0,1]{1}[0-9]{1}'),
  Metadata_Wavelength = stringr::str_extract(FileName_GFP, '(?<=_w)[0-9]+')
)

# Generate a unique output CSV for each well_site
output_csv <- file.path(output_dir, paste0("image_paths_", plate_short, "_", well_site, "_w", wavelength + 1, ".csv"))

# Debug check for output path
print(paste("Writing CSV to:", output_csv))

# Write the CSV to the defined path
readr::write_csv(load_csv, file = output_csv)
