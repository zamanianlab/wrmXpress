import re
from pathlib import Path
from os import walk


def get_wells(g_vars):
    '''
    Create a list with all the well names for a given plate format.
    '''

    # collect all wells from TimePoint_1 folder
    search_path = g_vars.plate_dir.joinpath('TimePoint_1')
    print(search_path)
    images = next(walk(search_path), (None, None, []))[2]
    if g_vars.n_waves == 1:
        if g_vars.x_sites and g_vars.x_sites == 1:
            wells = [file.replace(g_vars.plate_short + '_', '').replace('.TIF', '')
                     for file in images]
        else:
            wells = [file.replace(g_vars.plate_short + '_', '').replace('.TIF', '')
                     for file in images]
            wells = [re.sub('_s[0-9]*', '', well) for well in wells]
    else:
        if g_vars.x_sites and g_vars.x_sites == 1:
            wells = [file.replace(g_vars.plate_short + '_', '').replace('.TIF', '')
                     for file in images]
            wells = [re.sub('_w[0-9]', '', well) for well in wells]
        else:
            wells = [file.replace(g_vars.plate_short + '_', '').replace('.TIF', '')
                     for file in images]
            wells = [re.sub('_w[0-9]', '', well) for well in wells]
            wells = [re.sub('_s[0-9]*', '', well) for well in wells]

    # remove any .HTD file and duplicates due to multiple wavelengths
    filtered = [well for well in wells if len(well) == 3]
    filtered = list(set(filtered))

    # search for TimePoint_i folders and count up total time points
    search_path = g_vars.plate_dir
    dirs = next(walk(search_path), (None, None, []))[1]
    time_points = [int(dir.replace('TimePoint_', '')) for dir in dirs]
    time_points = max(time_points)

    # flag mismatches with HTD file
    if (len(filtered) != g_vars.rows*g_vars.columns):
        print("The number of identified wells {} does not match expectation of {} from HTD file".format(
            len(filtered), g_vars.rows*g_vars.columns))
    if (time_points != g_vars.time_points):
        print("The number of identified time points {} does not match expectation of {} from HTD file".format(
            time_points, g_vars.time_points))

    return filtered
