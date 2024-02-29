from PIL import Image
import cv2
import os
import re
from modules.preprocessing.image_processing import stitch, extract_well_name, well_idx_to_name
import numpy as np

# stitches all selected wells from timepoint 1 into diagnostic image of plate and saves it in 'output/dx' for each wavelength
# if video is flagged as True, do not save the images and simply return them in a list
def static_dx(g, rescale_factor):
    # get current directory
    # if images are at the site level, they must be stitched first and placed in generated 'work/dx' folder
    if g.mode == 'multi-site' and g.stitch == False:
        stitch(g, dx='static')
        base_dir = os.path.join(g.work, 'dx')
    else:
        base_dir = g.plate_dir  

    # ensure that current directory is valid
    if not os.path.isdir(base_dir):
        print(base_dir)
        raise ValueError("Path is not a directory.")

    # create 'output/dx' directory if it doesn't already exist
    os.makedirs(os.path.join(g.output, 'dx'), exist_ok=True)
    # save first frame of full plate image in 'output/dx'
    __save_frames(g, base_dir, rescale_factor, 'static')

def video_dx(g, rescale_factor):
    # if images are at the site level, they must be stitched first and placed in generated 'work/dx' folder
    if g.mode == 'multi-site' and g.stitch == False:
        stitch(g, dx='video')
        base_dir = os.path.join(g.work, 'dx')
    else:
        base_dir = g.plate_dir

    # ensure that current directory is valid
    if not os.path.isdir(base_dir):
        print(base_dir)
        raise ValueError("Path is not a directory.")
    
    # create 'output/dx' directory if it doesn't already exist
    os.makedirs(os.path.join(g.output, 'dx'), exist_ok=True)

    # if all wells selected, generate video of whole plate across all timepoints
    if g.wells == ['All']:
        # create frames and store paths to frames in dictionary
        # e.g. frames[0] = ['{path}/work/video_dx/TimePoint_1/20230511-p09-KTR_2789_w1_dx.TIF', '{path}/work/video_dx/TimePoint_2/20230511-p09-KTR_2789_w1_dx.TIF']
        frames = __save_frames(g, base_dir, rescale_factor, 'video')
        
        # set output directory
        out_dir = os.path.join(g.output, 'dx')

        # for each wavelength, create and save the video in 'output/dx'
        for wavelength in range(g.n_waves):
            outpath = outpath = os.path.join(out_dir, g.plate + f'_w{wavelength + 1}_dx.AVI')
            __create_video(frames[wavelength], outpath)
        
    # TODO: if specific wells selected, generate videos of selected wells across all timepoints
    else:
        pass

# combine wells into full plate images (referred to as a frame)
# if static_dx, save first frame in 'output/dx' and return empty dictionary
# if video_dx, save frames in 'work/video_dx'
# frames dictionary should contain image paths for each frame, where key is wavelength number and value is the list storing the path of every frame of that wavelength
# e.g. frames[0] = ['{path}/work/video_dx/TimePoint_1/20230511-p09-KTR_2789_w1_dx.TIF', '{path}/work/video_dx/TimePoint_2/20230511-p09-KTR_2789_w1_dx.TIF']
def __save_frames(g, base_dir, rescale_factor, dx):
    # create dictionary
    frames = {}

    # create set of selected wells; if all wells selected, set wells variable as None
    # should only apply for static_dx
    if g.wells == ['All']:
        wells = None
    else:
        wells = set(g.wells)

    # stitch wells into frames - save them in directory and store paths for frames in dictionary
    # if video_dx, frames should be saved in 'work/video_dx/TimePoint_{timepoint + 1}' and frames dictionary should contain image paths for each frame
    # if static_dx, first frame should be saved in 'output/dx' and function returns empty dictionary
    # populate dictionary
    for timepoint in range(g.time_points):
        current_dir = os.path.join(base_dir, f'TimePoint_{timepoint + 1}')
        # loop through wavelengths
        for wavelength in range(g.n_waves):
            # loop through individual wells and add them to current_frame list
            current_frame = []
            for row in range(g.rows):
                for col in range(g.cols):
                    # generate well id
                    well_id = well_idx_to_name(g, row, col)
                    # if not 'All' wells are selected and current well is not selected, skip over the file
                    if wells and well_id not in wells:
                        continue
                    # get path of current well image
                    # TODO: check whether g.plate or g.plate_short
                    img_path = os.path.join(current_dir, g.plate_short + f'_{well_id}_w{wavelength + 1}.TIF')
                    # add well to current frame
                    current_frame.append(img_path)
            # stitch current_frame into full plate image
            dx_image = __stitch_plate(g, current_frame, rescale_factor)
            # if static_dx save frame in 'output/dx' and skip over to next wavelength
            if dx == 'static':
                outpath = os.path.join(g.output, 'dx', g.plate + f'_w{wavelength + 1}_dx.TIF')
                dx_image.save(outpath)
                continue
            # create 'video_dx' directory in work if it doesn't already exist
            out_dir = os.path.join(g.work, 'video_dx', f'TimePoint_{timepoint + 1}')
            os.makedirs(out_dir, exist_ok=True)
            # save current frame in 'work/video_dx' and append its outpath to frames
            outpath = os.path.join(out_dir, g.plate + f'_w{wavelength + 1}_dx.TIF')
            dx_image.save(outpath)
            # create key-value pair if it doesn't exist
            if wavelength not in frames:
                frames[wavelength] = []
            # add current frame path to list for corresponding wavelength
            frames[wavelength].append(outpath)
    
    return frames

# takes a list of image paths and stitches all the specified wells together
# returns a PIL image
def __stitch_plate(g, image_paths, rescale_factor):
    # create an empty plate image based on the size of the well images (rescaled if required)
    first_image = __rescale_image(image_paths[0], rescale_factor)
    width = first_image.size[0]
    height = first_image.size[1]
    rows = g.rows
    cols = g.cols
    plate_image = Image.new('I;16', (cols * width, rows * height), 0)

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

    return plate_image

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

# converts a list of image paths to an AVI video and saves it in the 'output/dx' folder
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
    cv2.destroyAllWindows()