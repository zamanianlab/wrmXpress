import os
import shutil
import glob
import subprocess
import shlex
import tempfile
from pathlib import Path
import pandas as pd
from skimage import io

from pipelines.diagnostics import static_dx

def run_cellprofiler_on_image(cellprofiler_pipeline, image_path, output_dir):
    """Run CellProfiler on a single .tif file."""
    # Prepare CellProfiler command for the single image
    cellprofiler_command = (
        f'cellprofiler -c -r '
        f'-p wrmXpress/cp_pipelines/pipelines/{cellprofiler_pipeline}.cppipe '
        f'--data-file {image_path} '
        f'--output-dir {output_dir}'
    )
    
    # Run the CellProfiler command
    cellprofiler_command_split = shlex.split(cellprofiler_command)
    subprocess.run(cellprofiler_command_split)

def cellprofiler(g, wells, well_sites, options):
    # Create output and work directories at the start of the function
    work_dir = Path(g.work) / 'cellprofiler'
    csv_out_dir = Path(g.output) / 'cellprofiler'
    work_dir.mkdir(parents=True, exist_ok=True)
    csv_out_dir.mkdir(parents=True, exist_ok=True)

    cellprofiler_pipeline = options['pipeline']
    wavelengths_option = options['wavelengths']  # This may be 'All' or a string like 'w1,w2'
    timepoints = range(1, 2)  # Process only TimePoint_1 for now

    # Determine which wavelengths to use
    wavelengths_option = ','.join(wavelengths_option)
    if wavelengths_option == 'All':
        wavelengths = range(g.n_waves)  # Use all available wavelengths
    else:
        wavelengths = [int(w[1:]) - 1 for w in wavelengths_option.split(',')]


    for wavelength in wavelengths:  # Iterate directly over wavelengths
        file_list = []  # List to store results ffor list of files
        
        for well_site in well_sites:
            for timepoint in timepoints:
                # Construct the source TIFF file path with or without wavelength
                tiff_file_base = os.path.join(g.input, g.plate, f"TimePoint_{timepoint}", f"{g.plate_short}_{well_site}")
                
                # Check if the wavelength is specified in the filename
                tiff_file = None
                base_tiff_file = f"{tiff_file_base}.TIF"  # Base file without wavelength
                wavelength_tiff_file = f"{tiff_file_base}_w{wavelength + 1}.TIF"  # File with wavelength

                if os.path.exists(wavelength_tiff_file):
                    tiff_file = wavelength_tiff_file
                elif os.path.exists(base_tiff_file):
                    tiff_file = base_tiff_file

                if tiff_file:
                    # Create a temporary directory for this run
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # Copy the image to the temporary directory
                        temp_image_path = Path(temp_dir) / f"{g.plate_short}_{well_site}_w{wavelength + 1}.TIF"
                        shutil.copy(tiff_file, temp_image_path)
                        
                        # Run CellProfiler on the image (one by one)
                        run_cellprofiler_on_image(cellprofiler_pipeline, temp_image_path, temp_dir)
                        
                        # Move results from the temp directory to the final work directory
                        for file in glob.glob(f"{temp_dir}/*.png"): 
                            new_filename = f"{g.plate_short}_{well_site}_w{wavelength + 1}.png"
                            shutil.copy(file, work_dir / new_filename)

