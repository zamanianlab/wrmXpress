import glob
import os
import shutil
import shlex
import subprocess
import tempfile
from pathlib import Path

from config import get_program_dir
PROGRAM_DIR = get_program_dir()

###############################################
######### CELLPROFILER MAIN FUNCTION  #########
###############################################

# This is the main function that coordinates CellProfiler runs.  
# It prepares the directories, identifies the correct image files, runs CellPose segmentation (for certain models),  
# generates the required CSV file via R, and finally runs CellProfiler to analyze the segmented images.
def cellprofiler(g, options, well_site):
    # Create output and CSV directories at the very start of the function
    work_dir = Path(g.work) / "cellprofiler"
    img_out_dir = Path(g.output) / "cellprofiler" / "img"
    work_dir.mkdir(parents=True, exist_ok=True)
    img_out_dir.mkdir(parents=True, exist_ok=True)

    model_path = PROGRAM_DIR / "pipelines" / "models" / "cellpose" / options['cellpose_model'] if options['cellpose_model'] else None
    wavelength_option = options["cellpose_wavelength"]  # A single wavelength like 'w1'
    wavelength = int(wavelength_option[1:]) - 1  # Convert 'w1' to zero-based index
    timepoints = range(1, 2)  # Process only TimePoint_1 for now

    if options['cellpose_model'] != None:
        for timepoint in timepoints:
             # Construct the source TIF file path (it may or may not have wavelength suffix)
            tiff_file_base = os.path.join(g.input, g.plate, f"TimePoint_{timepoint}", f"{g.plate_short}_{well_site}")
            tiff_file = next((f for f in (f"{tiff_file_base}_w{wavelength + 1}.TIF", f"{tiff_file_base}.TIF") if os.path.exists(f)), None)

            if tiff_file is None:
                print(f"No TIF file found for well site {well_site} for timepoint {timepoint}. Skipping to next timepoint.")
                continue                                         

            # CellPose requires images to be in a directory for processing.
            # A temporary directory is chosen as it is automatically cleaned up after use
            with tempfile.TemporaryDirectory() as temp_dir:
                
                # Rename the TIF file to .tif as Cellpose also requires images to be in .tif format.
                rename_file_to_tif(tiff_file, temp_dir)

                # Run CellPose to segment the images for the current timepoint and wavelength
                run_cellpose(model_path, temp_dir)

                # Rename and move the resulting PNG mask to the 'work/cellprofiler' directory
                for file in glob.glob(f"{temp_dir}/*.png"):
                    if "cp_masks" in file:
                            new_filename = (f"{g.plate_short}_{well_site}_w{wavelength + 1}.png")
                            shutil.copy(file, work_dir / new_filename)

    # Generate the CSV file using the R script
    run_rscript_to_generate_csv(
        options["pipeline"],
        g.plate,
        g.input,
        g.work,
        well_site,
        wavelength,
        work_dir,
        g.plate_short,
    )

    # Run CellProfiler and save the output images to the output/cellprofiler/img directory
    csv_file = (
        work_dir / f"image_paths_{g.plate_short}_{well_site}_w{wavelength + 1}.csv"
    )
    if csv_file.exists():
        run_cellprofiler(options["pipeline"], csv_file, img_out_dir)
    else:
        print(f"CSV file not found: {csv_file}")

    return [wavelength]


##################################################
######### CELLPROFILER HELPER FUNCTIONS  #########
##################################################

# This function renames a .TIF file as .tif.  
# This is necessary because CellPose requires images to be in a directory and in .tif format for processing.
def rename_file_to_tif(src_file, temp_dir):
    temp_file = Path(temp_dir) / (Path(src_file).stem + ".tif")
    shutil.copy(src_file, temp_file)
    return temp_file

# This function runs the CellPose segmentation model on .tif images in a given directory.  
def run_cellpose(model_path, temp_dir):
    cellpose_command = (
        f"python -m cellpose "
        f"--dir {temp_dir} "
        f"--pretrained_model {model_path} "
        f"--diameter 0 --save_png --no_npy --verbose"
    )
    cellpose_command_split = shlex.split(cellpose_command)
    subprocess.run(cellpose_command_split)

# This function runs an R script to generate a CSV file listing image paths.  
# The CSV is required by CellProfiler to know which images to analyze and where to find them.
def run_rscript_to_generate_csv(
    cellprofiler_pipeline,
    plate,
    input,
    work,
    well_site,
    wavelength,
    csv_out_dir,
    plate_short,
):
    r_script_path = PROGRAM_DIR / "Rscripts" / "cellprofiler" / f"generate_filelist_{cellprofiler_pipeline}.R"
    r_command = f"Rscript {r_script_path} {plate} {input} {work} {well_site} {wavelength} {csv_out_dir} {plate_short}"
    print(f"Generating file list for {cellprofiler_pipeline}.")
    subprocess.run(shlex.split(r_command))
    

# This function executes the CellProfiler pipeline using the generated CSV file.  
# It processes images according to the specified pipeline and saves the results to the output directory.
def run_cellprofiler(cellprofiler_pipeline, csv_file, img_out_dir):
    pipeline_path = PROGRAM_DIR / "pipelines" / "cellprofiler" / f"{cellprofiler_pipeline}.cppipe"
    cp_command = f"cellprofiler -c -r -p {pipeline_path} --data-file={csv_file} --output-dir={img_out_dir}"
    print(f"Running CellProfiler using {csv_file.name}.")
    subprocess.run(shlex.split(cp_command))
