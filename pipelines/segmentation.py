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

def rename_file_to_temp_tif(src_file, temp_dir):
    """Rename a single TIF file to tif in a temporary directory."""
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

def segmentation(g, options, well_site):
    # Create output and CSV directories at the very start of the function
    work_dir = Path(g.work) / 'segmentation'
    csv_out_dir = Path(g.output) / 'segmentation'
    work_dir.mkdir(parents=True, exist_ok=True)
    csv_out_dir.mkdir(parents=True, exist_ok=True)

    model_path = f"wrmXpress/pipelines/models/cellpose/{options['model']}"
    model_type = options['model_type']
    wavelengths_option = options['wavelengths']  # This may be 'All' or a string like 'w1,w2'
    timepoints = range(1, 2)  # Process only TimePoint_1 for now

    # Determine which wavelengths to use
    wavelengths_option = ','.join(wavelengths_option)
    if wavelengths_option == 'All':
        wavelengths = [i for i in range(g.n_waves)]  # Use all available wavelengths
    else:
        wavelengths = [int(w[1:]) - 1 for w in wavelengths_option.split(',')]

    for wavelength in wavelengths:  # Iterate directly over wavelengths
        all_results = []

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
                    rename_file_to_temp_tif(tiff_file, temp_dir)

                    run_cellpose(model_type, model_path, temp_dir)

                    # Rename and move the resulting PNG mask to the 'work/segmentation' directory
                    for file in glob.glob(f"{temp_dir}/*.png"):
                        if 'cp_masks' in file:
                            new_filename = f"{g.plate_short}_{well_site}_w{wavelength + 1}.png"
                            shutil.copy(file, work_dir / new_filename)

            # Process the resulting image and calculate segmentation metrics
            image_path = work_dir / f'{g.plate_short}_{well_site}_w{wavelength + 1}.png'
            if os.path.exists(image_path):
                image = io.imread(image_path)

                # Calculate metrics for the current wavelength
                total_segmented_pixels = np.sum(image > 0)
                num_objects = len(np.unique(image)) - 1  # exclude background
                average_size = total_segmented_pixels / num_objects if num_objects > 0 else 0

                # Calculate compactness for each object
                compactness_list = [
                    (region.perimeter ** 2) / (4 * np.pi * region.area)
                    for region in measure.regionprops(image)
                ]
                average_compactness = np.mean(compactness_list) if compactness_list else 0

                # Prepare results for the current wavelength
                result = {
                    'well_site': well_site,
                    'total_segmented_pixels': total_segmented_pixels,
                    'num_objects': num_objects,
                    'average_size': average_size,
                    'average_compactness': average_compactness
                }

                all_results.append(result)  # Append the result dictionary to the list

        # Create a DataFrame for the results of the current wavelength
        df = pd.DataFrame(all_results)

        # Write the DataFrame to CSV for the current wavelength
        csv_outpath = csv_out_dir / f'{g.plate}_{well_site}_w{wavelength + 1}.csv'
        df.to_csv(csv_outpath, index=False)

    return wavelengths