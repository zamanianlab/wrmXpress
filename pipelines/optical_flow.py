import cv2
import numpy as np
import os

def optical_flow(g, wells, options):
    total_mag = 0

    # loop through all (well, wavelength) pairings
    for well in wells:
        for wavelength in range(g.n_waves):
            # create empty list to store magnitude arrays
            all_mag = []

            # loop through all timepoints
            for timepoint in range(g.time_points - 1):
                # get path of frame 1 and frame 2
                frame1 = cv2.imread(os.path.join(g.plate_dir, f'TimePoint_{timepoint + 1}', f'{g.plate_short}_{well}_w{wavelength + 1}.TIF'))
                frame2 = cv2.imread(os.path.join(g.plate_dir, f'TimePoint_{timepoint + 2}', f'{g.plate_short}_{well}_w{wavelength + 1}.TIF'))

                # convert frames to grayscale
                frame1_gray = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
                frame2_gray = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

                # calculate optical flow
                flow = cv2.calcOpticalFlowFarneback(frame1_gray, frame2_gray, None, options['levels'], options['winsize'], options['iterations'], options['poly_n'], options['poly_sigma'], options['flow'], options['flags'])

                # calculate magnitude of optical flow vectors
                magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)

                # add sum of magnitude values to total_mag
                total_mag += np.sum(magnitude)

                # store magnitude array in all_mag
                all_mag.append(magnitude)
        
            # calculate total flow across the entire array
            sum_img = np.sum(all_mag, axis=0)

            # apply Gaussian blur
            sum_blur = cv2.GaussianBlur(sum_img.astype('uint8'), (0, 0), 1.5)

            # save flow image in 'work/optical_flow'
            out_dir = os.path.join(g.work, 'optical_flow')
            os.makedirs(out_dir, exist_ok=True)
            outpath = os.path.join(out_dir, f'{g.plate_short}_{well}_w{wavelength + 1}.png')
            cv2.imwrite(outpath, sum_blur)

    return total_mag
