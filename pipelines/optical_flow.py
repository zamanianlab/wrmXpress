import cv2
import numpy as np
import os
from scipy import ndimage
from matplotlib import cm
from PIL import Image
import pandas as pd
from pathlib import Path

from pipelines.diagnostics import static_dx

def optical_flow(g, wells, well_sites, options, multiplier=2):
    # Create output and CSV directories at the start of the function
    work_dir = Path(g.work) / 'optical_flow'
    csv_out_dir = Path(g.output) / 'optical_flow'
    work_dir.mkdir(parents=True, exist_ok=True)
    csv_out_dir.mkdir(parents=True, exist_ok=True)

    wavelengths_option = options['wavelengths']  # This may be 'All' or a string like 'w1,w2'
    # Determine which wavelengths to use
    wavelengths_option = ','.join(wavelengths_option)
    if wavelengths_option == 'All':
        wavelengths = [i for i in range(g.n_waves)]  # Use all available wavelengths
    else:
        wavelengths = [int(w[1:]) - 1 for w in wavelengths_option.split(',')]

    # Loop through all wavelengths
    for wavelength in wavelengths:
        all_results = []  # List to store results for the current wavelength

        for well_site in well_sites:
            # Create empty list to store magnitude arrays
            all_mag = []
            total_mag = 0  # Initialize total_mag for each well_site

            # Read first frame
            frame1_path = Path(g.plate_dir) / f'TimePoint_1' / f'{g.plate_short}_{well_site}_w{wavelength + 1}.TIF'
            frame1 = cv2.imread(str(frame1_path), cv2.IMREAD_ANYDEPTH).astype('uint16')
            
            # Loop through all timepoints
            for timepoint in range(g.time_points - 1):
                # Get path of frame 1 and frame 2
                frame2_path = Path(g.plate_dir) / f'TimePoint_{timepoint + 2}' / f'{g.plate_short}_{well_site}_w{wavelength + 1}.TIF'
                frame2 = cv2.imread(str(frame2_path), cv2.IMREAD_ANYDEPTH).astype('uint16')

                # Calculate optical flow
                flow = cv2.calcOpticalFlowFarneback(frame1, frame2, options['flow'], options['pyrScale'], options['levels'], options['winsize'], options['iterations'], options['poly_n'], options['poly_sigma'], options['flags'])

                # Calculate magnitude of optical flow vectors
                magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)

                # Add sum of magnitude values to total_mag
                total_mag += np.sum(magnitude)

                # Store magnitude array in all_mag
                all_mag.append(magnitude)

                frame1 = frame2
            
            # Calculate total flow across the entire array
            sum_img = np.sum(all_mag, axis=0)

            # Rescaling if required
            sum_img = sum_img * multiplier
            pixel_max = np.amax(sum_img)

            # If there is not a single saturated pixel (low flow), set one to 255 in order to prevent rescaling
            if pixel_max < 255:
                print(f"Max flow is {pixel_max}. Rescaling")
                sum_img[0, 0] = 255
            # If there are saturated pixels (high flow), adjust everything > 255 to prevent rescaling
            elif pixel_max > 255:
                print(f"Max flow is {pixel_max}. Rescaling")
                sum_img[sum_img > 255] = 255
            else:
                print("Something went wrong.")

            # Apply Gaussian filter
            sum_blur = ndimage.filters.gaussian_filter(sum_img, 1.5)

            # Apply PIL colourmap
            new_im = np.asarray(sum_blur) / 255
            sum_blur_colour = Image.fromarray(np.uint8(cm.inferno(new_im) * 255))
            
            # Save flow image in 'work/optical_flow' folder
            outpath = work_dir / f'{g.plate_short}_{well_site}_w{wavelength + 1}.png'
            sum_blur_colour.save(outpath)

            # Prepare results for the current well_site and wavelength
            result = {
                'well_site': well_site,
                'optical_flow': total_mag
            }
            all_results.append(result)  # Append the result dictionary to the list

        # Create a DataFrame for the results of the current wavelength
        df = pd.DataFrame(all_results)

        # Write the DataFrame to CSV for the current wavelength
        csv_outpath = csv_out_dir / f'{g.plate}_w{wavelength + 1}.csv'
        df.to_csv(csv_outpath, index=False)

    # Run static_dx to make diagnostic image of flow images
    static_dx(g, wells,
              work_dir,
              csv_out_dir,
              None,
              wavelengths,
              rescale_factor=1,
              format='PNG')

    return total_mag
