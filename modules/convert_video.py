import cv2
import numpy as np
from skimage.transform import rescale
from pathlib import Path
from modules.crop_wells import create_htd


def convert_video(g, well, well_paths, reorganize, multiplier):

    # check if AVI already exists
    vid_path = g.input.joinpath(g.plate_dir, g.plate + "_" + well + '.avi')

    if vid_path.exists():

        print(f'AVI exists at {vid_path}')
        vid = cv2.VideoCapture(str(vid_path))
        ret = True
        frames = []
        while ret:
            ret, img = vid.read()
            if ret:
                img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                frames.append(img_gray)

        well_video = np.stack(frames, axis=0)

        create_htd(g, well_video)

        return well_video
    
    else:

        print(f'Converting well {well} to AVI.')
        # get the first image of the video
        first_image = cv2.imread(str(well_paths[0]), cv2.IMREAD_ANYDEPTH)

        # initialize an array with the correct shape of the final array
        height, width = first_image.shape
        well_video = np.zeros((g.time_points, height, width))

        # read images from well_paths
        # print("Reading images for well {}".format(well))
        counter = 0
        for time_point in well_paths:
            # print("Reading Timepoint_{}".format(counter + 1))
            image = cv2.imread(str(time_point), cv2.IMREAD_ANYDEPTH)
            well_video[counter] = image

            if reorganize:
                timepoint = str(counter + 1).zfill(2)
                g.output.joinpath('vid', well).mkdir(
                    parents=True, exist_ok=True)
                outpath = g.output.joinpath(
                    'vid', well,
                    g.plate + "_" + well + "_" + timepoint + ".TIF")
                if multiplier != 1:
                    # rescale the image with anti-aliasing
                    rescaled = rescale(image, multiplier, anti_aliasing=True, clip=False).astype(np.uint16)
                    try:
                        cv2.imwrite(str(outpath), rescaled)
                    except cv2.error:
                        print('TimePoint_{} does not exist. Please ensure the TimePoints field in the HTD is the same as the number of TimePoints included in input/.'.format(timepoint))
                        raise
                else:
                    try:
                        cv2.imwrite(str(outpath), image)
                    except cv2.error:
                        print('TimePoint_{} does not exist. Please ensure the TimePoints field in the HTD is the same as the number of TimePoints included in input/.'.format(timepoint))
                        raise
            counter += 1

        return well_video
