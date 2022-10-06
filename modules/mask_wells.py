import numpy as np
from datetime import datetime
import cv2
from pathlib import Path
from skimage.filters import threshold_otsu
from skimage import filters
from scipy import ndimage
import matplotlib.pyplot as plt

# create a circular disk mask
def create_circular_mask(h, w, center=None, radius=None):
    if center is None:  # make the center the center of the image
        center = (int(w / 2), int(h / 2))
    if radius is None:  # make the radius the size of the image
        radius = min(center[0], center[1], w - center[0], h - center[1])
    Y, X = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((X - center[0])**2 + (Y - center[1])**2)
    mask = dist_from_center <= radius
    return mask