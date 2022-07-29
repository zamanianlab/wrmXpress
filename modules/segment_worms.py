import numpy as np
from datetime import datetime
import cv2
from pathlib import Path
from skimage.filters import threshold_otsu
from skimage import filters
from scipy import ndimage
import matplotlib.pyplot as plt


def segment_worms(g, well, well_paths):
    '''
    Segments worms to use for downstream normalization.
    '''

    # create a disk mask for 2X images
    def create_circular_mask(h, w, center=None, radius=None):
        if center is None:  # make the center the center of the image
            center = (int(w / 2), int(h / 2))
        if radius is None:  # make the radius the size of the image
            radius = min(center[0], center[1], w - center[0], h - center[1])

        Y, X = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((X - center[0])**2 + (Y - center[1])**2)

        mask = dist_from_center <= radius
        return mask

    start_time = datetime.now()

    g.work.joinpath(g.plate, well, 'img').mkdir(
        parents=True, exist_ok=True)
    outpath = g.work.joinpath(g.plate, well, 'img')

    path = well_paths[0]
    image = cv2.imread(str(path), cv2.IMREAD_ANYDEPTH)

    if g.species == 'Sma':
        height, width = image.shape
        mask = create_circular_mask(height, width, radius=height / 2.1)

        # gaussian blur
        blur = ndimage.filters.gaussian_filter(image, 1.5)

        # set threshold, make binary
        # threshold = threshold_otsu(subtracted)
        threshold = np.percentile(blur, 1.5)
        binary = blur < threshold
        binary = binary * mask
        binary = ndimage.binary_closing(binary, iterations=5)

        # remove small segmented debris
        nb_components, labelled_image, stats, centroids = cv2.connectedComponentsWithStats(
            binary.astype('uint8'), connectivity=8)
        sizes = stats[1:, -1]
        nb_components = nb_components - 1

        # empirically derived minimum size
        min_size = 2500

        filtered = np.zeros((labelled_image.shape))
        for i in range(0, nb_components):
            if sizes[i] >= min_size:
                filtered[labelled_image == i + 1] = 255

        blur_png = g.work.joinpath(outpath,
                                   g.plate + "_" + well + '_blur' + ".png")
        cv2.imwrite(str(blur_png), blur * 255)

        bin_png = g.work.joinpath(outpath,
                                  g.plate + "_" + well + '_binary' + ".png")
        cv2.imwrite(str(bin_png), binary * 255)

        filt_png = g.work.joinpath(outpath,
                                   g.plate + "_" + well + '_binary' + ".png")
        cv2.imwrite(str(filt_png), filtered * 255)

        # the area is the sum of all the white pixels (1.0)
        area = np.sum(filtered)
        print("Completed in {}".
              format(datetime.now() - start_time))

    if g.species == 'Bma' and g.stages == 'Adult' and g.image_n_row * g.image_n_col > 1:

        frame1 = cv2.imread(str(well_paths[0]), cv2.IMREAD_ANYDEPTH)
        width, height = frame1.shape
        vid_array = np.zeros((g.time_points, height, width))

        n = 0
        for well_path in well_paths:
            frame = cv2.imread(str(well_path), cv2.IMREAD_ANYDEPTH)
            vid_array[n] = frame
            n += 1

        # subtrack background
        ave = np.mean(vid_array, axis=0)
        sub_back = frame1 - ave

        # sobel edge detection
        sobel = filters.sobel(sub_back)

        # gaussian blur
        blur = ndimage.filters.gaussian_filter(sobel, 1.25)

        # set threshold, make binary, mask
        threshold = threshold_otsu(blur)
        binary = blur > threshold
        mask = create_circular_mask(height, width, radius=height * .4)
        binary = binary * mask

        sobel_png = g.work.joinpath(outpath,
                                    g.plate + "_" + well + '_edge' + ".png")
        cv2.imwrite(str(sobel_png), sobel * 255)

        blur_png = g.work.joinpath(outpath,
                                   g.plate + "_" + well + '_blur' + ".png")
        cv2.imwrite(str(blur_png), blur * 255)

        bin_png = g.work.joinpath(outpath,
                                  g.plate + "_" + well + '_binary' + ".png")
        cv2.imwrite(str(bin_png), binary * 255)

        # the area is the sum of all the white pixels (1.0)
        area = np.sum(binary)
        print("Completed in {}".
              format(datetime.now() - start_time))

    else:

        # sobel edge detection
        sobel = filters.sobel(image)

        # gaussian blur
        blur = ndimage.filters.gaussian_filter(sobel, 1.5)

        # set threshold, make binary
        threshold = threshold_otsu(blur)
        binary = blur > threshold

        sobel_png = g.work.joinpath(outpath,
                                    g.plate + "_" + well + '_edge' + ".png")
        cv2.imwrite(str(sobel_png), sobel * 255)

        blur_png = g.work.joinpath(outpath,
                                   g.plate + "_" + well + '_blur' + ".png")
        cv2.imwrite(str(blur_png), blur * 255)

        bin_png = g.work.joinpath(outpath,
                                  g.plate + "_" + well + '_binary' + ".png")
        cv2.imwrite(str(bin_png), binary * 255)

        # the area is the sum of all the white pixels (1.0)
        area = np.sum(binary)
        print("Completed in {}".
              format(datetime.now() - start_time))

    return area
