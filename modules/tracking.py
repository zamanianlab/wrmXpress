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

    length, width, height = video.shape

    print('Generating background.')
    background = np.median(video, axis=0)
    worm_array = video - background

    # Run feature finding
    f = tp.batch(worm_array, 35, invert=True, minmass=400, processes='auto')
    t = tp.link(f, 50, memory=50)

    print('Plotting trajectories.')
    g.output.joinpath('tracks').mkdir(
        parents=True, exist_ok=True)
    outpath = g.output.joinpath('tracks')
    workpath = g.work.joinpath(g.plate, well, 'img')
    track_png_out = g.output.joinpath(outpath,
                                  g.plate + "_" + well + "_tracks.png")
    track_png_work = g.work.joinpath(workpath,
                               g.plate + "_" + well + '_tracks.png')
    dpi = 300
    fig = plt.figure(figsize=(2048/dpi, 2048/dpi), dpi=dpi)
    ax = plt.gca()
    ax.set_xlim([0, width])  
    ax.set_ylim([0, height])
    ax.set_aspect('equal', adjustable='box')
    radius = height / 2
    circle = patches.Circle((radius, radius), radius, fill=False)
    ax.add_patch(circle)
    ax.axis('off')

    tp.plot_traj(t, ax=ax)
    fig.savefig(track_png_out)
    fig.savefig(track_png_work)

    return t
