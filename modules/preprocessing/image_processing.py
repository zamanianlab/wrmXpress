from pathlib import Path
from string import ascii_uppercase
import cv2
import os
import re
import shutil

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
    for timepoint in range(g.time_points):
        original_images = os.listdir(g.plate_dir.joinpath('TimePoint_' + str(timepoint + 1)))
        for current in original_images:
            current_path = os.path.join(g.plate_dir, 'TimePoint_' + str(timepoint + 1), current)
            # conversion of the well name to an array - A01 becomes [0, 0] where the format is [col, row]
            # group refers to group of wells to be split (for example splitting the group A01 into a 2x2 would result in wells A01, A02, B01, and B02)
            # get group_id using regex by extracting column letter and row number from current
            letter, number, site, wavelength = __extract_well_name(current)
            group_id = [__capital_to_num(letter), int(number) - 1]
            individual_wells = __split_image(current_path, cols_per_image, rows_per_image)
            for i in range(rows_per_image):
                for j in range(cols_per_image):
                    well_name = __generate_well_name(group_id, i, j, cols_per_image, rows_per_image, g.cols)
                    # save current image as well name
                    if site:
                        outpath = g.plate_dir.joinpath('TimePoint_' + str(timepoint + 1), g.plate + f'_{well_name}_s{site}_w{wavelength}.TIF')
                    else:
                        outpath = g.plate_dir.joinpath('TimePoint_' + str(timepoint + 1), g.plate + f'_{well_name}_w{wavelength}.TIF')
                    cv2.imwrite(str(outpath), individual_wells[i * cols_per_image + j])

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

# private method that extracts the column letter, row number, site number, and wavelength number from the image name
def __extract_well_name(well_string):
    # regular expression pattern to match the format
    pattern = r'_([A-Z])(\d+)(?:_s(\d+)){0,1}_w(\d+)\.TIF$'
    match = re.search(pattern, well_string)
    # check number of groups to determine site number if applicable and well number
    if match:
        # extract column letter
        letter = match.group(1)
        # extract row number
        number = match.group(2)
        site = match.group(3)
        wavelength = match.group(4)
        return letter, number, site, wavelength
    else:
        # return None if the pattern doesn't match
        return None, None, None, None

# private method that converts capital letters to numbers, where A is 0, B is 1, and so on
def __capital_to_num(alpha):
    return ord(alpha) - 65

# private method that splits image into x by y images and delete original image
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

    os.remove(img_path)
    return images

# private method that generates well name using the provided group id
def __generate_well_name(group_id, col, row, cols_per_image, rows_per_image, total_cols):
    well_id = [group_id[0] * cols_per_image + col, group_id[1] * rows_per_image + row]
    letter = chr(well_id[0] + 65)
    # if statement determines number of preceding zeroes for single digit numbered columns:
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