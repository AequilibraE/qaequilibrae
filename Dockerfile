ARG QGIS_BASE_IMAGE=qgis/qgis:ltr
FROM ${QGIS_BASE_IMAGE}

RUN apt update -y \
    && apt install -y --no-install-recommends pandoc zip \
    && rm -rf /var/lib/apt/lists/*

COPY test/requirements_test.txt /tmp/requirements_test.txt

RUN python3 -m venv /opt/venv --system-site-packages \
    && /opt/venv/bin/python -m pip install --upgrade pip setuptools uv \
    && /opt/venv/bin/python -m uv pip install -r /tmp/requirements_test.txt \
    && rm /tmp/requirements_test.txt

ENV PATH=/opt/venv/bin:${PATH}
ENV PYTHONPATH=/workspace/qaequilibrae/packages:/usr/share/qgis/python
ENV QT_QPA_PLATFORM=offscreen
