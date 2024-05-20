FROM qgis/qgis:release-3_34

# Set environment variables for QGIS
ENV QGIS_PREFIX_PATH=/usr
ENV QT_QPA_PLATFORM=offscreen
ENV XDG_RUNTIME_DIR=/tmp/runtime-root

# Updates package indexes and installs necessary tools
RUN apt update && \
    apt install -y python3-venv python3-pip

# Set the working directory in the container
WORKDIR /app

# Creates and activates the virtual environment
RUN python3 -m venv --system-site-packages qgis_env
ENV PATH="/app/qgis_env/bin:$PATH"

# Activates the virtual environment and installs QGIS
RUN . qgis_env/bin/activate && \
    apt install -y qgis python3-qgis qgis-plugin-grass && \
    ln -s /usr/local/bin/qgis-bin /app/qgis_env/bin/qgis

RUN python3 -m pip install setuptools

# Defines the default command to be executed when the container starts
CMD ["bash", "-c", "source /app/qgis_env/bin/activate && qgis"]
