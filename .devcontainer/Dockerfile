FROM qgis/qgis:release-3_28

# [Optional] Uncomment this section to install additional OS packages.
RUN apt update -y && apt install -y pandoc zip

# [Optional] If your pip requirements rarely change, uncomment this section to add them to the image.
RUN pip3 --disable-pip-version-check --no-cache-dir install setuptools --upgrade

RUN export CI='CI'
