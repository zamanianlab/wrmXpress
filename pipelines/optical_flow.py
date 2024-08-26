import cv2
import numpy as np
import os
from scipy import ndimage
from matplotlib import cm
from PIL import Image
import csv
from pathlib import Path

from pipelines.diagnostics import static_dx

def optical_flow(g, wells, well_sites, options, multiplier=2):
    total_mag = 0
    csv_data = []

    # loop through all (well/site, wavelength) pairings
    # well or site is simply referred to as well_site for convenience
    for well_site in well_sites:
        for wavelength in range(g.n_waves):
            # create empty list to store magnitude arrays
            all_mag = []

            # read first frame
            frame1 = cv2.imread(os.path.join(g.plate_dir, f'TimePoint_1', f'{g.plate_short}_{well_site}_w{wavelength + 1}.TIF'), cv2.IMREAD_ANYDEPTH).astype('uint16')
            
            # loop through all timepoints
            for timepoint in range(g.time_points - 1):
                # get path of frame 1 and frame 2
                # frame1 = cv2.imread(os.path.join(g.plate_dir, f'TimePoint_{timepoint + 1}', f'{g.plate_short}_{well}_w{wavelength + 1}.TIF'), cv2.IMREAD_ANYDEPTH)
                frame2 = cv2.imread(os.path.join(g.plate_dir, f'TimePoint_{timepoint + 2}', f'{g.plate_short}_{well_site}_w{wavelength + 1}.TIF'), cv2.IMREAD_ANYDEPTH).astype('uint16')

                # calculate optical flow
                flow = cv2.calcOpticalFlowFarneback(frame1, frame2, options['flow'], options['pyrScale'], options['levels'], options['winsize'], options['iterations'], options['poly_n'], options['poly_sigma'], options['flags'])

                # calculate magnitude of optical flow vectors
                magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)

                # add sum of magnitude values to total_mag
                total_mag += np.sum(magnitude)

                # store magnitude array in all_mag
                all_mag.append(magnitude)

                frame1 = frame2
        
            # calculate total flow across the entire array
            sum_img = np.sum(all_mag, axis=0)

            # rescaling if required
            sum_img = sum_img * multiplier
            pixel_max = np.amax(sum_img)
            # if there is not a single saturated pixel (low flow), set one to 255 in order to prevent rescaling
            if pixel_max < 255:
                print("Max flow is {}. Rescaling".format(pixel_max))
                sum_img[0, 0] = 255
            # if there are saturated pixels (high flow), adjust everything > 255 to prevent rescaling
            elif pixel_max > 255:
                print("Max flow is {}. Rescaling".format(pixel_max))
                sum_img[sum_img > 255] = 255
            else:
                print("Something went wrong.")

            sum_blur = ndimage.filters.gaussian_filter(sum_img, 1.5)

            # apply PIL colourmap
            new_im = np.asarray(sum_blur) / 255
            sum_blur_colour = Image.fromarray(np.uint8(cm.inferno(new_im) * 255))
            
            # save flow image in 'work/optical_flow' folder
            out_dir = os.path.join(g.work, 'optical_flow')
            os.makedirs(out_dir, exist_ok=True)
            outpath = os.path.join(out_dir, f'{g.plate_short}_{well_site}_w{wavelength + 1}.png')
            sum_blur_colour.save(outpath)

            # Collect data for CSV
            csv_data.append([well_site, total_mag])

            # Create CSV file for the current wavelength inside the 'optical_flow' folder
            csv_out_dir = os.path.join(g.output, 'optical_flow')
            os.makedirs(csv_out_dir, exist_ok=True)
            csv_outpath = os.path.join(csv_out_dir, f'{g.plate}_w{wavelength + 1}.csv')
            
            # Write CSV data for the current wavelength
            with open(csv_outpath, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['well_site', 'optical_flow'])
                writer.writerows(csv_data)

    # run static_dx to make diagnostic image of flow images
    static_dx(g, wells,
                  os.path.join(g.work, 'optical_flow'),
                  os.path.join(g.output, 'optical_flow'),
                  None,
                  rescale_factor=1,
                  format='PNG')

    return total_mag