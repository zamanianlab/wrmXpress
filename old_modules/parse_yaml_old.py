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
    if mode == 'multi-well':
        well_detection = conf.get('multi-well-detection')[0]
        image_n_row = int(conf.get('multi-well-row'))
        image_n_col = int(conf.get('multi-well-cols'))
    else:
        well_detection = 'NA'
        image_n_row = 'NA'
        image_n_col = 'NA'
    print("\t\twell detection: {}".format(well_detection))
    print("\t\twell rows per image: {}".format(image_n_row))
    print("\t\twell columns per image: {}".format(image_n_col))

    # worm settings
    species = conf.get('species')[0]
    stages = conf.get('stages')[0]
    print('wormzzzz:')
    print("\t\tspecies: {}".format(species))
    print("\t\tstages: {}".format(stages))

    # read the modules, remove any where run is False
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

    yaml_out = g_class(mode, file_structure, well_detection, image_n_row, image_n_col,
                       species, stages,
                       input, work, output, plate_dir, plate, plate_short,
                       '', '', '', '', '', '', '', '', wells, '')

    return yaml_out, modules
