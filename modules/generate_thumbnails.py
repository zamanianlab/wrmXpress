import cv2
import numpy as np
from skimage.transform import rescale
from PIL import Image, ImageDraw
from matplotlib import cm


def generate_thumbnails(g, type):

    thumb_dict = {}
    for well in g.wells:
        if type == '':
            path = g.work.joinpath(g.plate, well, 'img',
                                   g.plate + '_' + well + '.png')
        else:
            path = g.work.joinpath(g.plate, well, 'img',
                                   g.plate + '_' + well + '_' + type + '.png')
        image = cv2.imread(str(path), cv2.IMREAD_ANYDEPTH)

        rescale_value = 256 / image.shape[0]
        rescaled = rescale(image, rescale_value,
                           anti_aliasing=True, clip=False)
        thumb_dict[well] = rescaled

    # normalize the color range
    max_vals = []
    for thumb in thumb_dict.values():
        max_vals.append(np.max(thumb))
    max_p = max(max_vals)
    for well, thumb in thumb_dict.items():
        thumb[0, 0] = max_p
        thumb[0, 1] = 0
        rescaled_norm = cv2.normalize(src=thumb, dst=None, alpha=0,
                                      beta=255, norm_type=cv2.NORM_MINMAX,
                                      dtype=-1)
        thumb_dict[well] = rescaled_norm

    # write out the stitched image
    # 0.125 of the 4X ImageXpress image is 256 x 256 pixels
    height = int(g.rows) * 256
    width = int(g.columns) * 256

    # new blank image with gridlines
    new_im = Image.new('L', (width, height))

    for well, thumb in thumb_dict.items():
        # row letters can be converted to integers with ord()
        # and then rescaled by subtracting a constant
        row = int(ord(well[:1]) - 64)
        col = int(well[1:].strip())
        new_im.paste(Image.fromarray(thumb),
                     ((col - 1) * 256, (row - 1) * 256))

    if type == 'motility':
        # apply a colormap if it's a flow image
        new_im = np.asarray(new_im) / 255
        new_im = Image.fromarray(np.uint8(cm.inferno(new_im) * 255))
        draw = ImageDraw.Draw(new_im)
        for col_line in range(0, width + 256, 256):
            draw.line((col_line, 0, col_line, height), fill=255, width=10)
        for row_line in range(0, height + 256, 256):
            draw.line((0, row_line, width, row_line), fill=255, width=10)
    else:
        draw = ImageDraw.Draw(new_im)
        for col_line in range(0, width + 256, 256):
            draw.line((col_line, 0, col_line, height), fill=64, width=10)
        for row_line in range(0, height + 256, 256):
            draw.line((0, row_line, width, row_line), fill=64, width=10)

    g.output.joinpath('thumbs').mkdir(
        parents=True, exist_ok=True)
    if type == '':
        outfile = g.output.joinpath('thumbs', g.plate + ".png")
    else:
        outfile = g.output.joinpath('thumbs', g.plate + '_' + type + ".png")

    new_im.save(outfile)
