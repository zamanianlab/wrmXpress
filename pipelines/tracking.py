import cv2
import numpy as np
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import time
import pandas as pd
from pathlib import Path
import trackpy as tp


def tracking(g, wells):
    """
    Tracking pipeline function to track objects across multiple frames and save trajectory data and plots.

    Args:
        g: Namedtuple containing general experiment settings and paths.
        wells: List of wells to process.
    """
    start_time = time.time()
    print("Starting tracking pipeline.")

    # Create directories for tracking output and images
    work_dir = Path(g.work) / 'tracking'
    tracks_output_dir = Path(g.output) / 'tracking'
    img_output_dir = Path(g.output) / 'tracking' / 'img'
    work_dir.mkdir(parents=True, exist_ok=True)
    tracks_output_dir.mkdir(parents=True, exist_ok=True)
    img_output_dir.mkdir(parents=True, exist_ok=True)

    # List to store all paths to individual CSVs for combining later
    all_well_csv_paths = []

    # Loop through each well
    for well in wells:
        print(f"Processing well {well}.")

        all_trajectories = []  # Store tracking data for each timepoint
        img_paths = []  # Store paths for trajectory images

        # List to store frames for calculating background
        background_frames = []

        # Loop through each timepoint
        for timepoint in range(g.time_points):
            print(f"Processing timepoint {timepoint + 1} for well {well}.")

            # List files in the timepoint folder to find the correct wavelength
            timepoint_folder = Path(g.plate_dir) / f'TimePoint_{timepoint + 1}'
            files = list(timepoint_folder.glob(f"{g.plate_short}_{well}*.TIF"))

            # If there are multiple files, identify the one with the wavelength suffix (w1, w2, etc.)
            if files:
                for file in files:
                    file_name = file.stem
                    if '_w' in file_name:
                        wavelength_suffix = file_name.split('_w')[1]
                        break
                else:
                    raise FileNotFoundError(f"No valid wavelength suffix found for well {well} at timepoint {timepoint + 1}")
            else:
                raise FileNotFoundError(f"No TIF files found for well {well} at timepoint {timepoint + 1}")

            # Construct the frame path using the dynamic wavelength suffix
            frame_path = timepoint_folder / f'{g.plate_short}_{well}_w{wavelength_suffix}.TIF'
            frame = load_frame(frame_path)

            # Accumulate frames for background calculation (first 10 frames)
            background_frames.append(frame)

            # Initialize background after the first 10 frames
            if len(background_frames) >= 10:
                background = np.median(background_frames[:10], axis=0)
                print(f"Background min: {background.min()}, max: {background.max()}")

                # Calculate worm array by subtracting the background
                worm_array = frame - background

                # Debugging print statement for worm array values
                print(f"Worm array min: {worm_array.min()}, max: {worm_array.max()}")

                # Run feature finding and link trajectories
                features = tp.batch(worm_array, 35, invert=True, minmass=400, processes='auto')
                trajectories = tp.link(features, 50, memory=50)

                all_trajectories.append(trajectories)

        # Concatenate all timepoint trajectories into a single DataFrame
        if all_trajectories:
            all_trajectories_df = pd.concat(all_trajectories, ignore_index=True)

            # Save tracking data to CSV in the work directory for the current well
            well_csv_path = work_dir / f"{g.plate}_{well}_tracking.csv"
            all_trajectories_df.to_csv(well_csv_path, index=False)

            # Add the path of this CSV to the list for later combination
            all_well_csv_paths.append(well_csv_path)

            # Plot and save trajectories in the work directory
            trajectory_plot_path = work_dir / f"{g.plate}_{well}_tracks.png"
            plot_trajectories(all_trajectories_df, frame.shape[1], frame.shape[0], trajectory_plot_path)

            img_paths.append(str(trajectory_plot_path))  # Store the path of the plot

    # After all wells are processed, combine all well CSVs into one large DataFrame
    combined_csv = pd.concat([pd.read_csv(csv_path) for csv_path in all_well_csv_paths], ignore_index=True)

    # Save the combined CSV to the output directory
    combined_csv_path = tracks_output_dir / f"{g.plate}_all_tracking_combined.csv"
    combined_csv.to_csv(combined_csv_path, index=False)

    # After all trajectory images are saved, use static_dx to create a plate format diagnostic
    static_dx(g, wells,
              work_dir,
              tracks_output_dir,
              img_paths,
              None,
              rescale_factor=1,
              format='PNG')

    print(f"Tracking pipeline completed in {time.time() - start_time:.2f} seconds.")

def load_frame(frame_path):
    """Loads a single TIFF image into a grayscale numpy array and normalizes if necessary."""
    frame = cv2.imread(str(frame_path), cv2.IMREAD_UNCHANGED)  # Load with original bit depth
    if frame is None:
        raise FileNotFoundError(f"Could not load frame from {frame_path}")

    # Check for higher bit-depth and normalize if needed
    if frame.dtype != np.uint8:  # If not 8-bit, rescale to 0-255
        frame = cv2.normalize(frame, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    print(f"Loaded frame {frame_path}: min={frame.min()}, max={frame.max()}")
    return frame

def plot_trajectories(trajectories, width, height, trajectory_plot_path):
    """Generates and saves a plot of the trajectories."""
    dpi = 300
    fig = plt.figure(figsize=(2048 / dpi, 2048 / dpi), dpi=dpi)
    ax = plt.gca()
    ax.set_xlim([0, width])
    ax.set_ylim([0, height])
    ax.set_aspect('equal', adjustable='box')
    radius = height / 2
    circle = patches.Circle((radius, radius), radius, fill=False)
    ax.add_patch(circle)
    ax.axis('off')

    tp.plot_traj(trajectories, ax=ax)
    fig.savefig(trajectory_plot_path)
    plt.close(fig)