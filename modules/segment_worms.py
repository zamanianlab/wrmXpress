import numpy as np
from datetime import datetime
import cv2
from pathlib import Path
from skimage.filters import threshold_otsu
from skimage import filters
from scipy import ndimage


def segment_worms(g, well, well_paths):
    '''
    Segments worms to use for downstream normalization.
    '''

    start_time = datetime.now()

    # sobel edge detection
    path = well_paths[0]
    image = cv2.imread(str(path), cv2.IMREAD_ANYDEPTH)
    sobel = filters.sobel(image)

    # gaussian blur
    blur = ndimage.filters.gaussian_filter(sobel, 1.5)

    # set threshold, make binary
    threshold = threshold_otsu(blur)
    binary = blur > threshold

    g.work.joinpath(g.plate, well, 'img').mkdir(
        parents=True, exist_ok=True)
    outpath = g.work.joinpath(g.plate, well, 'img')

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
