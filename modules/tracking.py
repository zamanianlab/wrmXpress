import matplotlib as mlp
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas import DataFrame, Series
import trackpy as tp
import time
import cv2
from pathlib import Path
import matplotlib.patches as patches

########################################################################
####                                                                ####
####                             tracking                           ####
####                                                                ####
########################################################################

def tracking(g, well, video):    

    start_time = time.time()
    print(f'Tracking well {well}.')

    column_names = ['y', 'x', 'mass', 'size', 'ecc', 'signal', 'raw_mass', 'ep', 'frame', 'particle', 'well']
    df = pd.DataFrame(columns=column_names)

    length, width, height = video.shape

    # Grab the first 25 frames and get the maximum projection
    first_bit = np.zeros((25, width, height))
    for i in range(0, 25):
        frame = video[i]
        first_bit[i] = frame
    max = np.amax(first_bit, axis=0)

    g.work.joinpath(g.plate, well, 'img').mkdir(
        parents=True, exist_ok=True)
    outpath = g.work.joinpath(g.plate, well, 'img')
    background_png = g.work.joinpath(outpath,
                               g.plate + "_" + well + '_background' + ".png")
    cv2.imwrite(str(background_png), max.astype('uint8'))

    # Initialize array - first argument should be the number of frames you're going to use
    test_vid = np.zeros((50, width, height))

    # Grab and background subtract frames
    frames = np.array([video[i] for i in range(test_vid.shape[0])])
    test_vid = frames - max

    # Run feature finding
    num_frames = len(video)
    f = tp.batch(test_vid, 49, invert=True, minmass=500, processes='auto')
    t = tp.link(f, 150, memory=50)
    # t1 = tp.filter_stubs(t, 15)

    print('Plotting trajectories.')
    g.output.joinpath('tracks').mkdir(
        parents=True, exist_ok=True)
    outpath = g.output.joinpath('tracks')
    track_pdf = g.output.joinpath(outpath,
                                  g.plate + "_" + well + "_tracks.pdf")
    fig = plt.figure()
    ax = plt.gca()
    ax.set_xlim([0, width])  
    ax.set_ylim([0, height])
    ax.set_aspect('equal', adjustable='box')
    radius = height / 2
    circle = patches.Circle((radius, radius), radius, fill=False)  # replace x, y, radius with actual values
    ax.add_patch(circle)

    tp.plot_traj(t, ax=ax)
    fig.savefig(track_pdf)

    # DataFrame sorting
    t2 = t.drop(index=0) 
    t2['new_column'] = well  # Change this with the real well name later
    
    # Concatenate new data with existing DataFrame
    df2 = pd.concat([df, t2], ignore_index=True)

    return df2
