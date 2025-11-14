from collections import defaultdict
import os
import shutil
import glob
import subprocess
import shlex
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import cv2
from skimage import io, filters, measure
from scipy import ndimage

from config import get_program_dir
PROGRAM_DIR = get_program_dir()


###############################################
######### SEGMENTATION MAIN FUNCTION  #########
###############################################

# Main segmentation function that performs image segmentation using either a Python-based method or Cellpose.
# It handles all wavelengths, applies circular masks, thresholds, blurs, edge detection, and saves results as CSV and images.
def segmentation(g, options, well_site):
    """Perform segmentation based on model type."""
    work_dir = Path(g.work) / 'segmentation'
    output_dir = Path(g.output) / 'segmentation'
    work_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    model_type = options['model_type']
    model_sigma = options['model_sigma']
    wavelengths_option = options['wavelengths']
    timepoints = range(1, 2)  # Process only TimePoint_1

    # Determine which wavelengths to use
    wavelengths_option = ','.join(wavelengths_option)
    wavelengths = [int(w[1:]) - 1 for w in wavelengths_option.split(',')] if wavelengths_option != 'All' else list(range(g.n_waves))

    for wavelength in wavelengths:
        all_results = []

        for timepoint in timepoints:
            # Construct the source TIF file path (it may or may not have wavelength suffix)
            tiff_file_base = os.path.join(g.input, g.plate, f"TimePoint_{timepoint}", f"{g.plate_short}_{well_site}")
            tiff_file = next((f for f in (f"{tiff_file_base}_w{wavelength + 1}.TIF", f"{tiff_file_base}.TIF") if os.path.exists(f)), None)

            if tiff_file is None:
                print(f"No TIF file found for well site {well_site} for timepoint {timepoint}. Skipping to next timepoint.")
                continue 

            if model_type == 'python': # Runs if model_type is Python
                out_dict = defaultdict(list)
                cols = []

                image = cv2.imread(str(tiff_file), cv2.IMREAD_ANYDEPTH)

                height, width = image.shape
                mask = create_circular_mask(height, width, radius=height / 2.2)

                # gaussian blur
                blur = ndimage.filters.gaussian_filter(image, model_sigma)

                # edges
                sobel = filters.sobel(blur)

                # set threshold, make binary, fill holes
                threshold = filters.threshold_otsu(sobel)
                binary = sobel > threshold
                binary = binary * mask

                # Run segmentation based on model selection (segment_sma or segment_mf)
                segmented_area  = segment_sma(g, well_site, binary) if options['model'] == 'segment_sma' else segment_mf(binary)

                bin_png = g.work.joinpath(work_dir, f"{g.plate_short}_{well_site}_w{wavelength+1}.png")
                cv2.imwrite(str(bin_png), binary * 255)
                    
                print(f"Segmented area is {segmented_area}")

                # Save segmentation results to CSV
                if 'segmented_area' not in cols:
                    cols.append('segmented_area')
                        
                out_dict[well_site].append(segmented_area)
                df = pd.DataFrame.from_dict(out_dict, orient='index', columns=cols)
                outpath = work_dir.joinpath(f"{g.plate_short}_{well_site}_w{wavelength+1}.csv")
                df.to_csv(path_or_buf=outpath, index_label='well_site')
            
            # elif model_type = 'yolo':

            else: # Runs if model_type is Cellpose
                model_path = PROGRAM_DIR / "pipelines" / "models" / "cellpose" / options['model']
                
                # CellPose requires images to be in a directory for processing.
                # A temporary directory is chosen as it is automatically cleaned up after use
                with tempfile.TemporaryDirectory() as temp_dir:

                    # Rename the TIF file to .tif as Cellpose also requires images to be in .tif format.
                    rename_file_to_tif(tiff_file, temp_dir)

                    # Run CellPose to segment the images for the current timepoint and wavelength
                    run_cellpose(model_type, model_path, temp_dir)

                    # Rename and move the resulting PNG mask to the 'work/cellprofiler' directory
                    for file in glob.glob(f"{temp_dir}/*.png"):
                        if 'cp_masks' in file:
                            new_filename = f"{g.plate_short}_{well_site}_w{wavelength + 1}.png"
                            shutil.copy(file, work_dir / new_filename)

                # Process segmentation metrics
                image_path = work_dir / f'{g.plate_short}_{well_site}_w{wavelength + 1}.png'
                if os.path.exists(image_path):
                    image = io.imread(image_path)
                    labeled_image = measure.label(image)
                    for object_id, region in enumerate(measure.regionprops(labeled_image), start=1):
                        result = {
                            'well_site': well_site,
                            'object_number': object_id,
                            'size': region.area,
                            'compactness': (region.perimeter ** 2) / (4 * np.pi * region.area) if region.area > 0 else 0
                        }
                        all_results.append(result)
                else:
                    result = {
                        'well_site': well_site,
                        'object_number': "NA",
                        'size': "NA",
                        'compactness': "NA"
                    }
                    all_results.append(result)

                # Save results to CSV
                df = pd.DataFrame(all_results)
                csv_outpath = work_dir / f'{g.plate_short}_{well_site}_w{wavelength + 1}.csv'
                df.to_csv(csv_outpath, index=False)

    return wavelengths


##################################################
######### SEGMENTATION HELPER FUNCTIONS  #########
##################################################

# Create a circular mask for an image of height h and width w. Useful for restricting analysis to a circular region.
def create_circular_mask(h, w, center=None, radius=None):
    if center is None:
        center = (int(w / 2), int(h / 2))
    if radius is None:
        radius = min(center[0], center[1], w - center[0], h - center[1])

    Y, X = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((X - center[0])**2 + (Y - center[1])**2)
    mask = dist_from_center <= radius
    return mask


# Originally developed to segment S. mansoni from a binary image, remove small debris, and save intermediate images.
def segment_sma(g, well_site, binary):
    filled = ndimage.binary_fill_holes(binary)

    # Remove small segmented debris
    nb_components, labelled_image, stats, centroids = cv2.connectedComponentsWithStats(
        filled.astype('uint8'), connectivity=8)
    sizes = stats[1:, -1]
    nb_components -= 1

    # empirically derived minimum size
    min_size, max_size = 10, 500
    bad_indices = []
    filtered = np.zeros(labelled_image.shape, dtype=np.uint8)

    for i in range(nb_components):
        if min_size <= sizes[i] <= max_size:
            filtered[labelled_image == i + 1] = 255
        else:
            bad_indices.append(i)

    sizes_l = list(sizes)
    filtered_sizes = [j for i, j in enumerate(sizes_l) if i not in bad_indices]

    # Saving the filled and filtered images with proper scaling
    cv2.imwrite(str(Path(g.work) / "segmentation" / f"{g.plate_short}_{well_site}_filled.png"), filled.astype(np.uint8) * 255)
    cv2.imwrite(str(Path(g.work) / "segmentation" / f"{g.plate_short}_{well_site}_filtered.png"), filtered.astype(np.uint8) * 255)

    return filtered_sizes


# Originally created to segment microfilarae by calculating the area of a binary image.
# Can be used as a general segmentation tool
def segment_mf(binary):
    area = np.sum(binary)
    return area


# This function renames a .TIF file as .tif.  
# This is necessary because CellPose requires images to be in a directory and in .tif format for processing.
def rename_file_to_tif(src_file, temp_dir):
    temp_file = Path(temp_dir) / (Path(src_file).stem + '.tif')
    shutil.copy(src_file, temp_file)
    return temp_file


# This function runs the CellPose segmentation model on .tif images in a given directory.
def run_cellpose(model_type, model_path, temp_dir):
    cellpose_command = (
        f'python -m {model_type} '
        f'--dir {temp_dir} '
        f'--pretrained_model {model_path} '
        f'--diameter 0 --save_png --no_npy --verbose'
    )
    cellpose_command_split = shlex.split(cellpose_command)
    subprocess.run(cellpose_command_split)
