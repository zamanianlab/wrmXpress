from PIL import Image
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

    # if only one wavelength, just stitch wells from first timepoint
    if g.n_waves == 1:
        image_paths = []
        for image_path in os.listdir(current_dir):
            if image_path.lower().endswith('.tif'):
                image_paths.append(os.path.join(current_dir, image_path))
        dx_image = __sdx_stitch(g, image_paths, rescale_factor)
        out_dir = os.path.join(g.output, 'dx')
        os.makedirs(out_dir, exist_ok=True)
        outpath = os.path.join(out_dir, g.plate + f'_w1_dx.TIF')
        dx_image.save(outpath)
        return

    # if multiple wavelengths, stitch wells from first timepoint for each wavelength
    elif g.n_waves > 1:
        # use regex to parse filename and extract well ID and wavelength number
        pattern = re.compile(r'(.+)_([A-Z][0-9]{2,})_w(\d+)\.(tif|TIF)$')

        # group images by wavelength number (e.g. all wells with 'w2' will be stitched together)
        images = {}
        for filename in os.listdir(current_dir):
            if filename.lower().endswith('.tif'):
                match = pattern.match(filename)
                if match:
                    wavelength_num = match.group(3)
                    if (wavelength_num) not in images:
                        images[wavelength_num] = []
                    images[wavelength_num].append(os.path.join(current_dir, filename))

        # stitch images for each wavelength and save them in the output folder
        for wavelength_num, image_paths in images.items():
            dx_image = __sdx_stitch(g, image_paths, rescale_factor)
            outpath = Path.home().joinpath(g.output, g.plate + f'_w{wavelength_num}_dx.TIF')
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
