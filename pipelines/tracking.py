import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
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

def tracking(g, options, well_site, video):
    """
    Tracks worm movement in a given well across multiple wavelengths and timepoints.

    Args:
        g: Namedtuple containing general experiment settings and paths.
        options: Dictionary containing configuration options.
        well_site: Well identifier to process.
        video: NumPy array representing the video frames for the well.
    """

    start_time = time.time()
    print(f'Tracking well {well_site}.')

    # Extract settings from options
    wavelengths_option = options['wavelengths']  # May be 'All' or a string like 'w1,w2'
    
    # Determine wavelengths to use
    wavelengths_option = ','.join(wavelengths_option)
    if wavelengths_option == 'All':
        wavelengths = list(range(g.n_waves))  # Use all available wavelengths
    else:
        wavelengths = [int(w[1:]) - 1 for w in wavelengths_option.split(',')]

    timepoints = range(1,2)  # timepoint 1 for testing

    # Extract dimensions
    num_frames, height, width = video.shape  # Ensure video is a 3D NumPy array

    for wavelength in wavelengths:
        for timepoint in timepoints:
            print(f'Processing timepoint {timepoint} , wavelength {wavelength + 1}')

            # Define the correct input directory
            timepoint_folder = Path(g.input) / g.plate / f"TimePoint_{timepoint + 1}"
            first_frame_path = list(timepoint_folder.glob(f"{g.plate_short}_{well_site}_w{wavelength + 1}*.TIF"))

            if not first_frame_path:
                print(f"Warning: No first frame found for timepoint {timepoint} , wavelength{wavelength + 1} in well {well_site}. Skipping.")
                continue

            first_frame = cv2.imread(str(first_frame_path[0]), cv2.IMREAD_GRAYSCALE)

            # Ensure the output directories exist
            img_output_dir = g.work.joinpath('tracking')
            img_output_dir.mkdir(parents=True, exist_ok=True)

            # Save first frame
            png_work = img_output_dir / f"{g.plate}_{well_site}_w{wavelength + 1}.png"
            cv2.imwrite(str(png_work), first_frame)

            background = np.median(video, axis=0)
            worm_array = video - background

            # Run feature finding
            # Test only: f = tp.batch(worm_array, 35, invert=True, minmass=400, processes='auto')
            # Test only: t = tp.link(f, 50, memory=50)
            f = tp.batch(worm_array, diameter=options['diameter'], invert=True, minmass=options['minmass'], noise_size=options['noisesize'], processes='auto')
            t = tp.link(f, search_range=options['searchrange'], memory=options['memory'], adaptive_stop=options['adaptivestop'])

            print(f'Plotting trajectories...')
            tracks_output_dir = g.output.joinpath('tracking')
            tracks_output_dir.mkdir(parents=True, exist_ok=True)

            track_png_work = img_output_dir / f"{g.plate}_{well_site}_w{wavelength + 1}_tracks.png"

            dpi = 300
            fig = plt.figure(figsize=(2048/dpi, 2048/dpi), dpi=dpi)
            ax = plt.gca()
            ax.set_xlim([0, width])
            ax.set_ylim([0, height])
            ax.set_aspect('equal', adjustable='box')

            # Add circular well boundary
            radius = height / 2
            circle = patches.Circle((radius, radius), radius, fill=False)
            ax.add_patch(circle)
            ax.axis('off')

            tp.plot_traj(t, ax=ax)
            fig.savefig(track_png_work)

    print(f'Tracking for well {well_site} completed in {time.time() - start_time:.2f} seconds.')

    # Save the DataFrame to CSV
    t['well_site'] = well_site # Add well_site column to the DataFrame
    t = t[['well_site'] + [col for col in t.columns if col != 'well_site']]
    tracks_csv_path = img_output_dir / f"{g.plate}_{well_site}_w{wavelength + 1}_tracks.csv"
    t.to_csv(str(tracks_csv_path), index=False)


    return wavelengths
