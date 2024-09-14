import os
import shutil
import glob
import subprocess
import shlex
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
from skimage import io, measure

from pipelines.diagnostics import static_dx

def rename_file_to_temp_tif(src_file, temp_dir):
    """Rename a single TIFF file to .tif in a temporary directory."""
    temp_file = Path(temp_dir) / (Path(src_file).stem + '.tif')
    shutil.copy(src_file, temp_file)
    return temp_file

def run_cellpose(model_type, model_path, temp_dir):
    """Run Cellpose on a single .tif file."""
    cellpose_command = (
        f'python -m {model_type} '
        f'--dir {temp_dir} '
        f'--pretrained_model {model_path} '
        f'--diameter 0 --save_png --no_npy --verbose'
    )

    # Run the Cellpose command
    cellpose_command_split = shlex.split(cellpose_command)
    subprocess.run(cellpose_command_split)

def segmentation(g, wells, well_sites, options):
    # Create output and CSV directories at the very start of the function
    work_dir = Path(g.work) / 'segmentation'
    csv_out_dir = Path(g.output) / 'segmentation'
    work_dir.mkdir(parents=True, exist_ok=True)
    csv_out_dir.mkdir(parents=True, exist_ok=True)

    model_path = f"wrmXpress/models/cellpose/{options['model']}"
    model_type = options['model_type']
    wavelengths_option = options['wavelengths']  # This may be 'All' or a string like 'w1,w2'
    timepoints = range(1, 2)  # Process only TimePoint_1 for now

    # Determine which wavelengths to use
    wavelengths_option = ','.join(wavelengths_option)
    if wavelengths_option == 'All':
        wavelengths = range(g.n_waves)  # Use all available wavelengths
    else:
        wavelengths = [int(w[1:]) - 1 for w in wavelengths_option.split(',')]

    # Initialize a dictionary to store results for each wavelength
    wavelength_data = {wavelength: [] for wavelength in wavelengths}

    for well_site in well_sites:
        for wavelength in wavelengths:  # Iterate directly over wavelengths
            for timepoint in timepoints:
                # Create a temporary directory
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Construct the source TIFF file path
                    tiff_file_base = os.path.join(g.input, g.plate, f"TimePoint_{timepoint}", f"{g.plate_short}_{well_site}")

                    # Check if the wavelength is specified in the filename
                    tiff_file = None
                    base_tiff_file = f"{tiff_file_base}.TIF"
                    wavelength_tiff_file = f"{tiff_file_base}_w{wavelength + 1}.TIF"

                    if os.path.exists(wavelength_tiff_file):
                        tiff_file = wavelength_tiff_file
                    elif os.path.exists(base_tiff_file):
                        tiff_file = base_tiff_file

                    if tiff_file:
                        # Rename the TIFF file to .tif and copy it to the temporary directory
                        temp_tif_file = rename_file_to_temp_tif(tiff_file, temp_dir)

                        run_cellpose(model_type, model_path, temp_dir)

                        # Rename and move the resulting PNG mask to the 'work/segmentation' directory
                        for file in glob.glob(f"{temp_dir}/*.png"):
                            if 'cp_masks' in file:
                                new_filename = f"{g.plate_short}_{well_site}_w{wavelength + 1}.png"
                                shutil.copy(file, work_dir / new_filename)

                        # Clean up the temporary TIFF file after Cellpose has run
                        os.remove(temp_tif_file)

                # Process the resulting image and calculate segmentation metrics
                image_path = work_dir / f'{g.plate_short}_{well_site}_w{wavelength + 1}.png'
                if os.path.exists(image_path):
                    image = io.imread(image_path)

                    # Calculate metrics for the current well_site and wavelength
                    total_segmented_pixels = np.sum(image > 0)
                    num_objects = len(np.unique(image)) - 1  # exclude background
                    average_size = total_segmented_pixels / num_objects if num_objects > 0 else 0

                    # Calculate compactness for each object
                    compactness_list = [
                        (region.perimeter ** 2) / (4 * np.pi * region.area)
                        for region in measure.regionprops(image)
                    ]
                    average_compactness = np.mean(compactness_list) if compactness_list else 0

                    # Append results for the current well_site and wavelength
                    wavelength_data[wavelength].append({
                        'well_site': well_site,
                        'total_segmented_pixels': total_segmented_pixels,
                        'num_objects': num_objects,
                        'average_size': average_size,
                        'average_compactness': average_compactness
                    })

    # Create pandas DataFrame and write to CSV
    for wavelength, results in wavelength_data.items():
        df_wavelength = pd.DataFrame(results)
        csv_outpath = csv_out_dir / f'{g.plate}_w{wavelength + 1}.csv'
        df_wavelength.to_csv(csv_outpath, index=False)

    # Run static_dx to make diagnostic image of segmented images
    static_dx(g, wells,
              work_dir,
              csv_out_dir,
              None,
              rescale_factor=1,
              format='PNG')
