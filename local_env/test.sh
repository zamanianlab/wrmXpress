#!/bin/bash

# set home () and mk dirs
export HOME=$PWD
mkdir input
mkdir metadata
mkdir output/
mkdir work/

# clone the repo
git clone --branch packagify https://github.com/zamanianlab/Core_imgproc.git

# run the wrapper
python Core_imgproc/wrapper.py Core_imgproc/local_env/parameters_template.yml 20211013-p03-NJW_931

# remove the repo
rm -rf Core_imgproc
