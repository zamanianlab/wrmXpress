from pathlib import Path
from string import ascii_uppercase
import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import ndimage
from scipy.ndimage import sum as ndi_sum
from skimage.draw import circle_perimeter
from skimage.filters import sobel, threshold_triangle
from skimage.transform import hough_circle, hough_circle_peaks
from skimage.morphology import dilation, reconstruction


def auto_crop(g):
    ''' 
    Use Hough transform to find and crop circular wells
    '''
    wells_per_image = g.image_n_row * g.image_n_col

    vid_path = Path.home().joinpath(g.plate_dir, g.plate + '.avi')

    vid = cv2.VideoCapture(str(vid_path))
    ret = True
    frames = []
    while ret:
        ret, img = vid.read()
        if ret:
            frames.append(img)

    vid_array = np.stack(frames, axis=0)
    ave = np.mean(vid_array, axis=0)
    ave_int = ave.astype(int)

    gry = cv2.cvtColor(ave.astype(np.float32), cv2.COLOR_BGR2GRAY)

    edges = sobel(gry)

    thresh = threshold_triangle(edges)
    binary = edges > thresh

    # emperically derived well radii
    if wells_per_image == 24:
        radius = 73
    elif wells_per_image == 96:
        radius = 23

    radii = np.arange(radius - 2, radius + 2, 2)
    hough_res = hough_circle(binary, radii)
    accums, cx, cy, radii = hough_circle_peaks(
        hough_res, radii, total_num_peaks=500)

    cy = np.ndarray.tolist(cy)
    cx = np.ndarray.tolist(cx)
    radii = np.ndarray.tolist(radii)

    bad_indices = []
    i = 0

    for x, y in zip(cx, cy):
        if x < 100:
            bad_indices.append(i)
        elif x > 200 and x < 300:
            bad_indices.append(i)
        elif x > 400 and x < 500:
            bad_indices.append(i)
        elif x > 600 and x < 700:
            bad_indices.append(i)
        elif x > 800 and x < 900:
            bad_indices.append(i)
        elif x > 1000 and x < 1100:
            bad_indices.append(i)
        elif x > 1200:
            bad_indices.append(i)
        elif y < 100:
            bad_indices.append(i)
        elif y > 200 and y < 300:
            bad_indices.append(i)
        elif y > 400 and y < 500:
            bad_indices.append(i)
        elif y > 600 and y < 700:
            bad_indices.append(i)
        elif y > 800:
            bad_indices.append(i)
        else:
            i += 1

    for i in bad_indices:
        cy.pop(i)
        cx.pop(i)
        radii.pop(i)

    ave_int = ave.astype(int)

    fig, ax = plt.subplots(ncols=1, nrows=1)
    for center_y, center_x, radius in zip(cy, cx, radii):
        circy, circx = circle_perimeter(center_y, center_x, radius)

    black = np.zeros(ave_int.shape[0:2])

    for center_y, center_x, radius in zip(cy, cx, radii):
        circy, circx = circle_perimeter(center_y, center_x, radius)
        black[circy, circx] = 1

    closed = dilation(black)

    seed = np.copy(closed)
    seed[1:-1, 1:-1] = closed.max()
    mask = closed

    filled = reconstruction(seed, mask, method='erosion')

    lbl, objects = ndimage.label(filled)
    centers = ndimage.center_of_mass(filled, lbl, range(
        1, 1 + wells_per_image, 1))

    # make a data frame with well names linked to coordinates of centers
    well_names = pd.DataFrame(centers, columns=['y', 'x'])
    well_names = well_names.sort_values(by=['y'])
    row_names = list(ascii_uppercase[0:g.image_n_row])
    col_names = list(range(1, g.image_n_col + 1, 1))

    row_names_df = []
    for name in row_names:
        for col in range(g.image_n_col):
            row_names_df.append(name)

    col_names_df = []
    for name in col_names:
        for row in range(g.image_n_row):
            col_names_df.append(str(name).zfill(2))

    well_names['row'] = row_names_df
    well_names = well_names.sort_values(by=['x'])
    well_names['col'] = col_names_df
    well_names['well'] = well_names['row'] + well_names['col']

    well_arrays = {}
    for index, row, in well_names.iterrows():
        well_array = vid_array[:, int(row['y'])-(radius + 10):int(row['y'])+(
            radius + 10), int(row['x'])-(radius + 10):int(row['x'])+(radius + 10), :]
        well_arrays[row['well']] = well_array

    for timepoint in range(1, vid_array.shape[0] + 1, 1):
        g.plate_dir.joinpath(
            'TimePoint_' + str(timepoint)).mkdir(parents=True, exist_ok=True)
        for well, well_array in well_arrays.items():
            outpath = g.plate_dir.joinpath(
                'TimePoint_' + str(timepoint), g.plate + '_' + well + '.TIF')
            cv2.imwrite(str(outpath), well_array[timepoint - 1])

    g = g._replace(time_points=vid_array.shape[0])

    create_htd(vid_array, well_names)

    return g


def grid_crop(g):
    ''' 
    Crop wells based on the image size and number of wells
    '''
    wells_per_image = g.image_n_row * g.image_n_col

    vid_path = Path.home().joinpath(g.plate_dir, g.plate + '.avi')

    vid = cv2.VideoCapture(str(vid_path))
    ret = True
    frames = []
    while ret:
        ret, img = vid.read()
        if ret:
            frames.append(img)

    vid_array = np.stack(frames, axis=0)
    timepoint, height, width = vid_array.shape

    x_interval = width / g.image_n_row
    y_interval = height / g.image_n_col


    create_htd(vid_array, well_names)


def create_htd(array, df):

    # make HTD for non-IX data
    lines = []
    lines.append('"TimePoints", ' + str(array.shape[0]) + "\n")
    lines.append('"XWells", ' + str(len(pd.unique(df['col']))) + "\n")
    lines.append('"YWells", ' + str(len(pd.unique(df['row']))) + "\n")
    lines.append('"XSites", ' + "1" + "\n")
    lines.append('"YSites", ' + "1" + "\n")
    lines.append('"NWavelengths", ' + "1" + "\n")
    lines.append('"WaveName1", ' + '"Transmitted Light"' + "\n")

    htd_path = g.plate_dir.joinpath(g.plate_short + '.HTD')
    with open(htd_path, mode='w') as htd_file:
        htd_file.writelines(lines)
