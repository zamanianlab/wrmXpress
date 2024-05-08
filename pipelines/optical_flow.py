import cv2
import numpy as np
import os
from scipy import ndimage
from matplotlib import cm
from PIL import Image

def optical_flow(g, wells, options, multiplier=2):
    total_mag = 0

    # loop through all (well/site, wavelength) pairings
    # well or site is simply referred to as well for convenience
    for well in wells:
        for wavelength in range(g.n_waves):
            # create empty list to store magnitude arrays
            all_mag = []

            # read first frame
            frame1 = cv2.imread(os.path.join(g.plate_dir, f'TimePoint_1', f'{g.plate_short}_{well}_w{wavelength + 1}.TIF'), cv2.IMREAD_ANYDEPTH).astype('uint16')
            
            # loop through all timepoints
            for timepoint in range(g.time_points - 1):
                # get path of frame 1 and frame 2
                # frame1 = cv2.imread(os.path.join(g.plate_dir, f'TimePoint_{timepoint + 1}', f'{g.plate_short}_{well}_w{wavelength + 1}.TIF'), cv2.IMREAD_ANYDEPTH)
                frame2 = cv2.imread(os.path.join(g.plate_dir, f'TimePoint_{timepoint + 2}', f'{g.plate_short}_{well}_w{wavelength + 1}.TIF'), cv2.IMREAD_ANYDEPTH).astype('uint16')

                # convert frames to grayscale
                # frame1_gray = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
                # frame2_gray = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
                # frame1_gray = frame1.astype('uint16')
                # frame2_gray = frame2.astype('uint16')

                # calculate optical flow
                # flow = cv2.calcOpticalFlowFarneback(frame1, frame2, options['flow'], options['pyrScale'], options['levels'], options['winsize'], options['iterations'], options['poly_n'], options['poly_sigma'], options['flags'])
                flow = cv2.calcOpticalFlowFarneback(frame1, frame2, None, 0.9, 10,  2, 7, 1, 0.7, 0)

                # calculate magnitude of optical flow vectors
                magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)

                # add sum of magnitude values to total_mag
                total_mag += np.sum(magnitude)

                # store magnitude array in all_mag
                all_mag.append(magnitude)

                frame1 = frame2
        
            # calculate total flow across the entire array
            sum_img = np.sum(all_mag, axis=0)

            # NEW STUFF
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
            # sum_blur = ndimage.filters.gaussian_filter(sum_img, 30)
            # sum_blur = cv2.GaussianBlur(sum_img.astype('uint8'), (0, 0), 1.5)

            # HSV colourmap
            # flow_colour = flow_to_colour(flow, sum_blur)

            # PIL colourmap
            new_im = np.asarray(sum_blur) / 255
            sum_blur_colour = Image.fromarray(np.uint8(cm.inferno(new_im) * 255))

            # cv2 colourmap
            # im_color = cv2.applyColorMap(sum_blur, cv2.COLORMAP_INFERNO)
            
            out_dir = os.path.join(g.work, 'optical_flow')
            os.makedirs(out_dir, exist_ok=True)
            outpath = os.path.join(out_dir, f'{g.plate_short}_{well}_w{wavelength + 1}.png')

            # PIL
            sum_blur_colour.save(outpath)

            # cv2
            # cv2.imwrite(outpath, im_color.astype('uint8'))

            # HSV
            # cv2.imwrite(outpath, flow_colour)

            # # apply Gaussian blur
            # sum_blur = cv2.GaussianBlur(sum_img.astype('uint8'), (0, 0), 1.5)

            # # apply contrast stretching
            # stretched_img = contrast_stretching(sum_blur)

            # # save flow image in 'work/optical_flow'
            # out_dir = os.path.join(g.work, 'optical_flow')
            # os.makedirs(out_dir, exist_ok=True)
            # outpath = os.path.join(out_dir, f'{g.plate_short}_{well}_w{wavelength + 1}.png')
            # cv2.imwrite(outpath, stretched_img)

    return total_mag

def contrast_stretching(image):
    # Calculate minimum and maximum intensity values
    min_val = np.min(image)
    max_val = np.max(image)

    # Apply contrast stretching
    stretched_image = (image - min_val) * (255.0 / (max_val - min_val))

    # Convert to uint8 datatype
    stretched_image = stretched_image.astype(np.uint8)

    return stretched_image

def flow_to_colour(flow, sum_blur):
    # Calculate magnitude and angle of optical flow vectors
    magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])

    # Set hue based on angle (direction) of flow vectors
    hue = angle * (180 / np.pi / 2)

    # Normalize magnitude to [0, 1]
    magnitude = cv2.normalize(magnitude, None, 0, 1, cv2.NORM_MINMAX)

    # Normalize blurred sum image to [0, 1]
    sum_blur = cv2.normalize(sum_blur, None, 0, 1, cv2.NORM_MINMAX)

    # Adjust brightness of color map based on blurred sum image
    value = magnitude * sum_blur * 255

    # Convert HSV to BGR color space
    hsv = np.zeros((flow.shape[0], flow.shape[1], 3), dtype=np.uint8)
    hsv[..., 0] = hue
    hsv[..., 1] = 255
    hsv[..., 2] = value.astype(np.uint8)
    bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    return bgr