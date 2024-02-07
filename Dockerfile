FROM amd64/ubuntu:20.04


# Install Cell Profiler and dependencies
ARG cp_version=4.2.6

ARG DEBIAN_FRONTEND=noninteractive

RUN apt update
RUN apt -y upgrade
RUN apt install -y make gcc build-essential libgtk-3-dev wget git
RUN apt install -y python3.9-dev python3.9-venv python3-pip openjdk-11-jdk-headless default-libmysqlclient-dev libnotify-dev libsdl2-dev libwebkit2gtk-4.0-dev

ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV VIRTUAL_ENV=/opt/venv
RUN python3.9 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN pip install --upgrade pip
RUN pip install wheel cython numpy

RUN pip install https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-20.04/wxPython-4.2.1-cp39-cp39-linux_x86_64.whl

RUN pip install cellprofiler==$cp_version

# Install R and packages
RUN apt update && apt install -y --no-install-recommends \ 
   r-base r-base-dev
RUN Rscript -e 'install.packages(c("dplyr", "stringr", "tidyr", "readr", "magrittr", "purrr"))'
# RUN Rscript -e 'install.packages("tidymodels")'

# Install wrmXpress dependencies
RUN pip install pandas pyyaml pyarrow opencv-python-headless==4.5.1.48 cellpose

RUN mkdir wrmXpress
COPY wrapper.py wrmXpress

RUN mkdir /root/wrmXpress/

RUN mkdir wrmXpress/cp_pipelines
RUN mkdir wrmXpress/cp_pipelines/cellpose_models
COPY cp_pipelines/cellpose_models/* wrmXpress/cp_pipelines/cellpose_models

RUN mkdir /root/wrmXpress/cp_pipelines
RUN mkdir /root/wrmXpress/cp_pipelines/masks
COPY cp_pipelines/masks/* /root/wrmXpress/cp_pipelines/masks

RUN mkdir wrmXpress/cp_pipelines/pipelines
COPY cp_pipelines/pipelines/* wrmXpress/cp_pipelines/pipelines

RUN mkdir /root/wrmXpress/cp_pipelines/worm_models
COPY cp_pipelines/worm_models/*.xml /root/wrmXpress/cp_pipelines/worm_models

RUN mkdir wrmXpress/modules
COPY modules/* wrmXpress/modules/

RUN mkdir wrmXpress/scripts
COPY scripts/metadata_join_master.R wrmXpress/scripts/
COPY scripts/npy_to_tiff.py wrmXpress/scripts/

# RUN mkdir wrmXpress/scripts
RUN mkdir wrmXpress/scripts/cp
COPY scripts/cp/* wrmXpress/scripts/cp
ENV CP_JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64