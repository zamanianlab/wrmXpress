import argparse
import sys
import re
import pandas as pd
import subprocess
import shlex
from pathlib import Path
from collections import defaultdict
from collections import namedtuple

# sys.path.append(str(Path.home().joinpath('wrmXpress/modules')))

from modules.parse_yaml import parse_yaml
from modules.parse_htd import parse_htd
from modules.get_wells import get_wells
from modules.get_image_paths import get_image_paths
from modules.convert_video import convert_video
from modules.dense_flow import dense_flow
from modules.segment_worms import segment_worms
from modules.generate_thumbnails import generate_thumbnails
from modules.parse_htd import parse_htd
from modules.crop_wells import auto_crop, grid_crop
from modules.parse_yaml import parse_yaml
from modules.fecundity import segment_progeny


if __name__ == "__main__":

    # create the class that will instantiate the namedtuple
    g_class = namedtuple(
        'g_class', 'mode file_structure well_detection image_n_row image_n_col species stages input work output plate_dir plate plate_short time_points columns rows x_sites y_sites n_waves wave_names wells plate_paths')

    ############################################
    ######### 1. GET THE YAML CONFIGS  #########
    ############################################
    arg_parser = argparse.ArgumentParser()
    g, modules = parse_yaml(arg_parser, g_class)


    #########################################################
    ######### 2. GET THE HTD CONFIGS OR CROP WELLS  #########
    #########################################################
    if g.file_structure == 'imagexpress':
        g = parse_htd(g, g_class)
    else:
         # crops_wells will write images in IX format to input/ and create an HTD
        if g.well_detection == 'auto':
            auto_crop(g)
        elif g.well_detection == 'grid':
            grid_crop(g)
        else:
            raise ValueError('Incompatible well detection mode selected (or none selected with multi-well mode.')
        g = parse_htd(g, g_class)


    #########################################
    ######### 3. GET WELLS & PATHS  #########
    #########################################
    # try:
    #     if 'All' in g.wells:
    #         wells = get_wells(g)
    #         plate_paths = get_image_paths(g, wells)
    #     else:
    #         wells = g.wells
    #         plate_paths = get_image_paths(g, g.wells)
    # except TypeError:
    #     print("ERROR: YAML parameter \"wells\" improperly formated (or none provided) or failure to retrieve image paths.")


    # # update g with wells & plate_paths and print contents (except for plate_paths)
    # g = g._replace(wells=wells, plate_paths=plate_paths)
    # for (i, j) in zip(g._fields[:-1], g[:-1]):
    #     print("{}:\t{}".format(i, j))

    # ########################################
    # ######### 4. RUN CELLPROFILER  #########
    # ########################################

    # if 'cellprofiler' in modules.keys():
    #     pipeline = modules['cellprofiler']['pipeline'][0]
    #     fl_command = 'Rscript wrmXpress/scripts/cp/generate_filelist_{}.R {} {}'.format(
    #         pipeline, g.plate, g.wells)
    #     fl_command_split = shlex.split(fl_command)
    #     print('Generating file list for CellProfiler.')
    #     subprocess.run(fl_command_split)

    #     cp_command = 'cellprofiler -c -r -p wrmXpress/cp_pipelines/pipelines/{}.cppipe --data-file=input/image_paths_{}.csv'.format(
    #         pipeline, pipeline)
    #     cp_command_split = shlex.split(cp_command)
    #     print('Starting CellProfiler.')
    #     subprocess.run(cp_command_split)

    #     md_command = 'Rscript wrmXpress/scripts/metadata_join_master.R {} {} {}'.format(
    #         g.plate, g.rows, g.columns)
    #     md_command_split = shlex.split(md_command)
    #     print('Joining experiment metadata and tidying.')
    #     subprocess.run(md_command_split)

    # ######################################
    # ######### 5. RUN PY MODULES  #########
    # ######################################

    # # Each module will give a single phenotypic value, which is then written
    # # out to a CSV. out_dict is a dictionary of well: [phenotype1, phenotype2, etc.]
    # # that will later be converted to a DataFrame and written to a csv.
    # # cols includes all the column names that will be in the output
    # # DataFrame. When the modules are run below, they need to append the column
    # # name to cols and the phenotypic value to out_dict['well'].

    # if 'cellprofiler' not in modules.keys():
    #     out_dict = defaultdict(list)
    #     cols = []

    # # start the well-by-well iterator
    #     for well, well_paths in zip(wells, plate_paths):
    #         print("Running well {}".format(well))

    #         if 'convert' in modules.keys():
    #             # get the value of reorganize and pass it to the module
    #             reorganize = modules.get('convert').get('save_video')
    #             multiplier = float(modules.get(
    #                 'convert').get('rescale_multiplier'))
    #             video = convert_video(g, well, well_paths, reorganize, multiplier)
    #             print('{}: module \'convert\' finished'.format(well))

    #         if 'segment' in modules.keys():
    #             if g.n_waves != 1:
    #                 wave_length = modules.get('segment').get('wavelength')
    #                 # filter for the paths to the wavelengths to be segmented
    #                 well_paths = [
    #                     path for path in well_paths if wave_length in str(path)]
    #             worm_area = segment_worms(g, well, well_paths)
    #             if 'worm_area' not in cols:
    #                 cols.append('worm_area')
    #             out_dict[well].append(worm_area)
    #             print('{}: module \'segment\' finished'.format(well))

    #         if 'motility' in modules.keys():
    #             # don't use a rescaled video for flow
    #             video = convert_video(g, well, well_paths, False, 1)
    #             flow = dense_flow(g, well, video)
    #             if 'optical_flow' not in cols:
    #                 cols.append('optical_flow')
    #             out_dict[well].append(flow)
    #             print('{}: module \'motility\' finished'.format(well))

    #         if 'fecundity' in modules.keys():
    #             progeny_area = fecundity(g, well, well_paths)
    #             if 'progeny_area' not in cols:
    #                 cols.append('progeny_area')
    #             out_dict[well].append(progeny_area)
    #             print('{}: module \'fecundity\' finished'.format(well))

    #     ##################################
    #     ######### 6. WRITE DATA  #########
    #     ##################################

    #     df = pd.DataFrame.from_dict(out_dict, orient='index', columns=cols)
    #     g.output.joinpath('data').mkdir(parents=True, exist_ok=True)
    #     outpath = g.output.joinpath('data', g.plate + '_data' + ".csv")
    #     df.to_csv(path_or_buf=outpath, index_label='well')

    #     md_command = 'Rscript wrmXpress/scripts/metadata_join_master.R {} {} {}'.format(g.plate, g.rows, g.columns)
    #     md_command_split = shlex.split(md_command)
    #     subprocess.run(md_command_split)

    # ###########################################
    # ######### 7. GENERATE THUMBNAILS  #########
    # ###########################################
    # if 'dx' in modules.keys():
    #     # one for each wavelength (TimePoint1)
    #     # this if/else is required because of an IX nomenclature quirk:
    #     #   if there is only one wavelength, there is no _w1 in the file name
    #     #   if there is > 1, each image has _w1, _w2, etc...
    #     if g.n_waves == 1:
    #         type = ''
    #         print("Generating w1 thumbnails")
    #         generate_thumbnails(g, type)
    #     else:
    #         for i in range(1, g.n_waves + 1):
    #             type = 'w' + str(i)
    #             print("Generating {} thumbnails".format(type))
    #             generate_thumbnails(g, type)

    #     # one for each specific module
    #     dx_types = []
    #     if 'segment' in modules:
    #         dx_types.append('binary')
    #     if 'motility' in modules:
    #         dx_types.append('motility')
    #     for type in dx_types:
    #         print("Generating {} thumbnails".format(type))
    #         generate_thumbnails(g, type)
