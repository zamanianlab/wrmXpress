import cv2
from PIL import Image
import numpy as np


def stitch_sites(g, well_paths, multiplier):

    panel_size = int(2048 - (2048 / 10))

    height = int(g.y_sites * panel_size)
    width = int(g.x_sites * panel_size)

    new_im = Image.new('I', (height, width))
    for site_path in well_paths:
        site_image = cv2.imread(
                     str(site_path), cv2.IMREAD_ANYDEPTH)
        if any(substring in str(site_path) for substring in ['_s1.TIF', '_s1_']):
            new_im.paste(Image.fromarray(site_image), (0, 0))
        elif any(substring in str(site_path) for substring in ['_s2.TIF', '_s2_']):
            new_im.paste(Image.fromarray(site_image), (panel_size, 0))
        elif any(substring in str(site_path) for substring in ['_s3.TIF', '_s3_']):
            new_im.paste(Image.fromarray(site_image), (0, panel_size))
        elif any(substring in str(site_path) for substring in ['_s4.TIF', '_s4_']):
            new_im.paste(Image.fromarray(site_image), (panel_size, panel_size))

    new_height = int(height * multiplier)
    new_width = int(width * multiplier)
    resize = new_im.resize((new_height, new_width), resample=Image.BILINEAR)

    return resize
