from pathlib import Path
import os
import cv2
import numpy as np

def avi_to_ix(g):
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

    # outpath = g.plate_dir.joinpath('TimePoint_1_test.TIF')
    # print("OUTPATH:", outpath)
    # cv2.imwrite(str(outpath), frames[0])

    for timepoint in range(timepoints):
        g.plate_dir.joinpath('TimePoint_' + str(timepoint + 1)).mkdir(parents=True, exist_ok=True)
        outpath = g.plate_dir.joinpath('TimePoint_' + str(timepoint + 1), g.plate + '_A01.TIF')
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

# def generate_well_names(coords, nrow, ncol):
#     # make a data frame with well names linked to coordinates of centers
#     # coords are in a list of tuples
#     well_names = pd.DataFrame(coords, columns=['y', 'x'])
#     well_names = well_names.sort_values(by=['y'])
#     row_names = list(ascii_uppercase[0:nrow])
#     col_names = list(range(1, ncol + 1, 1))

#     row_names_df = []
#     for name in row_names:
#         for col in range(ncol):
#             row_names_df.append(name)

#     col_names_df = []
#     for name in col_names:
#         for row in range(nrow):
#             col_names_df.append(str(name).zfill(2))

#     well_names['row'] = row_names_df
#     well_names = well_names.sort_values(by=['x'])
#     well_names['col'] = col_names_df
#     well_names['well'] = well_names['row'] + well_names['col']

#     return well_names
