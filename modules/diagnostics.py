from PIL import Image
import cv2
import os
import re
from pathlib import Path
from modules.preprocessing.image_processing import stitch, extract_well_name
import numpy as np

def static_dx(g, rescale_factor):
    # get current directory
    # if images are at the site level, they must be stitched first and placed in generated 'work/dx' folder
    if g.mode == 'multi-site' and g.stitch == False:
        stitch(g, dx=True)
        current_dir = os.path.join(g.work, 'dx', 'Timepoint_1')
    else:
        current_dir = os.path.join(g.plate_dir, 'TimePoint_1')

    # ensure that current directory is valid
    if not os.path.isdir(current_dir):
        print(current_dir)
        raise ValueError("Path is not a directory.")
    
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

    # create output directory if it doesn't already exist
    out_dir = os.path.join(g.output, 'dx')
    os.makedirs(out_dir, exist_ok=True)

    # stitch images for each wavelength and save them in the output folder
    for wavelength_num, image_paths in images.items():
        dx_image = __sdx_stitch(g, image_paths, rescale_factor)
        outpath = Path.home().joinpath(out_dir, g.plate + f'_w{wavelength_num}_dx.TIF')
        dx_image.save(outpath)

# takes a list of image paths and stitches all the specified wells together
def __sdx_stitch(g, image_paths, rescale_factor):
    # create an empty plate image based on the size of the well images (rescaled if required)
    first_image = __rescale_image(image_paths[0], rescale_factor)
    height = first_image.size[0]
    width = first_image.size[1]
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
        elif rescale_factor == 1:
            return img
        # rescale the image
        else:
            size = ((np.array(img.size) * rescale_factor).astype(int))
            rescaled_image = img.resize(size, resample=Image.NEAREST)

    return rescaled_image

def tif_to_avi(g, image_paths, wavelength_num, fps=30):
    """
    Convert a list of TIF images to an AVI video.

    fps (int, optional): Frames per second for the output video. Default is 30.
    """

    outpath = Path.home().joinpath(g.output, g.plate + f'_w{wavelength_num}_dx.TIF')

    # get the first image to extract dimensions
    first_image = cv2.imread(image_paths[0])
    height, width, _ = first_image.shape

    # define the codec and create VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    video = cv2.VideoWriter(outpath, fourcc, fps, (width, height))

    # iterate through each image and add it to the video
    for image_path in image_paths:
        image = cv2.imread(image_path)
        video.write(image)

    # release the video writer
    video.release()
