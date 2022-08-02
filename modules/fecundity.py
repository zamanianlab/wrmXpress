import numpy as np
from datetime import datetime
import cv2
from skimage import filters
from scipy import ndimage
import matplotlib.pyplot as plt


from modules.segment_worms import create_circular_mask


def fecundity(g, well, well_paths):
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
    mask = create_circular_mask(height, width, radius=height / 2.2)

    # gaussian blur
    blur = ndimage.filters.gaussian_filter(image, 2.5)

    # edges
    sobel = filters.sobel(blur)

    # set threshold, make binary, fill holes
    threshold = filters.threshold_otsu(sobel)
    binary = sobel > threshold
    binary = binary * mask

    if g.species == 'Sma':

        filled = ndimage.binary_fill_holes(binary)

        # remove small segmented debris
        nb_components, labelled_image, stats, centroids = cv2.connectedComponentsWithStats(
            filled.astype('uint8'), connectivity=8)
        sizes = stats[1:, -1]
        nb_components = nb_components - 1

        # empirically derived minimum size
        min_size = 10
        max_size = 500

        bad_indices = []
        filtered = np.zeros(labelled_image.shape)
        for i in range(0, nb_components):
            if sizes[i] >= min_size and sizes[i] <= max_size:
                filtered[labelled_image == i + 1] = 255
                nb_components -= 1
            else:
                bad_indices.append(i)

        sizes_l = list(sizes)
        filtered_sizes = [j for i, j in enumerate(
            sizes_l) if i not in bad_indices]

        fill_png = g.work.joinpath(outpath,
                                   g.plate + "_" + well + '_filled' + ".png")
        cv2.imwrite(str(fill_png), filled * 255)

        filter_png = g.work.joinpath(outpath,
                                     g.plate + "_" + well + '_filtered' + ".png")
        cv2.imwrite(str(filter_png), filtered * 255)

        fecundity_out = filtered_sizes

    else:

        area = np.sum(binary)
        
        fecundity_out = area

    blur_png = g.work.joinpath(outpath,
                               g.plate + "_" + well + '_blur' + ".png")
    cv2.imwrite(str(blur_png), blur)

    sobel_png = g.work.joinpath(outpath,
                                g.plate + "_" + well + '_edge' + ".png")
    cv2.imwrite(str(sobel_png), sobel * 255)

    bin_png = g.work.joinpath(outpath,
                              g.plate + "_" + well + '_binary' + ".png")
    cv2.imwrite(str(bin_png), binary * 255)
    
    print("Completed in {}".
          format(datetime.now() - start_time))

    return fecundity_out