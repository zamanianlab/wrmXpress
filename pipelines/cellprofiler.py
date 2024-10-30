import os
import shutil
import glob
import subprocess
import shlex
import tempfile
from pathlib import Path

def run_rscript_to_generate_csv(cellprofiler_pipeline, temp_dir, plate, wells, csv_out_dir, well_site):
    """Run the R script to generate the CSV file listing the image paths and save csvs to work/cellprofiler."""
    fl_command = f'Rscript wrmXpress/scripts/cp/generate_filelist_{cellprofiler_pipeline}.R {plate} {wells}'
    fl_command_split = shlex.split(fl_command)
    print(f'Generating file list for CellProfiler.')
    subprocess.run(fl_command_split, cwd=temp_dir)

    generated_csv_name = f'image_paths_{cellprofiler_pipeline}_{well_site}.csv'
    generated_csv = Path(temp_dir) / generated_csv_name
    if generated_csv.exists():
        shutil.copy(generated_csv, csv_out_dir / generated_csv_name)

def run_cellprofiler_with_csv(cellprofiler_pipeline, csv_file, output_img_dir):
    """Run CellProfiler using the generated CSV file and save output images to output/cellprofiler/img."""
    cellprofiler_command = f'cellprofiler -c -r -p wrmXpress/cp_pipelines/pipelines/{cellprofiler_pipeline}.cppipe --data-file={csv_file} --output-dir={output_img_dir}'
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
        wavelengths = range(g.n_waves)  # Use all available wavelengths
    else:
        wavelengths = [int(w[1:]) - 1 for w in wavelengths_option.split(',')]

    for wavelength in wavelengths:  # Iterate directly over wavelengths
        for well_site in well_sites:
            for timepoint in timepoints:
                # Create a temporary directory for this run
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Construct the source TIFF file pattern to match both with and without wavelength
                    base_tiff_file_pattern = os.path.join(
                        g.input, g.plate, f"TimePoint_{timepoint}", 
                        f"{g.plate_short}_{well_site}*_w{wavelength + 1}.TIF"  # Matches filenames with wavelength
                    )
                    
                    # Also add a pattern for files without wavelength
                    base_tiff_file_pattern_no_wavelength = os.path.join(
                        g.input, g.plate, f"TimePoint_{timepoint}", 
                        f"{g.plate_short}_{well_site}*.TIF"  # Matches filenames without wavelength
                    )
                    
                    # Use glob to find all matching TIFF files for both patterns
                    matching_images = glob.glob(base_tiff_file_pattern) + glob.glob(base_tiff_file_pattern_no_wavelength)


                    # Copy all matching images to the temporary directory
                    for img in matching_images:
                        # Get the filename
                        temp_image_name = os.path.basename(img)  
                        # Path in temp directory
                        temp_image_path = Path(temp_dir) / temp_image_name  
                        # Copy image
                        shutil.copy(img, temp_image_path)

                    # Generate the CSV file inside the temporary directory and move to work/cellprofiler
                    run_rscript_to_generate_csv(cellprofiler_pipeline, temp_dir, g.plate, g.wells, csv_out_dir, well_site)

                    # Use the CSV file to run CellProfiler and output images to output/cellprofiler/img
                    csv_file = csv_out_dir / f'image_paths_{cellprofiler_pipeline}_{well_site}.csv'
                    run_cellprofiler_with_csv(cellprofiler_pipeline, csv_file, img_out_dir)

                    # Copy the generated CSV files to the output/cellprofiler directory so as to run metadata script
                    for csv_file in work_dir.glob("*.csv"):
                        shutil.copy(csv_file, Path(g.output) / 'cellprofiler' / csv_file.name)
