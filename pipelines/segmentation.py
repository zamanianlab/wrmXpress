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
from ultralytics import YOLO

from config import get_program_dir
PROGRAM_DIR = get_program_dir()

###############################################
######### SEGMENTATION MAIN FUNCTION  #########
###############################################

# Main segmentation function that performs image segmentation using either a Python-based method, Cellpose, or yolo.
def segmentation(g, options, well_site):
    # Create work and output directories and gather the segmentation method
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
            
            elif model_type == 'yolo': # Runs if model_type is YOLO
                model_path = PROGRAM_DIR / "pipelines" / "models" / "yolo" / options['model']
                
                # YOLO requires PNG format for processing
                # Use a temporary directory that is automatically cleaned up after use
                with tempfile.TemporaryDirectory() as temp_dir:
                    
                    # Convert TIF to PNG for YOLO processing
                    png_path = convert_tif_to_png_for_yolo(tiff_file, temp_dir)
                    
                    # Run YOLO segmentation
                    output_img_dir = output_dir / 'img'
                    masks_data = run_yolo_segmentation(
                        model_path, 
                        png_path, 
                        output_img_dir,
                        g.plate_short,
                        well_site,
                        wavelength + 1
                    )
                    
                    # Create combined labeled mask image (matching cellpose format)
                    if masks_data:
                        # Get image shape from first mask
                        image_shape = masks_data[0]['mask'].shape
                        labeled_image = create_labeled_mask_from_yolo(masks_data, image_shape)
                        
                        # Scale labeled image for visibility (multiply by 255 so objects are visible)
                        labeled_image_scaled = labeled_image * 255
                        
                        # Save labeled mask PNG to work directory
                        mask_filename = f"{g.plate_short}_{well_site}_w{wavelength + 1}.png"
                        mask_path = work_dir / mask_filename
                        cv2.imwrite(str(mask_path), labeled_image_scaled.astype(np.uint16))
                        
                        # Process segmentation metrics
                        for mask_info in masks_data:
                            result = {
                                'well_site': well_site,
                                'object_number': mask_info['mask_id'],
                                'size': mask_info['area'],
                                'compactness': mask_info['compactness'],
                                'width_px': mask_info['width'],
                                'length_px': mask_info['length']
                            }
                            all_results.append(result)
                    else:
                        # No masks detected
                        result = {
                            'well_site': well_site,
                            'object_number': "NA",
                            'size': "NA",
                            'compactness': "NA",
                            'width_px': "NA",
                            'length_px': "NA"
                        }
                        all_results.append(result)
                
                # Save results to CSV
                df = pd.DataFrame(all_results)
                csv_outpath = work_dir / f'{g.plate_short}_{well_site}_w{wavelength + 1}.csv'
                df.to_csv(csv_outpath, index=False)

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


# Convert a TIF file to PNG format for YOLO processing and returns the path to the PNGs.
# Called in segmentation after temp directory is made
def convert_tif_to_png_for_yolo(tif_path, temp_dir, p_low=2.0, p_high=98.0):

    # Read the TIF file
    img = cv2.imread(str(tif_path), cv2.IMREAD_ANYDEPTH)
    
    if img is None:
        raise ValueError(f"Failed to read TIF file: {tif_path}")
    
    # Convert to float for processing
    array = img.astype(np.float64)
    
    # Calculate percentile-based min/max for robust contrast
    lo = float(np.percentile(array, p_low))
    hi = float(np.percentile(array, p_high))
    
    # Rescale to 0-255 range
    if hi > lo:
        scaled = (array - lo) / (hi - lo)
        scaled = np.clip(scaled, 0.0, 1.0)
        img_uint8 = (scaled * 255.0 + 0.5).astype(np.uint8)
    else:
        img_uint8 = np.zeros_like(array, dtype=np.uint8)
    
    # Save as PNG
    png_path = Path(temp_dir) / (Path(tif_path).stem + '.png')
    cv2.imwrite(str(png_path), img_uint8)
    
    return png_path


# Measures a binary mask and returns a tuple of the area, width, length, and compactness in pixels.
# Called in run_yolo_segmentation()
def measure_mask_yolo(mask):

    mask_uint8 = (mask * 255).astype(np.uint8)
    contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return 0, 0, 0, 0
    
    cnt = max(contours, key=cv2.contourArea)  # largest contour
    area = cv2.contourArea(cnt)
    perimeter = cv2.arcLength(cnt, True)
    
    # Fit a rotated rectangle to estimate length and width
    rect = cv2.minAreaRect(cnt)
    (cx, cy), (w, h), angle = rect
    length = max(w, h)
    width = min(w, h)
    
    # Calculate compactness (for cellpose compatibility)
    compactness = (perimeter ** 2) / (4 * np.pi * area) if area > 0 else 0
    
    return area, width, length, compactness


# Run YOLO segmentation model on an image and process results.
# Called in segmentation after mask paths are returned
def run_yolo_segmentation(model_path, image_path, output_img_dir, plate_short, well_site, wavelength):
    # Load YOLO model
    model = YOLO(str(model_path))
    
    # Create output directory for prediction images
    output_img_dir.mkdir(parents=True, exist_ok=True)
    
    # Run inference - save prediction images with bounding boxes
    # YOLO will create a subdirectory with the name parameter
    run_name = f"{plate_short}_{well_site}_w{wavelength}"
    results = model.predict(
        source=str(image_path),
        save=True,
        project=str(output_img_dir),
        name=run_name,
        exist_ok=True
    )
    
    # Move prediction image from nested folder to img folder directly
    nested_folder = output_img_dir / run_name
    if nested_folder.exists():
        # Find the prediction image (usually a jpg or png)
        for img_file in nested_folder.glob('*'):
            if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                # Move to parent img directory with descriptive name
                dest_path = output_img_dir / f"{run_name}{img_file.suffix}"
                shutil.move(str(img_file), str(dest_path))
        
        # Remove the now-empty nested folder
        try:
            nested_folder.rmdir()
        except OSError:
            # Folder not empty or other error, leave it
            pass
    
    # Process results
    masks_data = []
    
    for result in results:
        if not result.masks:
            continue
        
        for i, mask in enumerate(result.masks.data):
            mask_np = mask.cpu().numpy()
            
            # Measure the mask
            area, width, length, compactness = measure_mask_yolo(mask_np)
            
            masks_data.append({
                'mask': mask_np,
                'mask_id': i + 1,
                'area': area,
                'width': width,
                'length': length,
                'compactness': compactness
            })
    
    return masks_data


# Creates a single labeled image where each mask has a unique pixel value to match the cellpose output format.
# Called in segmentation after getting mask shape
def create_labeled_mask_from_yolo(masks_data, image_shape):

    labeled_image = np.zeros(image_shape, dtype=np.uint16)
    
    for mask_info in masks_data:
        mask = mask_info['mask']
        mask_id = mask_info['mask_id']
        
        # Assign unique label to each mask
        labeled_image[mask > 0.5] = mask_id
    
    return labeled_image
