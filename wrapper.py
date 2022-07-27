import argparse
import sys
import re
import pandas as pd
import subprocess
import shlex
from pathlib import Path
from collections import defaultdict
from collections import namedtuple

sys.path.append(str(Path.home().joinpath('wrmXpress/modules')))
sys.path.append(str(Path('/Users/njwheeler/GitHub').joinpath('wrmXpress/modules')))

from get_wells import get_wells
from get_image_paths import get_image_paths
from convert_video import convert_video
from dense_flow import dense_flow
from segment_worms import segment_worms
from generate_thumbnails import generate_thumbnails
from parse_htd import parse_htd
from crop_wells import crop_wells
from parse_yaml import parse_yaml


if __name__ == "__main__":

    # create the class that will instantiate the namedtuple
    g = namedtuple(
        'g', 'input work output plate_dir plate plate_short species stages wells_per_image time_points columns rows x_sites y_sites n_waves wave_names wells plate_paths')

    ############################################
    ######### 1. GET THE YAML CONFIGS  #########
    ############################################
    arg_parser = argparse.ArgumentParser()
    g_vars, modules = parse_yaml(arg_parser, g)


    #########################################################
    ######### 2. GET THE HTD CONFIGS OR CROP WELLS  #########
    #########################################################
    if g_vars.wells_per_image == 1:
        g_vars = parse_htd(g_vars)
    else:
        crop_wells(g_vars)
        g_vars = parse_htd(g_vars)


    #########################################
    ######### 3. GET WELLS & PATHS  #########
    #########################################
    try:
        if 'All' in g_vars.wells:
            wells = get_wells(g_vars)
            plate_paths = get_image_paths(g_vars, wells)
        else:
            wells = g_vars.wells
            plate_paths = get_image_paths(g_vars, g_vars.wells)
    except TypeError:
        print("ERROR: YAML parameter \"wells\" improperly formated (or none provided) or failure to retrieve image paths.")


    # update g with wells & plate_paths and print contents (except for plate_paths)
    g_vars = g_vars._replace(wells=wells, plate_paths=plate_paths)
    for (i, j) in zip(g_vars._fields[:-1], g_vars[:-1]):
        print("{}:\t{}".format(i, j))

    ########################################
    ######### 4. RUN CELLPROFILER  #########
    ########################################

    if 'cellprofiler' in modules.keys():
        pipeline = modules['cellprofiler']['pipeline'][0]
        fl_command = 'Rscript wrmXpress/scripts/cp/generate_filelist_{}.R {} {}'.format(
            pipeline, g_vars.plate, g_vars.wells)
        fl_command_split = shlex.split(fl_command)
        print('Generating file list for CellProfiler.')
        subprocess.run(fl_command_split)

        cp_command = 'cellprofiler -c -r -p wrmXpress/cp_pipelines/pipelines/{}.cppipe --data-file=input/image_paths_{}.csv'.format(
            pipeline, pipeline)
        cp_command_split = shlex.split(cp_command)
        print('Starting CellProfiler.')
        subprocess.run(cp_command_split)

        md_command = 'Rscript wrmXpress/scripts/metadata_join_master.R {} {} {}'.format(
            g_vars.plate, g_vars.rows, g_vars.columns)
        md_command_split = shlex.split(md_command)
        print('Joining experiment metadata and tidying.')
        subprocess.run(md_command_split)

    ######################################
    ######### 5. RUN PY MODULES  #########
    ######################################

    # Each module will give a single phenotypic value, which is then written
    # out to a CSV. out_dict is a dictionary of well: [phenotype1, phenotype2, etc.]
    # that will later be converted to a DataFrame and written to a csv.
    # cols includes all the column names that will be in the output
    # DataFrame. When the modules are run below, they need to append the column
    # name to cols and the phenotypic value to out_dict['well'].

    if 'cellprofiler' not in modules.keys():
        out_dict = defaultdict(list)
        cols = []

    # start the well-by-well iterator
        for well, well_paths in zip(wells, plate_paths):
            print("Running well {}".format(well))

            if 'convert' in modules.keys():
                # get the value of reorganize and pass it to the module
                reorganize = modules.get('convert').get('save_video')
                multiplier = float(modules.get(
                    'convert').get('rescale_multiplier'))
                video = convert_video(g_vars, well, well_paths, reorganize, multiplier)
                print('{}: module \'convert\' finished'.format(well))

            if 'segment' in modules.keys():
                if g_vars.n_waves != 1:
                    wave_length = modules.get('segment').get('wavelength')
                    # filter for the paths to the wavelengths to be segmented
                    well_paths = [
                        path for path in well_paths if wave_length in str(path)]
                worm_area = segment_worms(g_vars, well, well_paths)
                if 'worm_area' not in cols:
                    cols.append('worm_area')
                out_dict[well].append(worm_area)
                print('{}: module \'segment\' finished'.format(well))

            if 'motility' in modules.keys():
                # don't use a rescaled video for flow
                video = convert_video(g_vars, well, well_paths, False, 1)
                flow = dense_flow(g_vars, well, video)
                if 'optical_flow' not in cols:
                    cols.append('optical_flow')
                out_dict[well].append(flow)
                print('{}: module \'motility\' finished'.format(well))

        ##################################
        ######### 6. WRITE DATA  #########
        ##################################

        df = pd.DataFrame.from_dict(out_dict, orient='index', columns=cols)
        g_vars.output.joinpath('data').mkdir(parents=True, exist_ok=True)
        outpath = g_vars.output.joinpath('data', g_vars.plate + '_data' + ".csv")
        df.to_csv(path_or_buf=outpath, index_label='well')

        md_command = 'Rscript wrmXpress/scripts/metadata_join_master.R {} {} {}'.format(g_vars.plate, g_vars.rows, g_vars.columns)
        md_command_split = shlex.split(md_command)
        subprocess.run(md_command_split)

    ###########################################
    ######### 7. GENERATE THUMBNAILS  #########
    ###########################################
    if 'dx' in modules.keys():
        # one for each wavelength (TimePoint1)
        # this if/else is required because of an IX nomenclature quirk:
        #   if there is only one wavelength, there is no _w1 in the file name
        #   if there is > 1, each image has _w1, _w2, etc...
        if g_vars.n_waves == 1:
            type = ''
            print("Generating w1 thumbnails")
            generate_thumbnails(g_vars, type)
        else:
            for i in range(1, g_vars.n_waves + 1):
                type = 'w' + str(i)
                print("Generating {} thumbnails".format(type))
                generate_thumbnails(g_vars, type)

        # one for each specific module
        dx_types = []
        if 'segment' in modules:
            dx_types.append('binary')
        if 'motility' in modules:
            dx_types.append('motility')
        for type in dx_types:
            print("Generating {} thumbnails".format(type))
            generate_thumbnails(g_vars, type)
