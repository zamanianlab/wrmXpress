import os
import shutil
import glob
import shlex
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd
from skimage import io, measure
import tempfile

from pipelines.diagnostics import static_dx

def rename_files_temporarily(src_dir, temp_dir):
    """Copy and rename all .TIF files to .tif in a temporary directory."""
    Path(temp_dir).mkdir(parents=True, exist_ok=True)
    for filepath in Path(src_dir).glob('**/*.TIF'):
        new_filepath = Path(temp_dir) / (filepath.stem + '.tif')
        shutil.copy(filepath, new_filepath)

def run_cellpose(g, options):
    model_path = f"wrmXpress/models/cellpose/{options['model']}"
    model_type = options['model_type']

    for timepoint in range(1, 2):  # Adjusted to process only TimePoint 1
        input_dir = os.path.join(g.input, g.plate, f"TimePoint_{timepoint}")

        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Rename TIF to tif in the temporary directory
            rename_files_temporarily(input_dir, temp_dir)

            # Construct Cellpose command
            cellpose_command = (
                f'python -m {model_type} '
                f'--dir {temp_dir} '
                f'--pretrained_model {model_path} '
                f'--diameter 0 --save_png --no_npy --verbose'
            )

            # Run Cellpose command
            cellpose_command_split = shlex.split(cellpose_command)
            subprocess.run(cellpose_command_split)

            # Rename files inside temp_dir to add the wavelength (e.g., '_w1')
            wavelength = '_w1'
            for file in glob.glob(f"{temp_dir}/*.png"):
                filename = os.path.basename(file)
                if 'cp_masks' in filename:
                    # Extract parts of the filename
                    base_name = filename.split('_cp_masks')[0]
                    new_filename = f"{base_name}{wavelength}.png"
                    new_filepath = os.path.join(temp_dir, new_filename)
                    os.rename(file, new_filepath)

            # Move renamed PNG masks to 'work/segmentation' directory
            segmentation_dir = os.path.join(g.work, 'segmentation')
            os.makedirs(segmentation_dir, exist_ok=True)
            for file in glob.glob(f"{temp_dir}/*.png"):
                shutil.copy(file, segmentation_dir)

def segmentation(g, wells, well_sites, options):
    run_cellpose(g, options)

    # Directory where stitched image and CSV files will be saved
    segmentation_dir = Path(g.output) / 'segmentation'
    segmentation_dir.mkdir(parents=True, exist_ok=True)

    # Initialize a dictionary to store results for each wavelength
    wavelength_data = {wavelength: [] for wavelength in range(g.n_waves)}

    for well_site in well_sites:
        for wavelength in range(g.n_waves):
            # Construct the image path for the current well_site and wavelength
            image_path = os.path.join(g.work, 'segmentation', f'{g.plate_short}_{well_site}_w{wavelength + 1}.png')
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

    # Save CSV files for each wavelength
    for wavelength, results in wavelength_data.items():
        df_wavelength = pd.DataFrame(results)
        csv_aggregated_outpath = Path(g.output) / 'segmentation' / f'{g.plate}_w{wavelength + 1}.csv'
        df_wavelength.to_csv(csv_aggregated_outpath, index=False)

    # Run static_dx to make diagnostic image of segmented images
    static_dx(g, wells,
              os.path.join(g.work, 'segmentation'),
              os.path.join(g.output, 'segmentation'),
              None,
              rescale_factor=1,
              format='PNG')
