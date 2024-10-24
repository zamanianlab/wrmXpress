import yaml
import os
import re
from pathlib import Path

from preprocessing.image_processing import well_idx_to_name

# parses yaml
def parse_yaml(arg_parser, g_class):

    # required positional arguments
    arg_parser.add_argument('parameters',
                            help='Path to the parameters.yml file.')
    arg_parser.add_argument('plate',
                            help='Plate to be analyzed.')

    args = arg_parser.parse_args()

    ######################################
    #########   GET PARAMETERS   #########
    ######################################

    # read the parameters from the YAML
    with open(args.parameters, 'rb') as f:
        # BaseLoader reads everything as a string, won't recognize boolean
        conf = yaml.load(f.read(), Loader=yaml.FullLoader)

    # instrument settings
    file_structure = conf.get('file_structure')[0]
    mode = conf.get('imaging_mode')[0]
    print('instrument settings:')
    print("\t\timaging mode: {}".format(mode))
    print("\t\tfile structure: {}".format(file_structure))
    # physical plate dimensions
    rows = int(conf.get('well-row'))
    cols = int(conf.get('well-col'))
    if mode == 'multi-well':
        crop = conf.get('multi-well-detection')
        rec_rows = int(conf.get('multi-well-row'))
        rec_cols = int(conf.get('multi-well-col'))
        image_n_row = rows/rec_rows
        image_n_col = cols/rec_cols
    else:
        crop = 'NA'
        rec_rows = rows
        rec_cols = cols
        image_n_row = 'NA'
        image_n_col = 'NA'
    if mode == 'multi-site':
        x_sites = int(conf.get('x-sites'))
        y_sites = int(conf.get('y-sites'))
        stitch = conf.get('stitch')
    else:
        x_sites = 'NA'
        y_sites = 'NA'
        stitch = False
    print(f"\t\trows: {rows}")
    print(f"\t\tcolumns: {cols}")
    print(f"\t\tcrop: {crop}")
    print(f"\t\twell rows per image: {image_n_row}")
    print(f"\t\twell columns per image: {image_n_col}")
    print(f"\t\trecorded rows: {rec_rows}")
    print(f"\t\trecorded cols: {rec_cols}")
    print(f"\t\tx-sites: {x_sites}")
    print(f"\t\ty-sites: {y_sites}")

    # read the pipelines, remove any where run is False
    pipelines = conf.get('pipelines')
    print('pipelines:')
    for key, value in pipelines.copy().items():
        if value['run'] is False:
            print("\t\t{}: {}".format(key, value['run']))
            del pipelines[key]
        else:
            print("\t\t{}: {}".format(key, value['run']))
    # if 'cellprofiler' in modules.keys():
    #     for py_mod in ['segment', 'motility', 'convert']:
    #         if py_mod in modules.keys():
    #             raise ValueError(
    #                 "'{}' cannot be used with 'cellprofiler'".format(py_mod))

    # run-time settings
    wells = conf.get('wells')
    work = conf.get('directories').get('work')[0]
    input = conf.get('directories').get('input')[0]
    output = conf.get('directories').get('output')[0]
    plate = args.plate
    plate_short = re.sub('_[0-9]*$', '', plate)
    print('run-time settings:')
    print("\t\twells: {}".format(wells))
    print("\t\tplate: {}".format(plate))

    # define directories
    input = Path.home().joinpath(input)
    work = Path.home().joinpath(work)
    output = Path.home().joinpath(output)
    plate_dir = Path.home().joinpath(input, plate)
    print("\t\tinput directory: {}".format(str(input)))
    print("\t\twork directory: {}".format(str(work)))
    print("\t\toutput directory: {}".format(str(output)))

    # add masks (could have mask field which is 'circle', 'square', or 'NA')
    circle_diameter = conf.get('circle_diameter')
    square_side = conf.get('square_side')
    if circle_diameter != 'NA' and square_side != 'NA':
        raise ValueError("Cannot apply circle mask and square mask at the same time.")
    
    yaml_out = g_class(file_structure, mode, rows, cols, rec_rows, rec_cols,
                       crop, x_sites, y_sites, stitch, input, work, output,
                       plate_dir, plate, plate_short, wells,
                       circle_diameter, square_side,
                       '', '', '', '', '')

    return yaml_out, pipelines

# parses HTD
def parse_htd(yaml, g_class):
    '''
    Parse an HTD file and return experimental metadata as variables.
    '''

    # HTD
    with open(yaml.plate_dir.joinpath(yaml.plate_short + '.HTD'), encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        desc = str(next((s for s in lines if 'Description' in s), None).split(', ')[1])
        time_points = int(
            next((s for s in lines if 'TimePoints' in s), None).split(', ')[1])
        rows = int(
            next((s for s in lines if 'YWells' in s), None).split(', ')[1])
        cols = int(
            next((s for s in lines if 'XWells' in s), None).split(', ')[1])
        if rows != yaml.rec_rows:
            raise ValueError("Rows value does not match in yaml and HTD files.")
        if cols != yaml.rec_cols:
            raise ValueError("Columns value does not match in yaml and HTD files.")
        # if any("XSites" in line for line in lines):
        #     x_sites = int(
        #         next((s for s in lines if 'XSites' in s), None).split(', ')[1])
        # else:
        #     x_sites = 1
        # if any("YSites" in line for line in lines):
        #     y_sites = int(
        #         next((s for s in lines if 'YSites' in s), None).split(', ')[1])
        # else:
        #     y_sites = 1
        n_waves = int(
            next((s for s in lines if 'NWavelengths' in s), None).split(', ')[1])
        # loop to get all the WaveNames
        wave_names = []
        for i in range(n_waves):
            name = 'WaveName' + str(i + 1)
            wave_name = next((s for s in lines if name in s),
                             None).split(', ')[1]
            wave_names.append(wave_name.rstrip().replace('"', ''))

    print('HTD metadata:')
    print("\t\texperiment description: {}".format(desc))
    print("\t\ttime points: {}".format(time_points))
    print("\t\trows: {}".format(rows))
    print("\t\tcolumns: {}".format(cols))
    # print("\t\tx sites: {}".format(x_sites))
    # print("\t\ty sites: {}".format(y_sites))
    print("\t\tnumber of wavelengths: {}".format(n_waves))
    print("\t\twavelengths: {}".format(wave_names))

    g = g_class(yaml.file_structure, yaml.mode, yaml.rows, yaml.cols, yaml.rec_rows, yaml.rec_cols,
                yaml.crop, yaml.x_sites, yaml.y_sites, yaml.stitch, yaml.input, yaml.work, yaml.output,
                yaml.plate_dir, yaml.plate, yaml.plate_short, yaml.wells,
                yaml.circle_diameter, yaml.square_side,
                desc, time_points, n_waves, wave_names, '')

    return g

# checks and adds '_w1' at the end of all filenames within the given directory if it doesn't already exist
def rename_files(g):
    for timepoint in range(g.time_points):
        images = os.listdir(g.plate_dir.joinpath('TimePoint_' + str(timepoint + 1)))
        for current in images:
            current_path = os.path.join(g.plate_dir, 'TimePoint_' + str(timepoint + 1), current)
            if re.search(r'_w1\.(tif|TIF)$', current_path, re.IGNORECASE) or not re.search(r'\.(tif|TIF)$', current_path, re.IGNORECASE):
                continue
            outpath = current_path[:-4] + '_w1.TIF'
            os.rename(current_path, outpath)

# create list of selected wells and sites (specifically for 'All' wells selected)
# list of well_sites will be identical to list of wells if stitch == True
# else it will be a list of all well/site pairings
def get_wells(g):
    wells = []
    well_sites = []
    
    if g.wells == ['All']:
        for row in range(g.rows):
            for col in range(g.cols):
                # If site-level, include sites (e.g. A01_s1)
                if g.mode == 'multi-site' and g.stitch == False:
                    for site in range(g.x_sites * g.y_sites):
                        well_id = well_idx_to_name(g, row, col)
                        wells.append(well_id)
                        well_site_id = well_idx_to_name(g, row, col) + f'_s{site + 1}'
                        well_sites.append(well_site_id)
                else:
                    well_id = well_idx_to_name(g, row, col)
                    wells.append(well_id)
                    well_sites.append(well_id)
    else:
        if g.mode == 'multi-site' and g.stitch == False:
            # If site-level, include sites (e.g. A01_s1)
            for well in g.wells:
                for site in range(g.x_sites * g.y_sites):
                    well_site_id = well + f'_s{site + 1}'
                    well_sites.append(well_site_id)
        else:
            well_sites = g.wells
        
        wells = g.wells

    # Check available wells in TimePoint_1 folder
    available_wells = set()
    available_well_sites = set()
    timepoint_dir = os.path.join(g.input, g.plate, "TimePoint_1")
    
    if os.path.exists(timepoint_dir):
        available_images = os.listdir(timepoint_dir)

        # Compare well_sites against available images
        for well_site in well_sites:
            # Match well_site with optional '_w' suffix
            pattern = f"{g.plate_short}_{well_site}(_w\\d)?\\.TIF"
            for image in available_images:
                if re.match(pattern, image):
                    available_wells.add(well_site.split('_s')[0])  # Add base well id
                    available_well_sites.add(well_site)  # Add the full well site
                    break 

    # Identify missing wells and well_sites
    missing_wells = [well for well in wells if well not in available_wells]
    missing_well_sites = [well_site for well_site in well_sites if well_site not in available_well_sites]

    # Log missing wells
    if g.mode == 'multi-site':
        if missing_well_sites:
            print(f"Missing well sites: {', '.join(missing_well_sites)}")
    else:
        if missing_wells:
            print(f"Missing wells: {', '.join(missing_wells)}")

    # Update wells and well_sites to only include available ones
    wells = list(available_wells)
    well_sites = list(available_well_sites)

    # Return updated wells and well_sites
    return wells, well_sites
