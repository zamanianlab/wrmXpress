import sys
import cv2
from skimage.transform import rescale
from pathlib import Path
from PIL import Image
sys.path.append('/Users/njwheeler/GitHub/wrmXpress/modules')
sys.path.append(str(Path.home().joinpath('wrmXpress/modules')))

from stitch_sites import stitch_sites


def get_image_paths(g, wells):
    '''
    Create a list of lists where each internal list is all the paths to all the
    images for a given well, and the entire list is the plate.
    '''

    plate_paths = []

    for well in wells:
        well_paths = []

        # if g.x_sites * g.y_sites > 1 then there are no time points
        if g.x_sites * g.y_sites > 1:
            if g.n_waves == 1:
                for i in range(1, g.x_sites * g.y_sites + 1):
                    image_path = g.input.joinpath(g.plate, "TimePoint_1",
                                                  g.plate_short + "_" + well + '_s' + str(i) + ".TIF")
                    well_paths.append(image_path)
                print('Stitching w1 of multi-site images.')
                frame = stitch_sites(g, well_paths, 1)
                # well_paths will be regenerated with the paths to the stitched images
                well_paths = []
                g.work.joinpath(g.plate, well, 'img').mkdir(
                    parents=True, exist_ok=True)
                outpath = g.work.joinpath(g.plate, well, 'img')
                path = g.work.joinpath(outpath,
                                           g.plate + "_" + well + ".TIF")
                well_paths.append(path)
                frame.save(path)
                # also save a png for thumbnails
                # frame is a np.array
                # needs to be resized by 0.5
                resize = frame.resize((2048, 2048), resample=Image.BILINEAR)
                # converted to png
                # for now, dsave as another well_tif
                path = str(path).replace('.TIF', '.png')
                # saved
                resize.save(path, format="png")
            elif g.n_waves > 1:
                for w in range(1, g.n_waves + 1):
                    for s in range(1, g.x_sites * g.y_sites + 1):
                        image_path = g.input.joinpath(g.plate, "TimePoint_1",
                                                      g.plate_short + "_" + well + '_s' + str(s) + '_w' + str(w) + ".TIF")
                        well_paths.append(image_path)
                    print('Stitching w{} of multi-site images.'.format(w))
                    frame = stitch_sites(g, well_paths, 1)
                    well_paths = []
                    g.work.joinpath(g.plate, well, 'img').mkdir(
                        parents=True, exist_ok=True)
                    outpath = g.work.joinpath(g.plate, well, 'img')
                    well_tif = g.work.joinpath(outpath,
                                               g.plate + "_" + well + '_w' + str(w) + ".TIF")
                    well_paths.append(well_tif)
                    frame.save(well_tif)
                    # also save a png for thumbnails
                    path = str(path).replace('TIF', 'png')
                    rescaled = rescale(frame, 0.5, anti_aliasing=True, clip=False)
                    rescaled.save(path)

        else:
            for time_point in range(1, g.time_points + 1):
                # when there is only 1 wavelength, there is no 'w1' in the file name
                if g.n_waves == 1 and time_point == 1:
                    image_path = g.input.joinpath(g.plate, "TimePoint_" + str(time_point),
                                                  g.plate_short + "_" + well + ".TIF")
                    well_paths.append(image_path)
                    first_frame = cv2.imread(
                        str(image_path), cv2.IMREAD_ANYDEPTH)
                    g.work.joinpath(g.plate, well, 'img').mkdir(
                        parents=True, exist_ok=True)
                    outpath = g.work.joinpath(g.plate, well, 'img')
                    first_png = g.work.joinpath(outpath,
                                                g.plate + "_" + well + ".png")
                    try:
                        cv2.imwrite(str(first_png), first_frame)
                    except cv2.error:
                        print('{} does not exist. Please check your YAML and input to ensure all selected wells exist in the input data.'.format(well))
                        raise

                elif g.n_waves == 1 and time_point != 1:
                    image_path = g.input.joinpath(g.plate, "TimePoint_" + str(time_point),
                                                  g.plate_short + "_" + well + ".TIF")
                    well_paths.append(image_path)

                # w2, w3, etc is appened to the file name when there are multiple wavelengths
                elif g.n_waves > 1 and time_point == 1:
                    for i in range(1, g.n_waves + 1):
                        image_path = g.input.joinpath(g.plate, "TimePoint_" + str(time_point),
                                                      g.plate_short + "_" + well + '_w' + str(i) + ".TIF")
                        well_paths.append(image_path)
                        first_frame = cv2.imread(
                            str(image_path), cv2.IMREAD_ANYDEPTH)
                        g.work.joinpath(g.plate, well, 'img').mkdir(
                            parents=True, exist_ok=True)
                        outpath = g.work.joinpath(g.plate, well, 'img')
                        first_png = g.work.joinpath(outpath,
                                                    g.plate + "_" + well + '_w' + str(i) + ".png")
                        try:
                            cv2.imwrite(str(first_png), first_frame)
                        except cv2.error:
                            print('{} does not exist. Please check your YAML and input to ensure all selected wells exist in the input data.'.format(well))
                            raise

                elif g.n_waves > 1 and time_point != 1:
                    for i in range(1, g.n_waves + 1):
                        image_path = g.input.joinpath(g.plate, "TimePoint_" + str(time_point),
                                                      g.plate_short + "_" + well + '_w' + str(i) + ".TIF")
                        well_paths.append(image_path)
                else:
                    print('Something went wrong')
        plate_paths.append(well_paths)

    return plate_paths
