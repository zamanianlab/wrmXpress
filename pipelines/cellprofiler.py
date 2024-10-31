import os
import shutil
import glob
import subprocess
import shlex
import tempfile
from pathlib import Path

def run_rscript_to_generate_csv(cellprofiler_pipeline, temp_dir, plate, wells, well_site, wavelength, csv_out_dir):
    """Run the R script to generate the CSV file listing the image paths and save csvs to work/cellprofiler."""
    fl_command = f'Rscript {Path.home()}/wrmXpress/scripts/cellprofiler/generate_filelist_{cellprofiler_pipeline}.R {plate} {wells} {well_site} {wavelength} {csv_out_dir}'
    fl_command_split = shlex.split(fl_command)
    print(f'Generating file list for CellProfiler.')
    subprocess.run(fl_command_split, cwd=temp_dir)

def run_cellprofiler_with_csv(cellprofiler_pipeline, csv_file, img_out_dir):
    """Run CellProfiler using the generated CSV file and save output images to output/cellprofiler/img."""
    cellprofiler_command = f'cellprofiler -c -r -p {Path.home()}/wrmXpress/pipelines/cellprofiler/{cellprofiler_pipeline}.cppipe --data-file={csv_file} --output-dir={img_out_dir}'
    cellprofiler_command_split = shlex.split(cellprofiler_command)
    print('Starting CellProfiler.')
    subprocess.run(cellprofiler_command_split)

def cellprofiler(g, wells, well_sites, options):
    # Create output and work directories at the start of the function
    work_dir = Path(g.work) / 'cellprofiler'
    csv_out_dir = work_dir
    img_out_dir = Path(g.output) / 'cellprofiler' / 'img'
    work_dir.mkdir(parents=True, exist_ok=True)
    img_out_dir.mkdir(parents=True, exist_ok=True)
    

    cellprofiler_pipeline = options['pipeline']
    wavelengths_option = options['wavelengths']  # This may be 'All' or a string like 'w1,w2'
    timepoints = range(1, 2)  # Process only TimePoint_1 for now

    # Determine which wavelengths to use
    wavelengths_option = ','.join(wavelengths_option)
    if wavelengths_option == 'All':
        wavelengths = [i for i in range(g.n_waves)]  # Use all available wavelengths
    else:
        wavelengths = [int(w[1:]) - 1 for w in wavelengths_option.split(',')]

    for wavelength in wavelengths:  
        for well_site in well_sites:
            for timepoint in timepoints:
                # Create a temporary directory for this run
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Construct a file pattern to match the specific wavelength, if it's in the filename
                    base_tiff_file_pattern_with_wavelength = os.path.join(
                        g.input, g.plate, f"TimePoint_{timepoint}", 
                        f"{g.plate_short}_{well_site}_w{wavelength + 1}.TIF"  # Matches filenames with the wavelength
                    )
                    
                    # Construct a pattern to match files without wavelength, just in case
                    base_tiff_file_pattern_no_wavelength = os.path.join(
                        g.input, g.plate, f"TimePoint_{timepoint}", 
                        f"{g.plate_short}_{well_site}*.TIF"  # Matches filenames without wavelength
                    )
                    
                    # First, try to find files matching the specific wavelength
                    matching_images = glob.glob(base_tiff_file_pattern_with_wavelength)
                    
                    # If no files with wavelength are found, fall back to the pattern without wavelength
                    if not matching_images:
                        matching_images = glob.glob(base_tiff_file_pattern_no_wavelength)

                    # Copy all matching images to the temporary directory
                    for img in matching_images:
                        # Get the filename
                        temp_image_name = os.path.basename(img)  
                        # Path in temp directory
                        temp_image_path = Path(temp_dir) / temp_image_name  
                        # Copy image
                        shutil.copy(img, temp_image_path)

                    # Generate the CSV file inside the temporary directory and move to work/cellprofiler
                    run_rscript_to_generate_csv(cellprofiler_pipeline, temp_dir, g.plate, g.wells, well_site, wavelength, csv_out_dir)

                    # Use the CSV file to run CellProfiler and output images to output/cellprofiler/img
                    csv_file = csv_out_dir / f'image_paths_{g.plate}_{well_site}_w{wavelength + 1}.csv'
                    run_cellprofiler_with_csv(cellprofiler_pipeline, csv_file, img_out_dir)

                    # Copy the generated CSV files to the output/cellprofiler directory so as to run metadata script
                    for csv_file in work_dir.glob("*.csv"):
                        shutil.copy(csv_file, Path(g.output) / 'cellprofiler' / csv_file.name)
