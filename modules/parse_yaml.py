import yaml
import re
from pathlib import Path


def parse_yaml(arg_parser, g_class):

    # required positional arguments
    arg_parser.add_argument('parameters',
                            help='Path to the paramaters.yml file.')
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
    mode = conf.get('imaging_mode')[0]
    file_structure = conf.get('file_structure')[0]
    print('instrument settings:')
    print("\t\timaging mode: {}".format(mode))
    print("\t\tfile structure: {}".format(file_structure))
    # physical plate dimensions
    rows = int(conf.get('well-row'))
    columns = int(conf.get('well-col'))
    if mode == 'multi-well':
        well_detection = conf.get('multi-well-detection')
        recorded_n_row = int(conf.get('multi-well-row'))
        print("DEBUG", conf.get('multi-well-col'))
        recorded_n_col = int(conf.get('multi-well-col'))
        image_n_row = rows/recorded_n_row
        image_n_col = columns/recorded_n_col
    else:
        well_detection = 'NA'
        image_n_row = 'NA'
        image_n_col = 'NA'
    print(f"\t\trows: {rows}")
    print(f"\t\tcolumns: {columns}")
    print(f"\t\twell detection: {well_detection}")
    print(f"\t\twell rows per image: {image_n_row}")
    print(f"\t\twell columns per image: {image_n_col}")

    # read the modules, remove any where run is False
    modules = conf.get('modules')
    print('modules:')
    for key, value in modules.copy().items():
        if value['run'] is False:
            print("\t\t{}: {}".format(key, value['run']))
            del modules[key]
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
    circle_mask = conf.get('circle_mask')
    square_mask = conf.get('square_mask')
    circle_radius = ''
    square_side = ''
    if circle_mask == 'True' and square_mask == 'True':
        raise ValueError("circle_mask and square_mask cannot both be True.")
    elif circle_mask == 'True':
        circle_radius = conf.get('circle_radius')
        pass
    elif square_mask == 'True':
        square_side = conf.get('square_side')
        pass

    yaml_out = g_class(mode, file_structure, well_detection, image_n_row, image_n_col,
                       input, work, output, plate_dir, plate, plate_short,
                       '', '', columns, rows, '', '', '', '', wells, '', circle_mask, circle_radius, square_mask, square_side)

    return yaml_out, modules
