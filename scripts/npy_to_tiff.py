import glob
import numpy
from skimage import io

# Execute in folder with .npy files
for fn in glob.glob("*_seg.npy"):
    base_fn = fn[:-8]
    out_prob = base_fn + "_cellprob.tif"
    out_xy = base_fn + "_flowxy.tif"
    
    # load data from .npy
    npy = numpy.load(fn, allow_pickle=True)

    # convert masks to uint16 (be sure you have less than 2^16 - 1 segments)
    cellprobs = npy[()]['flows'][1].astype("uint16")
    xy = npy[()]['flows'][0]
    
    # save using skimage.io
    io.imsave(out_prob, cellprobs)
    io.imsave(out_xy, xy)
