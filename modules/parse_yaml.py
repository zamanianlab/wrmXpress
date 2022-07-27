import yaml
import re
from pathlib import Path
from collections import namedtuple

def parse_yaml(arg_parser, g):

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
    wells = conf.get('wells')  # list of wells or 'All'
    wells_per_image = conf.get('wells_per_image')  # string
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

    yaml_out = g(input, work, output, plate_dir, plate, plate_short, species, stages, wells_per_image, '', '', '', '', '', '', '', wells, '')

    return yaml_out, modules