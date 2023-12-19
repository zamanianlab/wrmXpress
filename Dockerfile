FROM continuumio/miniconda3:4.9.2

# install conda packages
COPY local_env/conda_env.yml .
RUN \
   conda env update -n root -f conda_env.yml \
&& conda clean -a

RUN mkdir wrmXpress
RUN mkdir wrmXpress/cp_pipelines
RUN mkdir wrmXpress/cellpose_training
RUN mkdir wrmXpress/cellpose_training/models
RUN mkdir wrmXpress/modules
RUN mkdir wrmXpress/scripts

COPY wrapper.py wrmXpress
COPY cp_pipelines/* wrmXpress/cp_pipelines/
COPY cellpose_training/models/* wrmXpress/cellpose_training/models/
COPY modules/* wrmXpress/modules/
COPY scripts/* wrmXpress/scripts/