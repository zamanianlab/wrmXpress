<img src="img/logo/output.png" alt="hex" align = "left" width="130" />

<br>  
<br>  
<br>  
<br>  
<br>  
<br>  

# Overview

This package contains a variety of Python and CellProfiler pipelines used for the analysis of worm imaging data. Some of these are specific to Zamanian lab experimental pipelines, but many of the pipelines should be robust to a diversity of species and experimental procedures.

Experimental protocols used to generate images that are compatible with wrmXpress can be found in the associated manuscripts and preprints:

- [wrmxpress V2.0 preprint](https://doi.org/10.1101/2025.03.14.643077)

- [wrmXpress manuscript](https://doi.org/10.1371/journal.pntd.0010937)

    Contains all the wrmXpress details. See this manuscript for an explanation of pipelines (previously called modules) included.
- [Multivariate screening preprint](https://doi.org/10.1101/2022.07.25.501423)

    Includes comprehensive protocols for microfilariae imaging (motility and viability) and adult filaria imaging (motility). Detailed step-by-step procedures can be found at Protocol Exchange for the [bivariate high-content mf screen](https://doi.org/10.21203/rs.3.pex-1916/v1) and the [multivarite adult screen](https://doi.org/10.21203/rs.3.pex-1918/v1).
- [*C. elegans* feeding preprint](https://doi.org/10.1101/2022.08.31.506057)

    Includes details on the development and validation of a feeding protocol using fluorescent stains. Detailed step-by-step procedures for parts of this assay can be found [here](https://doi.org/10.21203/rs.3.pex-2018/v1).

# Installation and usage

The Zamanian Lab run all analyses on a node at the [Center for High-Throughput Computing at UW-Madison](https://chtc.cs.wisc.edu). A Docker recipe containing all the dependendenies can be found in our [Docker GitHub repo](https://github.com/zamanianlab/Docker/tree/main/chtc-wrmxpress), and a pre-compiled image can be found at [DockerHub](https://hub.docker.com/repository/docker/zamanianlab/chtc-wrmxpress). A Conda environment file has also been provided at `local_env/conda_env.yml`, though this may need modification based on the user's processor (e.g., Apple vs Intel).

## Running wrmXpress in a Docker container (local or remote)

1. If running locally, use the Docker desktop app to access the [pre-compiled docker image](https://hub.docker.com/repository/docker/zamanianlab/chtc-wrmxpress). If running on a remote server, consult with the server administrator for using Docker images.

2. Create a directory where all the wrmXpress operations will take place.

3. In this new home directory, make `input`, `output`, `metadata`, and `work` directories.

4. Clone the wrmXpress repository from GitHub in the same folder.

5. Transfer the imaging data to `input`. If using a directory of images from wells of a multi-well plate, ensure the image directories are structured in the same was as the example datasets at this Zenodo repository: [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.7116648.svg)](https://doi.org/10.5281/zenodo.7116648).

6. Transfer the metadata to `metadata`. A given experiment can have any amount of metadata CSVs, and each CSV should contain a single piece of metadata (i.e., strain.csv, species.csv, treatment.csv, conc.csv, etc.). CSVs should be structured to have the same shape as the multi-well plate (that is, A01 should be the top-left cell).

7. Use and edit the provided YAML file `master.yml` to configure the run and add it to the home directory. The file should have the same name as the plate directory in `input`.

8. At this point, your home directory should look like this:
```
[name of home directory]/
├── input/{plate}
├── metadata/{plate}
├── work/
├── output/
├── wrmXpress/
└── {plate}.yml
```

9. Open Docker and a terminal window, and run this command with the path to your home directory
```
docker run -it -v /Path/To/Home/Directory:/home -rm=TRUE zamanianlab/chtc-wrmxpress:v7/bin/bash
```

10. Run these two commands:
```
cd .. && cd home
export HOME=$PWD
```

11. Run this final command: 
```
python wrmXpress/wrapper.py {plate}.yml {plate}
```
where `{plate}` is the name of the directory that contains the data in `input`.

If using a CellProfiler pipeline that implements Cellpose for *C. elegans* segementation, training of a custom model may be required. Follow the instructions [here](cellpose_training/README.md) to train a model on custom images.

For testing, example data for each pipline is provided here: [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.7116648.svg)](https://doi.org/10.5281/zenodo.7116648).

# Structure

Pipeline parameters are provided in a YAML file (a template with all the fields and options can be found in the main folder as `master.yml`). Parameters are organized within the following headings:

### Instrument settings

**File structure** - A raw, uncompressed avi (typically associated with multi-well imaging) or the opinionated structure used by the ImageXpress.

**Imaging mode** - Single well per image, multiple wells per image, or single sites per image (multi-site).

### Processing multi-well images

**Physical plate dimensions** - The true count of wells in each row and column

**Number of rows and columns per image** - If performing multi-well imaging, include the number of rows/columns in each image. Set both to 1 if mode is single-well.

**Multi-well detection mode** - If performing multi-well imaging, choose the method for detecting wells. `auto` works for cropped videos of 24-well plates; use `grid` for other formats.

**Sites** - If multi-site is flagged, set the number of sites on the x and y axis.

### Run-time settings

**Wells** - Either `All` or a list of wells (each well on a new line, initiated with a hyphen)

**Directories** - Full paths of the `input/`, `output/`, and `work/` directories. If using a Docker image, each can be in the root directory.

### Universal Image Transformations

**Circle diameter** - To apply a circular mask where the radius is a fraction of the image height

**Square side** - To apply a square mask where the square side is a fraction of the image height

### Pipeline selection

**Pipelines** contains a key for each possible pipeline, including CellProfiler. Pipelines are invoked by setting the value of `run` to `True`; additional pipeline-specific parameters may apply.

# Pipelines 

Please see the [manuscript](https://doi.org/10.1371/journal.pntd.0010937) for a more thorough description of each pipeline previously called "modules".

## Diagnostics

### static_dx

<img src="img/wormsize_dx.png" alt="wormsize" align = "left" width="200" />

Generates a plate-shaped thumbnail of each wavelength, as well as diagnostic images from certain pipelines.

<br>
<br>
<br>
<br>

### video_dx

Generates a plate-shaped video of each wavelength, where single-well video can be captured as well.

## Motility

<img src="img/flow_dx.png" alt="flow" align = "left" width="200" />

A Python implementation of CV2's dense flow algorithm. Requires video input and supports `imagexpress` or `avi` modalities. Thumbnails of flow output are generated by `static_dx`. If using `multi-well`, `auto` works for videos of 24-well plates cropped to only include the plate; otherwise use `grid`.

<br>
<br>
<br>
<br>

## Segmentation

<img src="img/segment_dx.png" alt="segment" align = "left" width="200" />

Segments worms using a combination of Sobel and Gaussian filters. Has been tested with microfilaria, nematode larvae and adults, and schistosome adults. Can be run on multiple wavelengths and with multi-site images. Thumbnails of segmented worms are generated by `static_dx`.

<br>
<br>
<br>
<br>

## CellProfiler pipelines

### mf_celltox

<img src="img/celltox.png" alt="celltox" align = "left" width="200" />

Measures dead microfilaria via fluorescent staining. Compatible with multi-site images. Untested for other worms/stages, but is likely to work out-of-the-box.

<br>
<br>
<br>
<br>

### feeding

<img src="img/feeding.png" alt="feeding" align = "left" width="200" />

Measures fluorescence in two channels. Specifically used for *C. elegans* feeding assays, but likely to work with slight modification for any *C. elegans* assay that seeks to measure worm fluorescence in multiple channels.

<br>
<br>

### wormsize

<img src="img/straightened.png" alt="straightened" align = "left" width="200" />

Generic pipeline for measuring the size of worms. Has been tested with mixed stages of *C. elegans*; may work with parasites. Incorporates the worm untangling and straightening algorithms from the [Worm Toolbox](https://doi.org/10.1038/nmeth.1984).

<br>
<br>
<br>

### wormsize_trans

Implementation of `wormsize` that also measures worm fluorescence in a single wavelength. Useful for filtering for transgenic worms containing a fluorescent marker.

### wormsize_intensity

Implementation of `wormsize` that also measures intensity features, which may be helpful for filtering non-worms.

### wormsize_intensity_cellpose

Implementation of `wormsize_intensity` that uses [Cellpose](https://github.com/MouseLand/cellpose) and a pre-trained model for *C. elegans* segmentation.

## Tracking

<img src="img/tracking.png" alt="straightened" align = "left" width="200" />

Tracks the individual worms by generating frame-by-frame coordinated data

<br>
<br>

# Issues

Please use the provided issue template when submitting a bug report.
