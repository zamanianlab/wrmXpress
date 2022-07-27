from pathlib import Path
from collections import namedtuple


def parse_htd(yaml):
    '''
    Parse an HTD file and return experimental metadata as variables.
    '''

    # HTD
    with open(yaml.plate_dir.joinpath(yaml.plate_short + '.HTD'), encoding='utf-8', errors='ignore') as f:
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
    print(yaml.wells_per_image)
    g = namedtuple(
        'g', 'input work output plate_dir plate plate_short species stages wells_per_image time_points columns rows x_sites y_sites n_waves wave_names wells plate_paths')
    g = g(yaml.input, yaml.work, yaml.output, yaml.plate_dir, yaml.plate, yaml.plate_short, yaml.species, yaml.stages, yaml.wells_per_image, time_points,
          columns, rows, x_sites, y_sites, n_waves, wave_names, yaml.wells, '')

    return g