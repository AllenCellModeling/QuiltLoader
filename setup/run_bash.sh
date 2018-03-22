docker run -it --rm \
    -p ${1}:8888 \
    -v /allen/aics/modeling/${USER}/projects/QuiltLoader/:/home/jovyan/ \
    -v /allen/aics/modeling/data/data_packages/:/home/jovyan/data_packages/ \
    quilt_package_gen \
    bash
