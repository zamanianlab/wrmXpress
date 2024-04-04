import cv2
import numpy as np
import os

def optical_flow(g, wells, options):
    length = len(wells)
    first_image = cv2.imread(os.path.join(g.plate_dir, 'Timepoint_1', g.plate_short + f'_{wells[0]}_w1.TIF'))
    height, width = first_image.shape[:2]

    # create empty np array to store all magnitudes
    all_mag = np.zeros((length - 1, height, width))

    total_mag = 0

    # loop through all (well, wavelength pairings)
    for well in wells:
        for wavelength in range(g.n_waves):
            for timepoint in range(g.time_points - 1):
                # get path of frame 1 and frame 2
                frame1 = cv2.imread(os.path.join(g.plate_dir, f'TimePoint_{timepoint + 1}', g.plate_short + f'_{well}_w{wavelength + 1}.TIF'))
                frame2 = cv2.imread(os.path.join(g.plate_dir, f'TimePoint_{timepoint + 2}', g.plate_short + f'_{well}_w{wavelength + 1}.TIF'))

                # calculate optical flow
                # flow = cv2.calcOpticalFlowFarneback(frame1, frame2, options['pyr_scale'], options['levels'], options['winsize'], options['iterations'], options['poly_n'], options['poly_sigma'], options['flow'], options['flags'])
                flow = cv2.calcOpticalFlowFarneback(frame1, frame2, None, 0.9, 10, 2, 7, 1, 0.7, 0)

                # calculate magnitude of optical flow vectors
                magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
                # add sum of magnitude values in array to total_mag
                total_mag += np.sum(magnitude)
                # store magnitude in all_mag
                all_mag.append(magnitude)
        
            # calculate total flow across the entire array
            sum_img = np.sum(all_mag, axis=0)

            # apply Gaussian blur
            sum_blur = cv2.GaussianBlur(sum_img.astype('uint8'), (0, 0), 1.5)

            # save flow image in 'work/optical_flow'
            out_dir = os.path.join(g.work, 'optical_flow')
            os.makedirs(out_dir, exist_ok=True)
            outpath = os.join(out_dir, g.plate_short + f'_{well}_w{wavelength}.png')
            cv2.imwrite(str(outpath), sum_blur)

            return total_mag