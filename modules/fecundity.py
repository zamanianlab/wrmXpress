import sys
import numpy as np
from datetime import datetime
import cv2
from pathlib import Path
from skimage.filters import threshold_otsu
from skimage import filters
from scipy import ndimage
import matplotlib.pyplot as plt

sys.path.append(str(Path.home().joinpath('wrmXpress/modules')))
sys.path.append(str(Path('/Users/njwheeler/GitHub').joinpath('wrmXpress/modules')))

from modules.segment_worms import create_circular_mask


def segment_progeny(g, well, well_paths):
    '''
    Segments worms to use for downstream normalization.
    '''

    start_time = datetime.now()

    g.work.joinpath(g.plate, well, 'img').mkdir(
        parents=True, exist_ok=True)
    outpath = g.work.joinpath(g.plate, well, 'img')

    path = well_paths[0]
    image = cv2.imread(str(path), cv2.IMREAD_ANYDEPTH)

    height, width = image.shape
    mask = create_circular_mask(height, width, radius=height / 2.1)

    # gaussian blur
    blur = ndimage.filters.gaussian_filter(image, 2.5)

    # edges
    sobel = filters.sobel(blur)

    # set threshold, make binary
    # threshold = threshold_otsu(subtracted)
    threshold = np.percentile(sobel, 2.5)
    binary = blur < threshold
    binary = binary * mask
    binary = ndimage.binary_fill_holes(binary)

    plt.imshow(binary, cmap='gray')
    plt.show()

    # # remove small segmented debris
    # nb_components, labelled_image, stats, centroids = cv2.connectedComponentsWithStats(
    #     binary.astype('uint8'), connectivity=8)
    # sizes = stats[1:, -1]
    # nb_components = nb_components - 1

    # # # empirically derived minimum size
    # # min_size = 2500

    # # filtered = np.zeros((labelled_image.shape))
    # # for i in range(0, nb_components):
    # #     if sizes[i] >= min_size:
    # #         filtered[labelled_image == i + 1] = 255
