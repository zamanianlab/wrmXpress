from PIL import Image
import cv2
import os
from preprocessing.image_processing import stitch_all_timepoints, stitch_directory, extract_well_name, generate_selected_image_paths
import numpy as np

# stitches all selected wells from a directory into diagnostic image of plate and saves it in output directory for each wavelength
# if sites need to be stitched first, save them in the specified work directory
# return list of outpaths of static_dx images generated
def static_dx(g, wells, input_dir, output_dir, work_dir, rescale_factor, format='TIF'):
    # get current directory
    # if images are at the site level, they must be stitched first and placed in generated an intermediate folder
    if g.mode == 'multi-site' and g.stitch == False:
        if not work_dir:
            raise ValueError("Work directory has not been specified")
        stitch_directory(g, wells, input_dir, work_dir)
        base_dir = work_dir
    else:
        base_dir = input_dir

    # ensure that current directory is valid
    if not os.path.isdir(base_dir):
        print(base_dir)
        raise ValueError("Path is not a directory.")

    # create output directory if it doesn't already exist
    os.makedirs(output_dir, exist_ok=True)

    outpaths = []

    # for each wavelength, generate image paths of wells to be stitched
    for wavelength in range(g.n_waves):
        image_paths = generate_selected_image_paths(g, wells, wavelength+1, base_dir, format)
        # stitch plate and save in output directory
        outpath = os.path.join(output_dir, g.plate_short + f'_w{wavelength+1}.{format}')
        outpaths.append(outpath)
        __stitch_plate(g, image_paths, outpath, rescale_factor, format)

    return outpaths

def video_dx(g, wells, input_dir, output_dir, static_work_dir, video_work_dir, rescale_factor):
    # if all wells are selected, run static_dx on each timepoint and save plate image in specified output folder
    # add plate image to list of image paths for video conversion
    if g.wells == ['All']:
        # create dictionary to hold image paths of each wavelength
        frame_paths = {}
        # populate dictionary with each wavelengths' frame paths
        for timepoint in range(g.time_points):
            # create path for current timepoint directory
            current_timepoint = os.path.join(input_dir, f'TimePoint_{timepoint+1}')
            # create outpath for generated static_dx image
            static_output_dir = os.path.join(video_work_dir, f'TimePoint_{timepoint+1}')
            static_work_timepoint = os.path.join(static_work_dir, f'TimePoint_{timepoint+1}')
            # generate static_dx image for current timepoint and save in static_output_dir
            current_frame_paths = static_dx(g, wells, current_timepoint, static_output_dir, static_work_timepoint, rescale_factor)
            # for each wavelength populate the frame paths dictionary
            for wavelength in range(g.n_waves):
                if wavelength in frame_paths:
                    frame_paths[wavelength].append(current_frame_paths[wavelength])
                else:
                    frame_paths[wavelength] = [current_frame_paths[wavelength]]

        # create video for each wavelength and save in output directory
        for wavelength in range(g.n_waves):
            outpath = os.path.join(output_dir, g.plate_short + f'_w{wavelength + 1}.AVI')
            __create_video(frame_paths[wavelength], outpath)
    
    # if not all wells selected, videos will be at the well level
    else:
        # if wells have not been stitched, stitch them first
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

# takes a list of image paths and stitches all the selected wells together
# saves stitched image to specified outpath
def __stitch_plate(g, image_paths, outpath, rescale_factor, format='TIF'):
    # create an empty plate image based on the size of the well images (rescaled if required)
    first_image = __rescale_image(image_paths[0], rescale_factor)
    width = first_image.size[0]
    height = first_image.size[1]
    rows = g.rows
    cols = g.cols

    if format == 'TIF':
        plate_image = Image.new('I;16', (cols * width, rows * height), 0)
    else:
        plate_image = Image.new('RGB', (cols * width, rows * height))

    # loop through each image path
    for image_path in image_paths:
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

# rescales an image by the rescale factor
def __rescale_image(image_path, rescale_factor):
    with Image.open(image_path) as img:
        # if rescale factor is less than or equal to 0 or greater than 1, raise an error
        if rescale_factor <=0 or rescale_factor > 1:
            raise ValueError("Rescale factor cannot be less than or equal to 0 or greater than 1.")
        # if rescale factor is 1, do not do anything
        # elif rescale_factor == 1:
        #     return img
        # rescale the image
        else:
            size = ((np.array(img.size) * rescale_factor).astype(int))
            rescaled_image = img.resize(size, resample=Image.NEAREST)

    return rescaled_image

# converts a list of image paths to an AVI video and saves it to the specified output video path
def __create_video(image_paths, output_video_path, duration=15):
    # check if duration is specified in seconds
    if not isinstance(duration, (int, float)) or duration <= 0:
        raise ValueError("Duration must be a positive number in seconds.")

    # read the first image to get dimensions
    first_image = cv2.imread(image_paths[0], cv2.IMREAD_UNCHANGED)
    height, width = first_image.shape[:2]

    # define the codec and create a VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    fps = len(image_paths) / duration
    video_writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height), isColor=False)

    # iterate over image paths, convert to 8-bit, and add them to the video
    for image_path in image_paths:
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        # normalize pixel values to fit into 8-bit range
        img_normalized = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        video_writer.write(img_normalized)

    # release the VideoWriter and close all windows
    video_writer.release()