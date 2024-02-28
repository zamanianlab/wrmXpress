from PIL import Image
import cv2
import os
import re
from modules.preprocessing.image_processing import stitch, extract_well_name, well_idx_to_name
import numpy as np

# stitches all selected wells from timepoint 1 into diagnostic image of plate and saves it in 'output/dx' for each wavelength
# if video is flagged as True, do not save the images and simply return them in a list
def static_dx(g, rescale_factor, timepoint=1):
    # get current directory
    # if images are at the site level, they must be stitched first and placed in generated 'work/dx' folder
    if g.mode == 'multi-site' and g.stitch == False:
        stitch(g, dx='static')
        current_dir = os.path.join(g.work, 'dx', f'Timepoint_{timepoint}')
    else:
        current_dir = os.path.join(g.plate_dir, f'TimePoint_{timepoint}')

    # ensure that current directory is valid
    if not os.path.isdir(current_dir):
        print(current_dir)
        raise ValueError("Path is not a directory.")
    
    # group images by wavelength number (e.g. all wells with 'w2' will be stitched together)
    # images has a key of wavelength number and value of list of all the corresponding files for that wavelength number
    images = __group_images(g, current_dir)

    # create 'output/dx' directory if it doesn't already exist
    out_dir = os.path.join(g.output, 'dx')
    os.makedirs(out_dir, exist_ok=True)

    # stitch images for each wavelength and save them in the output folder
    for wavelength_num, image_paths in images.items():
        dx_image = __stitch_plate(g, image_paths, rescale_factor)
        outpath = os.path.join(out_dir, g.plate + f'_w{wavelength_num}_dx.TIF')
        dx_image.save(outpath)

def video_dx(g, rescale_factor):
    # if all wells selected, generate video of whole plate across all timepoints
    if g.wells == ['All']:
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
        out_dir = os.path.join(g.output, 'dx')
        os.makedirs(out_dir, exist_ok=True)

        # create a dictionary where the key is wavelength number and the value is the list holding the path of every frame of that wavelength for the entire plate
        frames = {}
        # populate dictionary
        for timepoint in range(g.time_points):
            current_dir = os.path.join(base_dir, f'TimePoint_{timepoint + 1}')
            # stitch wells into plates for each wavelength and save them in the work folder
            for wavelength in range(g.n_waves):
                # loop through individual wells and stitch them into full plate image
                current_frame = []
                for row in range(g.rows):
                    for col in range(g.cols):
                        # generate well id
                        well_id = well_idx_to_name(g, row, col)
                        # get path of current image of well
                        img_path = os.path.join(current_dir, g.plate_short + f'_{well_id}_w{wavelength + 1}.TIF')
                        # add well to current frame
                        current_frame.append(img_path)
                # stitch current frame and save it in work/video_dx
                dx_image = __stitch_plate(g, current_frame, rescale_factor)
                # create 'video_dx' directory in work if it doesn't already exist
                out_dir = os.path.join(g.work, 'video_dx', f'TimePoint_{timepoint + 1}')
                os.makedirs(out_dir, exist_ok=True)
                # save current frame in 'work/video_dx' and append its outpath to frames
                outpath = os.path.join(out_dir, g.plate_short + f'_w{wavelength + 1}_dx.TIF')
                dx_image.save(outpath)
                # create key-value pair if it doesn't exist
                if wavelength not in frames:
                    frames[wavelength] = []
                # add current frame path to list for corresponding wavelength
                frames[wavelength].append(outpath)

        # create 'output/dx' directory if it doesn't already exist
        out_dir = os.path.join(g.output, 'dx')
        os.makedirs(out_dir, exist_ok=True)
        
        # for each wavelength, create and save the video in 'output/dx'
        for wavelength in range(g.n_waves):
            outpath = outpath = os.path.join(out_dir, g.plate_short + f'_w{wavelength + 1}_dx.AVI')
            __create_video(frames[wavelength], outpath)
        
    # TODO: if specific wells selected, generate videos of selected wells across all timepoints
    else:
        pass

# given a timepoint directory, group images by wavelength number (e.g. all wells with 'w2' will be placed in the same list together in a dictionary where the key is the wavelength number)
# only include selected wells as in g.wells
def __group_images(g, current_dir):
    # use regex to parse filename and extract well ID and wavelength number
    pattern = re.compile(r'(.+)_([A-Z][0-9]{2,})_w(\d+)\.(tif|TIF)$')

    # create set of selected wells; if all wells selected, set wells variable as None
    if g.wells == ['All']:
        wells = None
    else:
        wells = set(g.wells)

    # group images by wavelength number (e.g. all wells with 'w2' will be stitched together)
    images = {}
    for filename in os.listdir(current_dir):
        if filename.lower().endswith('.tif'):
            match = pattern.match(filename)
            if match:
                well = match.group(2)
                # if not all wells are selected and current well is not selected, skip over the file
                if wells and well not in wells:
                    continue
                wavelength_num = match.group(3)
                if (wavelength_num) not in images:
                    images[wavelength_num] = []
                images[wavelength_num].append(os.path.join(current_dir, filename))

    return images

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
def create_video(image_paths, output_video_path, duration=15):
    # Check if duration is specified in seconds
    if not isinstance(duration, (int, float)) or duration <= 0:
        raise ValueError("Duration must be a positive number in seconds.")

    # Read the first image to get dimensions
    first_image = cv2.imread(image_paths[0], cv2.IMREAD_UNCHANGED)
    height, width = first_image.shape[:2]

    # Define the codec and create a VideoWriter object
    fourcc = 0
    fps = len(image_paths) / duration
    video_writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    # Iterate over image paths, convert to 8-bit, and add them to the video
    for image_path in image_paths:
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        # Normalize pixel values to fit into 8-bit range
        img_normalized = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        # Convert to 3-channel (grayscale to BGR)
        img_bgr = cv2.cvtColor(img_normalized, cv2.COLOR_GRAY2BGR)
        video_writer.write(img_bgr)

    # Release the VideoWriter and close all windows
    video_writer.release()
    cv2.destroyAllWindows()

def __create_video(image_paths, output_video_path, duration=15):
    # Check if duration is specified in seconds
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
    cv2.destroyAllWindows()