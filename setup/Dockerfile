# start from jupyter
FROM jupyter/minimal-notebook

# for jupyter/ ipython
EXPOSE 8888

# libtiff c functions
USER root

# libtiff5 for other image processing
RUN apt-get update && apt-get install --no-install-recommends \
    libtiff5

# move back to jovyan
USER $NB_USER

# install potential tiff image python libraries
RUN pip --quiet --no-cache-dir install \
    'numpy' \
    'pandas' \
    'matplotlib' \
    'Pillow' \
    'Tifffile'

RUN pip --quiet --no-cache-dir install \
    'labkey' \
    'xmltodict' \
    'lxml' \
    'pprint'

RUN pip install \
    'git+https://github.com/quiltdata/quilt.git#subdirectory=compiler'

# portable environment
ENV IN_DOCKER Yes
ENV QUILT_PRIMARY_PACKAGE_DIR /home/jovyan/data_packages/quilt_packages
ENV QUILT_PACKAGE_DIRS /home/jovyan/data_packages/quilt_packages
