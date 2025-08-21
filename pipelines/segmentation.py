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
from datetime import datetime

from config import get_program_dir
PROGRAM_DIR = get_program_dir()


def create_circular_mask(h, w, center=None, radius=None):
    if center is None:
        center = (int(w / 2), int(h / 2))
    if radius is None:
        radius = min(center[0], center[1], w - center[0], h - center[1])

    Y, X = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((X - center[0])**2 + (Y - center[1])**2)
    mask = dist_from_center <= radius
    return mask


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
    cv2.imwrite(str(Path(g.work) / "segmentation" / f"{g.plate}_{well_site}_filled.png"), filled.astype(np.uint8) * 255)
    cv2.imwrite(str(Path(g.work) / "segmentation" / f"{g.plate}_{well_site}_filtered.png"), filtered.astype(np.uint8) * 255)

    return filtered_sizes


def segment_mf(binary):
    area = np.sum(binary)
    return area

def rename_file_to_temp_tif(src_file, temp_dir):
    """Rename a single TIF file to .tif in a temporary directory."""
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
    """Perform segmentation based on model type."""
    work_dir = Path(g.work) / 'segmentation'
    output_dir = Path(g.output) / 'segmentation'
    work_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    model_path = PROGRAM_DIR / "pipelines" / "models" / "cellpose" / options['model']
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
            tiff_file_base = os.path.join(g.input, g.plate, f"TimePoint_{timepoint}", f"{g.plate_short}_{well_site}")
            tiff_file = f"{tiff_file_base}_w{wavelength + 1}.TIF" if os.path.exists(f"{tiff_file_base}_w{wavelength + 1}.TIF") else f"{tiff_file_base}.TIF"

            if model_type == 'python':
                if os.path.exists(tiff_file):
                    out_dict = defaultdict(list)
                    cols = []

                    start_time = datetime.now()
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

                    segmented_area  = segment_sma(g, well_site, binary) if options['model'] == 'segment_sma' else segment_mf(binary)

                    # blur_png = g.work.joinpath(work_dir, f"{g.plate}_{well_site}_{wavelength+1}_blur.png")
                    # cv2.imwrite(str(blur_png), blur)

                    # sobel_png = g.work.joinpath(work_dir, f"{g.plate}_{well_site}_{wavelength+1}_edge.png")
                    # cv2.imwrite(str(sobel_png), sobel * 255)

                    bin_png = g.work.joinpath(work_dir, f"{g.plate_short}_{well_site}_w{wavelength+1}.png")
                    cv2.imwrite(str(bin_png), binary * 255)
                    
                    print(f"Segmented area is {segmented_area}")

                    # Save segmentation result
                    if 'segmented_area' not in cols:
                        cols.append('segmented_area')
                    out_dict[well_site].append(segmented_area)
                    df = pd.DataFrame.from_dict(out_dict, orient='index', columns=cols)
                    outpath = work_dir.joinpath(f"{g.plate_short}_{well_site}_w{wavelength+1}.csv")
                    df.to_csv(path_or_buf=outpath, index_label='well_site')

            else: # Runs if model_type is Cellpose
                with tempfile.TemporaryDirectory() as temp_dir:
                    if os.path.exists(tiff_file):
                        rename_file_to_temp_tif(tiff_file, temp_dir)
                        run_cellpose(model_type, model_path, temp_dir)

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
                csv_outpath = work_dir / f'{g.plate}_{well_site}_w{wavelength + 1}.csv'
                df.to_csv(csv_outpath, index=False)

    return wavelengths
