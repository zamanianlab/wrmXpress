import cv2
import numpy as np
from datetime import datetime
from pathlib import Path
from scipy import ndimage


def dense_flow(g, well, video):
    '''
    Uses Farneback's algorithm to calculate optical flow for each well. To get
    a single motility values, the magnitude of the flow is summed across each
    frame, and then again for the entire array.
    '''

    start_time = datetime.now()

    length, width, height = video.shape

    # initialize emtpy array of video length minus one (the length of the dense flow output)
    all_mag = np.zeros((length - 1, height, width))
    count = 0
    frame1 = video[count]

    while(1):
        if count < length - 1:
            frame1 = video[count].astype('uint16')
            frame2 = video[count + 1].astype('uint16')

            if g.stages == 'Adult' and g.species == 'Bma':
                flow = cv2.calcOpticalFlowFarneback(frame1, frame2, None, 0.9, 10,
                                                    2, 7, 1, 0.7, 0)
            else:
                flow = cv2.calcOpticalFlowFarneback(frame1, frame2, None, 0.5, 3,
                                                    30, 3, 5, 1.1, 0)
            mag = np.sqrt(np.square(flow[..., 0]) + np.square(flow[..., 1]))

            frame1 = frame2

            # replace proper frame with the magnitude of the flow between prvs and next frames
            all_mag[count] = mag
            count += 1

        else:
            break

    # calculate total flow across the entire array
    sum_img = np.sum(all_mag, axis=0)
    total_sum = np.sum(sum_img)

    # write out the dx flow image
    g.work.joinpath(g.plate, well, 'img').mkdir(
        parents=True, exist_ok=True)
    outpath = g.work.joinpath(g.plate, well, 'img')
    flow_png = g.work.joinpath(outpath,
                               g.plate + "_" + well + '_motility' + ".png")

    # write to png
    # the current multiplier works for 10 frame videos, not sure if it will work for others
    multiplier = 20 / g.time_points
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
    cv2.imwrite(str(flow_png), sum_blur.astype('uint8'))

    print("Optical flow = {0}. Analysis took {1}".format(
        total_sum, datetime.now() - start_time))

    return total_sum
