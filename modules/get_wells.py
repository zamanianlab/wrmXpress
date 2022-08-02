import re
from os import walk


def get_wells(g):
    '''
    Create a list with all the well names for a given plate format.
    '''

    # collect all wells from TimePoint_1 folder
    search_path = g.plate_dir.joinpath('TimePoint_1')
    images = next(walk(search_path), (None, None, []))[2]
    if g.n_waves == 1:
        if g.x_sites and g.x_sites == 1 and "Montage" not in g.desc:
            wells = [file.replace(g.plate_short + '_', '').replace('.TIF', '')
                     for file in images]
        elif g.x_sites and g.x_sites == 1 and "Montage" in g.desc:
            wells = [file.replace(g.plate_short + '_', '') for file in images]
            wells = [well.replace('_w1', '').replace('.tif', '') for well in wells]
        else:
            wells = [file.replace(g.plate_short + '_', '').replace('.TIF', '')
                     for file in images]
            wells = [re.sub('_s[0-9]*', '', well) for well in wells]
    else:
        if g.x_sites and g.x_sites == 1:
            wells = [file.replace(g.plate_short + '_', '').replace('.TIF', '')
                     for file in images]
            wells = [re.sub('_w[0-9]', '', well) for well in wells]
        else:
            wells = [file.replace(g.plate_short + '_', '').replace('.TIF', '')
                     for file in images]
            wells = [re.sub('_w[0-9]', '', well) for well in wells]
            wells = [re.sub('_s[0-9]*', '', well) for well in wells]

    # remove any .HTD file and duplicates due to multiple wavelengths
    filtered = [well for well in wells if len(well) == 3]
    filtered = list(set(filtered))

    # search for TimePoint_i folders and count up total time points
    search_path = g.plate_dir
    dirs = next(walk(search_path), (None, None, []))[1]
    time_points = [int(dir.replace('TimePoint_', '')) for dir in dirs]
    time_points = max(time_points)

    # flag mismatches with HTD file
    if (len(filtered) != g.rows*g.columns):
        print("The number of identified wells {} does not match expectation of {} from HTD file".format(
            len(filtered), g.rows*g.columns))
    if (time_points != g.time_points):
        print("The number of identified time points {} does not match expectation of {} from HTD file".format(
            time_points, g.time_points))

    return filtered
