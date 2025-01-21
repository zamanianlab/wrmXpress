import os
import shutil
import glob
import subprocess
import shlex
import tempfile
from pathlib import Path


def rename_file_to_temp_tif(src_file, temp_dir):
    """Rename a single TIF file to tif in a temporary directory."""
    temp_file = Path(temp_dir) / (Path(src_file).stem + ".tif")
    shutil.copy(src_file, temp_file)
    return temp_file


def run_cellpose(model_path, temp_dir):
    """Run CellPose on a single .tif file."""
    cellpose_command = (
        f"python -m cellpose "
        f"--dir {temp_dir} "
        f"--pretrained_model {model_path} "
        f"--diameter 0 --save_png --no_npy --verbose"
    )
    cellpose_command_split = shlex.split(cellpose_command)
    subprocess.run(cellpose_command_split)


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
    """Run the R script to generate the CSV file listing the image paths and save csvs to work/cellprofiler."""
    r_command = f"Rscript /root/wrmXpress/Rscripts/cellprofiler/generate_filelist_{cellprofiler_pipeline}.R {plate} {input} {work} {well_site} {wavelength} {csv_out_dir} {plate_short}"
    print(f"Generating file list for {cellprofiler_pipeline}.")
    subprocess.run(shlex.split(r_command))
    


def run_cellprofiler(cellprofiler_pipeline, csv_file, img_out_dir):
    """Run CellProfiler using the generated CSV file and save output images to output/cellprofiler/img."""
    cp_command = f"cellprofiler -c -r -p /root/wrmXpress/pipelines/cellprofiler/{cellprofiler_pipeline}.cppipe --data-file={csv_file} --output-dir={img_out_dir}"
    print(f"Running CellProfiler using {csv_file.name}.")
    subprocess.run(shlex.split(cp_command))
    


def cellprofiler(g, options, well_site):
    # Create output and CSV directories at the very start of the function
    work_dir = Path(g.work) / "cellprofiler"
    img_out_dir = Path(g.output) / "cellprofiler" / "img"
    work_dir.mkdir(parents=True, exist_ok=True)
    img_out_dir.mkdir(parents=True, exist_ok=True)

    model_path = f"/root/wrmXpress/pipelines/models/cellpose/{options['cellpose_model']}"
    wavelength_option = options["cellpose_wavelength"]  # A single wavelength like 'w1'
    wavelength = int(wavelength_option[1:]) - 1  # Convert 'w1' to 0-based index
    timepoints = range(1, 2)  # Process only TimePoint_1 for now

    # Only proceed with the timepoints loop if cellpose_model is not empty
    if options['cellpose_model'] != None:
        # Iterate over the timepoints for CellPose processing
        for timepoint in timepoints:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Construct the source TIFF file path
                tiff_file_base = os.path.join(
                    g.input,
                    g.plate,
                    f"TimePoint_{timepoint}",
                    f"{g.plate_short}_{well_site}",
                )

                # Check if the wavelength is specified in the filename
                tiff_file = None
                base_tiff_file = f"{tiff_file_base}.TIF"
                wavelength_tiff_file = f"{tiff_file_base}_w{wavelength + 1}.TIF"

                if os.path.exists(wavelength_tiff_file):
                    tiff_file = wavelength_tiff_file
                elif os.path.exists(base_tiff_file):
                    tiff_file = base_tiff_file

                if tiff_file:
                    # Rename the TIF file to .tif and copy it to the temporary directory
                    rename_file_to_temp_tif(tiff_file, temp_dir)

                    # Step 1: Run CellPose to segment the images for the current timepoint and wavelength
                    run_cellpose(model_path, temp_dir)

                    # Rename and move the resulting PNG mask to the 'work/cellprofiler' directory
                    for file in glob.glob(f"{temp_dir}/*.png"):
                        if "cp_masks" in file:
                            new_filename = (
                                f"{g.plate_short}_{well_site}_w{wavelength + 1}.png"
                            )
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
