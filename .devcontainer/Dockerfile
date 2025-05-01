# syntax=docker/dockerfile:1.7-labs
# Required syntax parser to handle --exclude option for COPY instructions

# -- GLOBAL

# Arguments to customize build
ARG LINUX_DISTRO_NAME=fedora
ARG LINUX_DISTRO_VERSION=39
ARG QGIS_GIT_VERSION=master
ARG BASE_RUN_IMAGE=stage-build

# -- STAGE: BUILD from QGIS Qt6 image
FROM qgis/qgis3-qt6-build-deps-bin-only:${QGIS_GIT_VERSION} as stage-build

ARG QGIS_GIT_VERSION

ENV BUILD_WITH_QT6=ON \
    CCACHE_DIR=/root/.ccache \
    CTEST_BUILD_COMMAND=/usr/bin/ninja \
    CTEST_BUILD_DIR=/root/QGIS/build \
    CTEST_SOURCE_DIR=/root/QGIS \
    ENABLE_UNITY_BUILDS=ON \
    LD_PRELOAD='' \
    QGIS_CONTINUOUS_INTEGRATION_RUN=true \
    QGIS_NO_OVERRIDE_IMPORT=1 \
    QT_VERSION=6 \
    SEGFAULT_SIGNALS="abrt segv" \
    TERM=xterm \
    WITH_3D=ON \
    WITH_CLAZY=OFF \
    WITH_COMPILE_COMMANDS=OFF \
    WITH_GRASS7=OFF \
    WITH_GRASS8=ON \
    WITH_PDF4QT=ON \
    WITH_QT5=OFF \
    WITH_QTWEBENGINE=ON \
    WITH_QUICK=ON \
    XDG_RUNTIME_DIR=/tmp

# clone QGIS source code and launch QGIS build
RUN --mount=type=cache,target=/tmp/ccache \
    ccache --show-stats \
    && git clone --depth 1 --filter=blob:none --single-branch -b ${QGIS_GIT_VERSION} https://github.com/qgis/QGIS.git /root/QGIS/ \
    && rm -rf /root/QGIS/.git \
    && /root/QGIS/.docker/docker-qgis-build.sh

# -- STAGE: RUN
FROM ${LINUX_DISTRO_NAME}:${LINUX_DISTRO_VERSION} as stage-run

LABEL org.opencontainers.image.title="QGIS with Qt6 (testing)" \
    org.opencontainers.image.description="QGIS built with Qt6 from source code. Not suitable for production, only for end-users testing and PyQGIS developers testing." \
    org.opencontainers.image.source="https://github.com/qgis/pyqgis4-checker" \
    org.opencontainers.image.licenses="GPL-2.0-or-later"

# Write .pyc files only once. See: https://stackoverflow.com/a/60797635/2556577
ENV PYTHONDONTWRITEBYTECODE=1 \
    # Make sure that stdout and stderr are not buffered. See: https://stackoverflow.com/a/59812588/2556577
    PYTHONUNBUFFERED=0 \
    # Remove assert statements and any code conditional on __debug__. See: https://docs.python.org/3/using/cmdline.html#cmdoption-O
    PYTHONOPTIMIZE=2

# Import generated files from build stage
COPY --from=stage-build --exclude=share/qgis/i18n/* --exclude=share/qgis/resources/data/* /root/QGIS/build/output/ /usr/local/
COPY --from=stage-build /root/QGIS/build/usr/lib/ /usr/lib/

# Install required dependencies
RUN dnf install --nodocs --refresh -y \
    draco \
    gdal \
    gdal-python-tools \
    gpsbabel \
    grass \
    gsl \
    libzip \
    PDAL \
    PDAL-libs \
    perl-YAML-Tiny \
    poppler-utils \
    protobuf-lite \
    python3-mock \
    python3-oauthlib \
    python3-OWSLib \
    python3-pip \
    python3-pyqt6 \
    python3-qscintilla-qt6 \
    # python3-termcolor \
    # PyQt-builder \
    qca-qt6 \
    qpdf \
    qt6-qt3d \
    qt6-qtbase \
    qt6-qttools-static \
    qt6-qtwebengine \
    qtkeychain-qt6 \
    qwt-qt6 \
    spatialindex \
    util-linux \
    # locale generation
    glibc-langpack-en \
    && localedef -i en_US -f UTF-8 en_US.UTF-8 || true \
    # && dnf remove -y glibc-langpack-en \
    # clean up
    && dnf autoremove -y \
    && dnf clean all \
    && rm -rf /var/cache/dnf/*

# Reference QGIS headers and Python packages into the Python environment
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH \
    PYTHONPATH=/usr/local/python:$PYTHONPATH \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8

# Create non-root user
# -m -> Create the user's home directory
# -s /bin/bash -> Set as the user's
RUN useradd -ms /bin/bash quser \
    && groupadd -f wheel \
    && usermod -aG wheel quser \
    && echo '%wheel ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
USER quser
WORKDIR /home/quser

# # -- STAGE: switchable RUN
# FROM ${BASE_RUN_IMAGE} AS run-from-image
# FROM stage-run AS run-fallback