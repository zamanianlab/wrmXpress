########################################################################
####                                                                ####
####                             Imports                            ####
####                                                                ####
########################################################################

import matplotlib as mlp
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas import DataFrame, Series
import trackpy as tp
import time
import os

########################################################################
####                                                                ####
####                          create sheet                          ####
####                                                                ####
########################################################################

column_names = ['y', 'x', 'mass', 'size', 'ecc', 'signal', 'raw_mass', 'ep', 'frame', 'particle', 'well']
df = pd.DataFrame(columns=column_names)

########################################################################
####                                                                ####
####                             tracking                           ####
####                                                                ####
########################################################################

def tracking(g, video, df):    

    start_time = time.time()

    length, width, height = video.shape

    # Grab the first 25 frames and get the maximum projection
    first_bit = np.zeros((25, width, height))
    for i in range(0, 25):
        frame = video[i]
        first_bit[i] = frame
    max = np.amax(first_bit, axis=0)

    # Initialize array - first argument should be the number of frames you're going to use
    test_vid = np.zeros((50, width, height))

    # Grab, crop, and background subtract frames
    frames = np.array([video[i] for i in range(test_vid.shape[0])])
    test_vid = frames - max

    # Run feature finding
    num_frames = len(video)
    f = tp.batch(test_vid, num_frames, invert=True, minmass=1300, processes='auto')
    t = tp.link(f, 15, memory=50)
    t1 = tp.filter_stubs(t, 15)

    # DataFrame sorting
    t2 = t1.drop(index=0) 
    t2['new_column'] = g.well  # Change this with the real well name later
    
    # Concatenate new data with existing DataFrame
    df = pd.concat([df, t2], ignore_index=True)

    return df
