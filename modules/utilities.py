from pathlib import Path
import os
import cv2
import numpy as np
import shutil
import re

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

    create_htd(g, timepoints)

    return timepoints

def create_htd(g, timepoints):

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

# split image into x by y images and delete original image
def split_image(img_path, x, y):
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

# checks and adds '_w1' at the end of all filenames within the given directory if it doesn't already exist
def rename_files(g):
    for timepoint in range(g.time_points):
        images = os.listdir(g.plate_dir.joinpath('TimePoint_' + str(timepoint + 1)))
        for current in images:
            current_path = os.path.join(g.plate_dir, 'TimePoint_' + str(timepoint + 1), current)
            if re.search(r'_w1\.TIF$', current_path, re.IGNORECASE):
                continue
            outpath = current_path[:-4] + '_w1.TIF'
            os.rename(current_path, outpath)
