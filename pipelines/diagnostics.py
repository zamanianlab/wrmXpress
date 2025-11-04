from datetime import datetime
import cv2
import os
import numpy as np
import re
from PIL import Image

from preprocessing.image_processing import stitch_all_timepoints, stitch_directory, extract_well_name, generate_selected_image_paths

##################################
######### MAIN FUNCTIONS #########
##################################

# Generate a static diagnostic image for a plate by stitching selected wells
# Saves the resulting stitched image in the output directory for each wavelength
# Returns a list of paths to the stitched images
def static_dx(g, wells, input_dir, output_dir, work_dir, wavelengths, rescale_factor, format='TIF'):
    start_time = datetime.now()
    print("Stitching images for static dx.")
    
    if wavelengths is None:
        wavelengths = [i for i in range(g.n_waves)]
    
    # If images are at the site level, they must be stitched first and placed in generated an intermediate folder
    if g.mode == 'multi-site' and g.stitch == False:
        if not work_dir:
            raise ValueError("Work directory has not been specified")
        # Stitch site-level images into intermediate folder
        stitch_directory(g, wells, input_dir, work_dir)
        base_dir = work_dir
    else:
        base_dir = input_dir

    # Ensure the directory exists and create it if it doesn't exist
    if not os.path.isdir(base_dir):
        print(base_dir)
        raise ValueError("Path is not a directory.")
    os.makedirs(output_dir, exist_ok=True)
    outpaths = []

    # For each wavelength, generate image paths of wells to be stitched
    for wavelength in wavelengths:
        image_paths = generate_selected_image_paths(g, wells, wavelength+1, base_dir, format)
        outpath = os.path.join(output_dir, g.plate_short + f'_w{wavelength+1}.{format}')
        outpaths.append(outpath)
        __stitch_plate(g, image_paths, outpath, rescale_factor, format)

    print("Finished stitching images in {}".format(datetime.now() - start_time))
    return outpaths


# Generate a video diagnostic of a plate or well
# If all wells selected, stitches each timepoint into a plate image first using static_dx
# Otherwise, generates video at the well level
def video_dx(g, wells, input_dir, output_dir, static_work_dir, video_work_dir, rescale_factor):
    print("Creating video for video dx...")
    
    if g.wells == ['All']:
        # Dictionary to store frame paths for each wavelength
        frame_paths = {}
        time_points = len([
            name for name in os.listdir(input_dir) 
            if os.path.isdir(os.path.join(input_dir, name)) and re.match(r"TimePoint_\d+", name)
        ])
        
        # Generate static_dx image for each timepoint
        for timepoint in range(time_points):
            # Create path for current timepoint directory
            current_timepoint = os.path.join(input_dir, f'TimePoint_{timepoint+1}')
            # Create outpath for generated static_dx image
            static_output_dir = os.path.join(video_work_dir, f'TimePoint_{timepoint+1}')
            static_work_timepoint = os.path.join(static_work_dir, f'TimePoint_{timepoint+1}')
            # Generate static_dx image for current timepoint and save in static_output_dir
            current_frame_paths = static_dx(g, wells, current_timepoint, static_output_dir, static_work_timepoint, None, rescale_factor)
            
            # Append frame paths for each wavelength
            for wavelength in range(g.n_waves):
                if wavelength in frame_paths:
                    frame_paths[wavelength].append(current_frame_paths[wavelength])
                else:
                    frame_paths[wavelength] = [current_frame_paths[wavelength]]

        # Create video for each wavelength and save in output directory
        for wavelength in range(g.n_waves):
            outpath = os.path.join(output_dir, g.plate_short + f'_w{wavelength + 1}.AVI')
            __create_video(frame_paths[wavelength], outpath)
    
    else:
        # If wells have not been stitched, stitch them first
        if g.mode == "multi-site" and g.stitch == False:
            stitch_all_timepoints(g, wells, input_dir, video_work_dir)
            base_dir = video_work_dir
        else:
            base_dir = input_dir
        
        for well in wells:
            frame_paths = []
            for wavelength in range(g.n_waves):
                for timepoint in range(g.time_points):
                    frame_path = os.path.join(base_dir, f'TimePoint_{timepoint + 1}', g.plate_short + f'_{well}_w{wavelength + 1}.TIF')
                    frame_paths.append(frame_path)
                outpath = os.path.join(output_dir, g.plate_short + f'_{well}_w{wavelength + 1}.AVI')
                __create_video(frame_paths, outpath)
                
    print("Finished creating video.")


#####################################
######### HELPER FUNCTIONS  #########
#####################################

# Stitch a list of well images into a single plate image
def __stitch_plate(g, image_paths, outpath, rescale_factor, format='TIF'):
    first_image = __rescale_image(image_paths[0], rescale_factor)
    width = first_image.size[0]
    height = first_image.size[1]
    rows = g.rows
    cols = g.cols

    # Create blank plate image
    if format == 'TIF':
        plate_image = Image.new('I;16', (cols * width, rows * height), 0)
    else:
        plate_image = Image.new('RGB', (cols * width, rows * height))

    # Paste each well image into the plate image
    for image_path in image_paths:
        print(f"Reading image: {image_path}")
        # extract well ID from the image path
        letter, number, _, _ = extract_well_name(image_path)

        # extract row and column indices from well name
        col_index = int(number) - 1
        row_index = ord(letter.lower()) - ord('a')

        # calculate the position to paste the well image
        paste_position = (col_index * width, row_index * height)

        # open the well image and rescale it if required
        well_image = __rescale_image(image_path, rescale_factor)

        # paste the well image onto the plate image
        plate_image.paste(well_image, paste_position)

    plate_image.save(outpath)

# Rescale an image by the rescale factor
def __rescale_image(image_path, rescale_factor):
    with Image.open(image_path) as img:
        # If rescale factor is less than or equal to 0 or greater than 1, raise an error.
        if rescale_factor <=0 or rescale_factor > 1:
            raise ValueError("Rescale factor cannot be less than or equal to 0 or greater than 1.")
        else:
            size = ((np.array(img.size) * rescale_factor).astype(int))
            rescaled_image = img.resize(size, resample=Image.NEAREST)
    return rescaled_image

# Convert a list of images into an AVI video
def __create_video(image_paths, output_video_path, duration=15):
    if not isinstance(duration, (int, float)) or duration <= 0:
        raise ValueError("Duration must be a positive number in seconds.")

    # Read the first image to get dimensions
    first_image = cv2.imread(image_paths[0], cv2.IMREAD_UNCHANGED)
    height, width = first_image.shape[:2]

    # Define the codec and create a VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    fps = len(image_paths) / duration
    video_writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height), isColor=False)

    # Iterate over image paths, convert to 8-bit, and add them to the video
    for image_path in image_paths:
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        # Normalize pixel values to fit into 8-bit range
        img_normalized = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        video_writer.write(img_normalized)

    # Release the VideoWriter and close all windows
    video_writer.release()
