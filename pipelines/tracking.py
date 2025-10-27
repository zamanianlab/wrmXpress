import matplotlib.pyplot as plt
import numpy as np
import trackpy as tp
import time
import imageio.v3 as iio
from pathlib import Path
import matplotlib.patches as patches


##################################
######### MAIN FUNCTION  #########
##################################

# Main tracking function that processes a single well and wavelength.
# It reads the image sequence for the well, normalizes images, runs Trackpy for particle/worm tracking,
# plots trajectories on a circular well boundary, and saves both PNG visualizations and CSV results.
def tracking(g, options, well_site):
    # Ensure the output directories exist
    img_output_dir = g.work.joinpath('tracking')
    img_output_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    print(f'Tracking well {well_site}.')

    # Extract settings from options
    wavelengths_option = options['wavelengths']  # May be 'All' or 'w1,w2'
    
    # Determine wavelengths to use
    wavelengths_option = ','.join(wavelengths_option)
    if wavelengths_option == 'All':
        wavelengths = list(range(g.n_waves))  # Use all available wavelengths
    else:
        wavelengths = [int(w[1:]) - 1 for w in wavelengths_option.split(',')]

    # List all timepoint folders in order
    timepoints = sorted(Path(g.input, g.plate).glob("TimePoint_*"))

    # Process each wavelength
    for wavelength in wavelengths:
        image_sequence = []  # Store images for Trackpy

        for timepoint_folder in timepoints:
            # Find image for this well site at the current timepoint
            image_path = list(timepoint_folder.glob(f"{g.plate_short}_{well_site}_w{wavelength + 1}*.TIF"))
            
            # Load image as 16-bit and normalize to 8-bit
            img = iio.imread(str(image_path[0]))
            img_8bit = (img / img.max() * 255).astype(np.uint8)

            image_sequence.append(img_8bit)

        # If no valid images, skip tracking
        if not image_sequence:
            print(f"Skipping well {well_site} for wavelength {wavelength + 1} (no images found).")
            continue
        
        # Convert list to NumPy array (frames x height x width)
        video = np.stack(image_sequence, axis=0)

        # Extract dimensions
        num_frames, height, width = video.shape

        print(f"Tracking {num_frames} frames for well {well_site}, wavelength {wavelength + 1}...")

        # Track worms using Trackpy
        f = tp.batch(video, diameter=options['diameter'], invert=True, minmass=options['minmass'], noise_size=options['noisesize'], processes='auto')
        t = tp.link(f, search_range=options['searchrange'], memory=options['memory'], adaptive_stop=options['adaptivestop'])

        print(f'Plotting trajectories...')

        # Save PNGs of the tracking results
        track_png_work = img_output_dir / f"{g.plate}_{well_site}_w{wavelength + 1}.png"

        dpi = 300
        fig = plt.figure(figsize=(2048/dpi, 2048/dpi), dpi=dpi)
        ax = plt.gca()
        ax.set_xlim([0, width])
        ax.set_ylim([0, height])
        ax.set_aspect('equal', adjustable='box')

        # Add circular well boundary for reference
        radius = height / 2
        circle = patches.Circle((radius, radius), radius, fill=False)
        ax.add_patch(circle)
        ax.axis('off')

        # Plot trajectories on the figure
        tp.plot_traj(t, ax=ax)
        fig.savefig(track_png_work)

        print(f'Tracking for well {well_site}, wavelength {wavelength + 1} completed in {time.time() - start_time:.2f} seconds.')

        # Save tracking results to CSV
        t['well_site'] = well_site  # Add well_site column
        t = t[['well_site'] + [col for col in t.columns if col != 'well_site']]
        tracks_csv_path = img_output_dir / f"{g.plate}_{well_site}_w{wavelength + 1}.csv"
        t.to_csv(str(tracks_csv_path), index=False)

    return wavelengths
