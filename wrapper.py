import argparse
import subprocess
import glob
from pathlib import Path
from collections import defaultdict, namedtuple
import time
import os

from preprocessing.utilities import parse_yaml, parse_htd, rename_files, get_wells
from preprocessing.image_processing import (
    avi_to_ix,
    grid_crop,
    stitch_all_timepoints,
    apply_masks,
)
from pipelines.diagnostics import static_dx, video_dx
from pipelines.optical_flow import optical_flow
from pipelines.segmentation import segmentation
from pipelines.cellprofiler import cellprofiler

if __name__ == "__main__":

    start = time.time()

    # create the class that will instantiate the namedtuple
    g_class = namedtuple(
        "g_class",
        [
            "file_structure",
            "mode",
            "rows",
            "cols",
            "rec_rows",
            "rec_cols",
            "crop",
            "x_sites",
            "y_sites",
            "stitch",
            "input",
            "work",
            "output",
            "plate_dir",
            "plate",
            "plate_short",
            "wells",
            "circle_diameter",
            "square_side",
            "desc",
            "time_points",
            "n_waves",
            "wave_names",
            "plate_paths",
        ],
    )

    ############################################
    ######### 1. GET THE YAML CONFIGS  #########
    ############################################

    arg_parser = argparse.ArgumentParser()
    g, pipelines = parse_yaml(arg_parser, g_class)

    # get wells/sites to be used
    wells, well_sites = get_wells(g)

    #########################################################
    ######### 2. GET THE HTD CONFIGS OR CROP WELLS  #########
    #########################################################

    # standardise file structure to imageXpress and parse HTD
    if g.file_structure == "imagexpress":
        g = parse_htd(g, g_class)
        # if single wavelength, '_w1' filename will not have '_w1' so it must be added
        if g.n_waves == 1:
            rename_files(g)
    elif g.file_structure == "avi":
        # convert avi to tifs and create HTD (done in avi_to_ix)
        avi_to_ix(g)
        g = parse_htd(g, g_class)
    else:
        raise ValueError("Unsupported file structure.")

    # crop/stitch wells if specified and apply mask if required
    if g.crop == "grid":
        grid_crop(g)
    elif g.crop == "auto":
        # auto_crop(g)
        pass
    elif g.stitch:
        # stitch(g)
        stitch_all_timepoints(g, wells, Path(g.plate_dir), Path(g.plate_dir))

    # apply masks if required
    apply_masks(g)

    ###################################
    ######### 3. CREATE FOLDERS  #########
    ###################################
    # Create folder for each pipeline and the subfolders
    for pipeline in pipelines.keys():
        pipeline_output_dir = Path(g.output) / pipeline
        pipeline_work_dir = Path(g.work) / pipeline
        # Create main pipeline directory
        pipeline_output_dir.mkdir(parents=True, exist_ok=True)
        pipeline_work_dir.mkdir(parents=True, exist_ok=True)
        # Create 'img' folder
        img_dir = pipeline_output_dir / "img"
        img_dir.mkdir(parents=True, exist_ok=True)

    ##############################################
    ######### 4. DIAGNOSTICS & PIPELINES #########
    ##############################################
    # generate static_dx
    if "static_dx" in pipelines:
        static_dx(
            g,
            wells,
            Path(g.plate_dir) / "TimePoint_1",
            Path(g.output) / "static_dx",
            Path(g.work) / "static_dx" / "TimePoint_1",
            None,
            pipelines["static_dx"]["rescale_multiplier"],
        )

    # generate video_dx
    if "video_dx" in pipelines:
        video_dx(
            g,
            wells,
            Path(g.plate_dir),
            Path(g.output) / "video_dx",
            Path(g.work) / "static_dx",
            Path(g.work) / "video_dx",
            pipelines["video_dx"]["rescale_multiplier"],
        )

    wavelengths_dict = {}  # Dictionary to store wavelengths for each pipeline
    well_site_num = 1  # counter for well_sites

    for well_site in well_sites:
        print(well_site, f"{well_site_num}/{len(well_sites)}")
        if "optical_flow" in pipelines:
            wavelengths = optical_flow(g, pipelines["optical_flow"], well_site, multiplier=2)
            wavelengths_dict["optical_flow"] = wavelengths

        if "segmentation" in pipelines:
            wavelengths = segmentation(g, pipelines["segmentation"], well_site)
            wavelengths_dict["segmentation"] = wavelengths

        if "cellprofiler" in pipelines:
            wavelengths = cellprofiler(g, pipelines["cellprofiler"], well_site)
            wavelengths_dict["cellprofiler"] = wavelengths

        well_site_num += 1

    # After running the pipelines, call static_dx with the correct wavelengths
    for pipeline in pipelines:
        print(f"Running static_dx for {pipeline}.")
        if any(file.endswith(".png") for file in os.listdir(Path(g.work, pipeline))):
            pipeline_wavelengths = wavelengths_dict.get(pipeline, None)
            for wavelength in pipeline_wavelengths:
                static_dx(
                    g,
                    wells,
                    Path(g.work, pipeline),
                    Path(g.output, pipeline),
                    None,
                    [wavelength],
                    rescale_factor=1,
                    format="PNG",
                )

    # generate tidy csvs using the R script
    print("Running R script to join metadata and tidy.")
    r_script_path = "/root/wrmXpress/Rscripts/metadata_join_master.R"

    # Get the list of pipeline directories
    pipeline_dirs = [d for d in Path(g.work).iterdir() if d.is_dir()]

    # Filter and get CSVs for the specific plate in the pipeline directories
    pipeline_csv_list = [
        d.name
        for d in pipeline_dirs
        if any(glob.glob(str(d / f"*{g.plate_short}*.csv")))
    ]
    print("Pipeline CSVs list:", pipeline_csv_list)

    # Check if there are any CSVs to process
    if pipeline_csv_list:
        subprocess.run(
            [
                "Rscript",
                r_script_path,
                g.input,
                g.work,
                g.output,
                g.plate,
                g.plate_short,
                str(g.rows),
                str(g.cols),
                ",".join(pipeline_csv_list),
            ]
        )
    else:
        print("No CSV files found for the specified plate.")

    end = time.time()
    print("Time elapsed (seconds):", end - start)
    raise Exception("CODE STOPS HERE")