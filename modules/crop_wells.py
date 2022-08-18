from pathlib import Path
from string import ascii_uppercase
import cv2
import numpy as np
import pandas as pd
from scipy import ndimage
from skimage.draw import circle_perimeter
from skimage.filters import sobel, threshold_triangle
from skimage.transform import hough_circle, hough_circle_peaks
from skimage.morphology import dilation, reconstruction
from itertools import product

import matplotlib.pyplot as plt

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
        hough_res, radii, total_num_peaks=wells_per_image*2000)

    cy = np.ndarray.tolist(cy)
    cx = np.ndarray.tolist(cx)
    radii = np.ndarray.tolist(radii)

    # filter the circle centers using an auto-generated grid
    timepoint, height, width, depth = vid_array.shape

    x_interval = int(width // g.image_n_col)
    y_interval = int(height // g.image_n_row)

    grid_mask = np.ones(vid_array.shape[1:3])

    for row in range(1, g.image_n_row):
        start = y_interval * row - 80
        stop = y_interval * row + 80
        grid_mask[start:stop, :] = 0
    grid_mask[0:int(y_interval // 2), :] = 0
    grid_mask[grid_mask.shape[0] - int(y_interval // 2):grid_mask.shape[0] , :] = 0
    for col in range(1, g.image_n_col):
        start = x_interval * col - 80
        stop = x_interval * col + 80
        grid_mask[:, start:stop] = 0
    grid_mask[:, 0:int(x_interval // 2)] = 0
    grid_mask[:, grid_mask.shape[1] - int(x_interval // 2):grid_mask.shape[1]] = 0
    # plt.imshow(grid_mask)
    # plt.show()
  
    # centers of the hough transform == 1
    black = np.zeros(ave.shape[0:2])
    for center_y, center_x in zip(cy, cx):
        black[center_y, center_x] = 1
    # plt.imshow(black)
    # plt.show()
    black = black * grid_mask
    # plt.imshow(black)
    # plt.show()
    centers = tuple(zip(*np.where(black == 1)))
    for center_y, center_x, in centers:
        circy, circx = circle_perimeter(center_y, center_x, radius)
        try: 
            black[circy, circx] = 1
        except IndexError:
            pass

    closed = dilation(black)

    seed = np.copy(closed)
    seed[1:-1, 1:-1] = closed.max()
    mask = closed

    filled = reconstruction(seed, mask, method='erosion')
    # plt.imshow(filled)
    # plt.show()

    lbl, objects = ndimage.label(filled)
    centers = ndimage.center_of_mass(filled, lbl, range(
        1, 1 + wells_per_image, 1))
    
    well_names = generate_well_names(centers, g.image_n_row, g.image_n_col)

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

    create_htd(g, vid_array, well_names)

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
    timepoint, height, width, depth = vid_array.shape

    x_interval = int(width // g.image_n_col)
    y_interval = int(height // g.image_n_row)
    radius = min(x_interval, y_interval) // 2

    x_centers = [(x_interval / 2) + (x_interval * col) for col in range(g.image_n_col)]
    y_centers = [(y_interval / 2) + (y_interval * row) for row in range(g.image_n_row)]

    centers = list(product(y_centers, x_centers))

    well_names = generate_well_names(centers, g.image_n_row, g.image_n_col)

    well_arrays = {}
    for index, row, in well_names.iterrows():
        well_array = vid_array[:, int(row['y'])-radius:int(row['y'])+
            radius, int(row['x'])-radius:int(row['x'])+radius, :]
        well_arrays[row['well']] = well_array

    for timepoint in range(1, vid_array.shape[0] + 1, 1):
        g.plate_dir.joinpath(
            'TimePoint_' + str(timepoint)).mkdir(parents=True, exist_ok=True)
        for well, well_array in well_arrays.items():
            outpath = g.plate_dir.joinpath(
                'TimePoint_' + str(timepoint), g.plate + '_' + well + '.TIF')
            cv2.imwrite(str(outpath), well_array[timepoint - 1])

    g = g._replace(time_points=vid_array.shape[0])

    create_htd(g, vid_array, well_names)

def create_htd(g, array, df):

    # make HTD for non-IX data
    lines = []
    lines.append('"Description", ' + "AVI" + "\n")
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


def generate_well_names(coords, nrow, ncol):
    # make a data frame with well names linked to coordinates of centers
    # coords are in a list of tuples
    well_names = pd.DataFrame(coords, columns=['y', 'x'])
    well_names = well_names.sort_values(by=['y'])
    row_names = list(ascii_uppercase[0:nrow])
    col_names = list(range(1, ncol + 1, 1))

    row_names_df = []
    for name in row_names:
        for col in range(ncol):
            row_names_df.append(name)

    col_names_df = []
    for name in col_names:
        for row in range(nrow):
            col_names_df.append(str(name).zfill(2))

    well_names['row'] = row_names_df
    well_names = well_names.sort_values(by=['x'])
    well_names['col'] = col_names_df
    well_names['well'] = well_names['row'] + well_names['col']

    return well_names