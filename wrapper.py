import sys
import yaml
import argparse
import re
import pandas as pd
import subprocess
import shlex
from pathlib import Path
from collections import defaultdict
from collections import namedtuple

sys.path.append(str(Path.home().joinpath('wrmXpress/modules')))

from get_wells import get_wells
from get_image_paths import get_image_paths
from convert_video import convert_video
from dense_flow import dense_flow
from segment_worms import segment_worms
from generate_thumbnails import generate_thumbnails


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    # required positional arguments
    parser.add_argument('parameters',
                        help='Path to the paramaters.yml file.')
    parser.add_argument('plate',
                        help='Plate to be analyzed.')

    args = parser.parse_args()

    ######################################
    #########   GET PARAMETERS   #########
    ######################################

    # read the parameters from the YAML
    with open(args.parameters, 'rb') as f:
        # BaseLoader reads everything as a string, won't recognize boolean
        conf = yaml.load(f.read(), Loader=yaml.FullLoader)

    # read the modules, remove any where run is False
    species = conf.get('species')[0]
    stages = conf.get('stages')[0]
    modules = conf.get('modules')
    print('modules:')
    for key, value in modules.copy().items():
        if value['run'] is False:
            print("\t\t{}: {}".format(key, value['run']))
            del modules[key]
        else:
            print("\t\t{}: {}".format(key, value['run']))
    if 'cellprofiler' in modules.keys():
        for py_mod in ['segment', 'motility', 'convert']:
            if py_mod in modules.keys():
                raise ValueError(
                    "'{}' cannot be used with 'cellprofiler'".format(py_mod))

    # save the parameters in variables
    wells = conf.get('wells')  # list of wells or 'all'
    work = conf.get('directories').get('work')[0]  # string
    input = conf.get('directories').get('input')[0]  # string
    output = conf.get('directories').get('output')[0]  # string
    # plate = conf.get('directories').get('plate')[0]  # string
    plate = args.plate
    plate_short = re.sub('_[0-9]*$', '', plate)  # string

    # define directories
    input = Path.home().joinpath(input)
    work = Path.home().joinpath(work)
    output = Path.home().joinpath(output)
    plate_dir = Path.home().joinpath(input, plate)

    # HTD
    with open(plate_dir.joinpath(plate_short + '.HTD'), encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        time_points = int(
            next((s for s in lines if 'TimePoints' in s), None).split(', ')[1])
        columns = int(
            next((s for s in lines if 'XWells' in s), None).split(', ')[1])
        rows = int(
            next((s for s in lines if 'YWells' in s), None).split(', ')[1])
        x_sites = int(
            next((s for s in lines if 'XSites' in s), None).split(', ')[1])
        y_sites = int(
            next((s for s in lines if 'YSites' in s), None).split(', ')[1])
        n_waves = int(
            next((s for s in lines if 'NWavelengths' in s), None).split(', ')[1])
        # loop to get all the WaveNames
        wave_names = []
        for i in range(n_waves):
            name = 'WaveName' + str(i + 1)
            wave_name = next((s for s in lines if name in s),
                             None).split(', ')[1]
            wave_names.append(wave_name.rstrip().replace('"', ''))

    # pool global variables into namedtuple (g)
    g = namedtuple(
        'g', 'input work output plate_dir plate plate_short species stages time_points columns rows x_sites y_sites n_waves wave_names wells plate_paths')
    g = g(input, work, output, plate_dir, plate, plate_short, species, stages, time_points,
          columns, rows, x_sites, y_sites, n_waves, wave_names, wells, '')

    ######################################
    ######### GET WELLS & PATHS  #########
    ######################################

    # get the wells and well paths
    try:
        if 'All' in wells:
            wells = get_wells(g)
            plate_paths = get_image_paths(g, wells)
        else:
            plate_paths = get_image_paths(g, wells)
    except TypeError:
        print("ERROR: YAML parameter \"wells\" improperly formated (or none provided) or failure to retrieve image paths.")

    # update g with wells & plate_paths and print contents (except for plate_paths)
    g = g._replace(wells=wells, plate_paths=plate_paths)
    for (i, j) in zip(g._fields[:-1], g[:-1]):
        print("{}:\t{}".format(i, j))

    ##########################################
    #########    RUN CELLPROFILER    #########
    ##########################################

    if 'cellprofiler' in modules.keys():
        pipeline = modules['cellprofiler']['pipeline'][0]
        fl_command = 'Rscript wrmXpress/scripts/cp/generate_filelist_{}.R {} {}'.format(
            pipeline, g.plate, g.wells)
        fl_command_split = shlex.split(fl_command)
        print('Generating file list for CellProfiler.')
        subprocess.run(fl_command_split)

        cp_command = 'cellprofiler -c -r -p wrmXpress/cp_pipelines/pipelines/{}.cppipe --data-file=input/image_paths_{}.csv'.format(
            pipeline, pipeline)
        cp_command_split = shlex.split(cp_command)
        print('Starting CellProfiler.')
        subprocess.run(cp_command_split)

        md_command = 'Rscript wrmXpress/scripts/metadata_join_master.R {}'.format(
            g.plate)
        md_command_split = shlex.split(md_command)
        print('Joining experiment metadata and tidying.')
        subprocess.run(md_command_split)

    ######################################
    #########   RUN PY MODULES   #########
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
                video = convert_video(g, well, well_paths, reorganize, multiplier)
                print('{}: module \'convert\' finished'.format(well))

            if 'segment' in modules.keys():
                if n_waves != 1:
                    wave_length = modules.get('segment').get('wavelength')
                    # filter for the paths to the wavelengths to be segmented
                    well_paths = [
                        path for path in well_paths if wave_length in str(path)]
                worm_area = segment_worms(g, well, well_paths)
                if 'worm_area' not in cols:
                    cols.append('worm_area')
                out_dict[well].append(worm_area)
                print('{}: module \'segment\' finished'.format(well))

            if 'motility' in modules.keys():
                # don't use a rescaled video for flow
                video = convert_video(g, well, well_paths, False, 1)
                flow = dense_flow(g, well, video)
                if 'optical_flow' not in cols:
                    cols.append('optical_flow')
                out_dict[well].append(flow)
                print('{}: module \'motility\' finished'.format(well))

        ###############################################
        #########         WRITE DATA          #########
        ###############################################

        df = pd.DataFrame.from_dict(out_dict, orient='index', columns=cols)
        output.joinpath('data').mkdir(parents=True, exist_ok=True)
        outpath = output.joinpath('data', plate + '_data' + ".csv")
        df.to_csv(path_or_buf=outpath, index_label='well')

        md_command = 'Rscript wrmXpress/scripts/metadata_join_master.R {}'.format(g.plate)
        md_command_split = shlex.split(md_command)
        subprocess.run(md_command_split)

    ###############################################
    #########     GENERATE THUMBNAILS     #########
    ###############################################
    if 'dx' in modules.keys():
        # one for each wavelength (TimePoint1)
        # this if/else is required because of an IX nomenclature quirk:
        #   if there is only one wavelength, there is no _w1 in the file name
        #   if there is > 1, each image has _w1, _w2, etc...
        if n_waves == 1:
            type = ''
            print("Generating w1 thumbnails")
            generate_thumbnails(g, type)
        else:
            for i in range(1, n_waves + 1):
                type = 'w' + str(i)
                print("Generating {} thumbnails".format(type))
                generate_thumbnails(g, type)

        # one for each specific module
        dx_types = []
        if 'segment' in modules:
            dx_types.append('binary')
        if 'motility' in modules:
            dx_types.append('motility')
        for type in dx_types:
            print("Generating {} thumbnails".format(type))
            generate_thumbnails(g, type)
