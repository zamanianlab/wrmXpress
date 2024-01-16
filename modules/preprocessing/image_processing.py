from pathlib import Path
from string import ascii_uppercase
from PIL import Image
import cv2
import os
import re
import shutil
import math
import numpy as np

# converts avi to imageXpress
def avi_to_ix(g):
    # this assumes that the avi file has the same name as the directory it is in
    vid_path = Path.home().joinpath(g.plate_dir, g.plate + '.avi')

    # gets avi information
    vid = cv2.VideoCapture(str(vid_path))
    ret = True
    frames = []
    while ret:
        # returns next frame
        ret, img = vid.read()
        if ret:
            frames.append(img)

    timepoints = len(frames)

    # loop through each timepoint
    for timepoint in range(timepoints):
        dir = g.plate_dir.joinpath('TimePoint_' + str(timepoint + 1))
        if dir.exists():
            shutil.rmtree(dir)
        dir.mkdir(parents=True, exist_ok=True)
        # add '_A01_w1' to file name
        outpath = g.plate_dir.joinpath('TimePoint_' + str(timepoint + 1), g.plate + '_A01_w1.TIF')
        cv2.imwrite(str(outpath), frames[timepoint])

    __create_htd(g, timepoints)

    return timepoints

# crops all images to the individual well level
def grid_crop(g):
    rows_per_image = g.rows // g.rec_rows
    cols_per_image = g.cols // g.rec_cols

    # loop through each timepoint folder
    for timepoint in range(g.time_points):
        original_images = os.listdir(g.plate_dir.joinpath('TimePoint_' + str(timepoint + 1)))

        # loop through each image in timepoint folder
        for current in original_images:
            # get path of current image
            current_path = os.path.join(g.plate_dir, 'TimePoint_' + str(timepoint + 1), current)

            # conversion of the well name to an array - A01 becomes [0, 0] where the format is [col, row]
            # group refers to group of wells to be split (for example splitting the group A01 into a 2x2 would result in wells A01, A02, B01, and B02)
            # get group_id using regex by extracting column letter and row number from current
            letter, number, site, wavelength = __extract_well_name(current)
            group_id = [__capital_to_num(letter), int(number) - 1]

            # split image into individual wells
            individual_wells = __split_image(current_path, cols_per_image, rows_per_image)

            # loop through individual well images and save with corresponding well name
            for i in range(rows_per_image):
                for j in range(cols_per_image):
                    well_name = __generate_well_name(group_id, i, j, cols_per_image, rows_per_image, g.cols)
                    # save current image as well name
                    if site:
                        outpath = g.plate_dir.joinpath('TimePoint_' + str(timepoint + 1), g.plate + f'_{well_name}_s{site}_w{wavelength}.TIF')
                    else:
                        outpath = g.plate_dir.joinpath('TimePoint_' + str(timepoint + 1), g.plate + f'_{well_name}_w{wavelength}.TIF')
                    cv2.imwrite(str(outpath), individual_wells[i * cols_per_image + j])

# stitches all sites into wells by well ID (e.g. all files of well C03 will be stitched together)
def stitch(g):
    # loop through each timepoint folder
    for timepoint in range(g.time_points):
        # get current directory
        current_dir = os.path.join(g.plate_dir, 'TimePoint_' + str(timepoint + 1))

        # ensure that current directory is valid
        if not os.path.isdir(current_dir):
            raise ValueError("Path is not a directory.")
        
        # use regex to parse filename and extract well ID and wavelength number
        pattern = re.compile(r'(.+)_([A-Z][0-9]{2,})_s(\d+)_w(\d+)\.(tif|TIF)$')

        # group images by well ID and wavelength number (e.g. all sites with 'A01' and 'w2' will be stitched together)
        # TODO: add notes about key value pairings
        images = {}
        for filename in os.listdir(current_dir):
            if filename.lower().endswith('.tif'):
                match = pattern.match(filename)
                if match:
                    well_id = match.group(2)
                    wavelength_num = match.group(4)
                    if (well_id, wavelength_num) not in images:
                        images[(well_id, wavelength_num)] = []
                    images[(well_id, wavelength_num)].append(os.path.join(current_dir, filename))

        # stitch images for each well ID, apply mask if applicable, and save them in the current folder
        for file_info, image_paths in images.items():
            stitched_image = __stitch_images(sorted(image_paths))
            outpath = g.plate_dir.joinpath('Timepoint_' + str(timepoint + 1), g.plate + f'_{file_info[0]}_w{file_info[1]}.TIF')
            if g.circle_diameter != 'NA':
                __apply_mask(stitched_image, g.circle_diameter, 'circle').save(outpath)
            elif g.square_side != 'NA':
                __apply_mask(stitched_image, g.square_side, 'square').save(outpath)
            else:
                stitched_image.save(outpath)

# creates HTD for avi input
def __create_htd(g, timepoints):
    # make HTD for non-IX data
    lines = []
    lines.append('"Description", ' + "AVI" + "\n")
    lines.append('"TimePoints", ' + str(timepoints) + "\n")
    lines.append('"XWells", ' + str(g.rec_cols) + "\n")
    lines.append('"YWells", ' + str(g.rec_rows) + "\n")
    lines.append('"XSites", ' + "1" + "\n")
    lines.append('"YSites", ' + "1" + "\n")
    lines.append('"NWavelengths", ' + "1" + "\n")
    lines.append('"WaveName1", ' + '"Transmitted Light"' + "\n")

    htd_path = g.plate_dir.joinpath(g.plate_short + '.HTD')
    with open(htd_path, mode='w') as htd_file:
        htd_file.writelines(lines)

# extracts the column letter, row number, site number, and wavelength number from the image name
def __extract_well_name(well_string):
    # regular expression pattern to match the format
    pattern = r'_([A-Z])(\d+)(?:_s(\d+)){0,1}_w(\d+)\.(tif|TIF)$'
    match = re.search(pattern, well_string)

    # check number of groups to determine site number if applicable and well number
    if match:
        # extract column letter
        letter = match.group(1)

        # extract row number
        number = match.group(2)

        # extract site number
        # if no site, site will be None
        site = match.group(3)

        # extract wavelength number
        wavelength = match.group(4)

        return letter, number, site, wavelength
    else:
        # return None if the pattern doesn't match
        return None, None, None, None

# converts capital letters to numbers, where A is 0, B is 1, and so on
def __capital_to_num(alpha):
    return ord(alpha) - 65

# splits image into x by y images and delete original image
def __split_image(img_path, x, y):
    original_img = cv2.imread(img_path)
    if original_img is None:
        raise ValueError("Could not load the image")
    
    # get dimensions of original image
    original_height, original_width, unused = original_img.shape

    # calculate dimensions of cropped images
    height = original_height // y
    width = original_width // x

    images = []

    # loop through grid and split the image
    # place images into array row by row
    for i in range(y):
        for j in range(x):
            # calculate the coordinates for cropping
            start_x = j * width
            end_x = (j + 1) * width
            start_y = i * height
            end_y = (i + 1) * height

            # crop the region from the original image
            cropped_img = original_img[start_y:end_y, start_x:end_x]

            # append the small image to the array
            images.append(cropped_img)

    # delete original uncropped image
    os.remove(img_path)

    return images

# generates well name using the provided group id
def __generate_well_name(group_id, col, row, cols_per_image, rows_per_image, total_cols):
    # calculate well_id
    well_id = [group_id[0] * cols_per_image + col, group_id[1] * rows_per_image + row]

    # extract letter
    letter = chr(well_id[0] + 65)

    # determine number of preceding zeroes for single digit numbered columns
    # if total columns is less than 100, columns will be two digits, else number of digits for columns will match the total columns
    if well_id[1] < 9:
        if total_cols >= 100:
            num_zeroes = len(str(total_cols)) - 1
            number = num_zeroes*"0" + str(well_id[1] + 1)
        else:
            number = f"0{well_id[1] + 1}"
    else:
        number = str(well_id[1] + 1)
    return f"{letter}{number}"

# stitches sites into an n by n square image and fills extra space with black
def __stitch_images(image_paths):
    if not image_paths:
        raise ValueError("The list of image paths is empty.")

    # Load the first image to determine individual image size
    with Image.open(image_paths[0]) as img:
        img_width, img_height = img.size

    if img_width != img_height:
        raise ValueError("Images are not square.")

    # Calculate dimensions for the output image
    num_images = len(image_paths)
    side_length = math.ceil(math.sqrt(num_images))
    canvas_size = side_length * img_width

    # Create a new image with a black background
    stitched_image = Image.new('I;16', (canvas_size, canvas_size), 0)

    # Place each image into the stitched_image
    # assumes that stitched sites form a square (if requires change in the future, use x_sites and y_sites)
    for i, img_path in enumerate(image_paths):
        with Image.open(img_path) as img:
            if img.size != (img_width, img_height):
                raise ValueError(f"Image at {img_path} is not of the correct size.")
            x = (i % side_length) * img_width
            y = (i // side_length) * img_height
            stitched_image.paste(img, (x, y))
        
        # delete original image
        os.remove(img_path)

    return stitched_image

# apply a circle or square mask as specified by the type parameter
# mask_size is a fraction of the current image size
# circle mask will add a black border around the specified size of circle while square mask  crops the image to the specified size
def __apply_mask(image, mask_size, type):
    # get current height and width of image
    width, height = image.size

    # ensure the image is square
    if width != height:
        raise ValueError("Image must be square")
    
    # square mask
    if type == 'square':
        new_side_length = width * mask_size
        # calculate the coordinates to crop the image
        left = (width - new_side_length) // 2
        top = (height - new_side_length) // 2
        right = (width + new_side_length) // 2
        bottom = (height + new_side_length) // 2

        # crop the image
        masked_image = image.crop((left, top, right, bottom))

        return masked_image
    
    #circle mask
    elif type == 'circle':
        # calculate the circle's radius
        radius = (width * mask_size) / 2

        # create a circular mask
        y, x = np.ogrid[:height, :width]
        center = (width // 2, height // 2)
        # find squared distance of each coordinate from the centre and return True if it is within the mask area
        mask_area = (x - center[0])**2 + (y - center[1])**2 > radius**2

        # apply the mask to the image
        masked_array = np.array(image)
        masked_array[mask_area] = 0
        masked_image = Image.fromarray(masked_array, mode='I;16')

        return masked_image