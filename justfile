set shell := ["bash", "-uc"]

qgis_image := "qaequilibrae-qgis"
qgis_runtime_environment := "-e QT_QPA_PLATFORM=offscreen -e PYTHONPATH=/workspace/qaequilibrae/packages:/usr/share/qgis/python"
workspace := justfile_directory()

# The LTR QGIS image provides the PyQt5 bindings required by the plugin.
# List available recipes.
default:
    @just --list

# Run a command in a QGIS container with the project's persistent test environment.
# `tty` and `environment` are empty for a non-interactive command without QGIS runtime variables.
_qgis tag tty environment command:
    docker run --rm --init {{ tty }} {{ environment }} \
        -v "{{ workspace }}:/workspace" \
        -v "qaequilibrae-{{ tag }}-venv:/opt/venv" \
        -v "qaequilibrae-{{ tag }}-packages:/workspace/qaequilibrae/packages" \
        -w /workspace \
        {{ qgis_image }}:{{ tag }} \
        bash -lc '{{ command }}'

# Build the local QGIS image. The public `ltr` tag is fixed to the CI QGIS 3.44.0 image.
_qgis-image tag:
    qgis_base_image="qgis/qgis:{{ tag }}"; \
    if [ "{{ tag }}" = "ltr" ]; then \
        qgis_base_image="qgis/qgis:3.44.0"; \
    fi; \
    docker build --pull \
        --build-arg QGIS_BASE_IMAGE="$qgis_base_image" \
        --tag {{ qgis_image }}:{{ tag }} \
        .

# Create or update the isolated test environment for a QGIS image.
# The named volumes keep Linux packages out of the working tree.
setup tag="ltr":
    just _qgis-image {{ tag }}
    just _qgis {{ tag }} '' '{{ qgis_runtime_environment }}' '\
        export PATH=/opt/venv/bin:$PATH; \
        set -euo pipefail; \
        qgis_python_version=$(python3 -c "import sys; print(f\"{sys.version_info.major}.{sys.version_info.minor}\")"); \
        venv_python_version=$(/opt/venv/bin/python -c "import sys; print(f\"{sys.version_info.major}.{sys.version_info.minor}\")" 2>/dev/null || true); \
        if [ "$venv_python_version" != "$qgis_python_version" ]; then \
            python3 -m venv --clear /opt/venv --system-site-packages; \
        fi; \
        packages_signature=$( \
            { \
                printf "%s\n" "$qgis_python_version"; \
                sha256sum qaequilibrae/requirements.txt qaequilibrae/aequilibrae_version.txt; \
            } | sha256sum | awk "{print \$1}" \
        ); \
        packages_signature_file=/workspace/qaequilibrae/packages/.qaequilibrae-package-signature; \
        reset_packages=0; \
        if [ "$(cat "$packages_signature_file" 2>/dev/null || true)" != "$packages_signature" ]; then \
            find /workspace/qaequilibrae/packages -mindepth 1 -maxdepth 1 ! -name __init__.py -exec rm -rf {} +; \
            reset_packages=1; \
        fi; \
        /opt/venv/bin/python -m pip install --upgrade pip setuptools uv; \
        constraints_arg=""; \
        if [ -f ci/constraints.txt ]; then \
            constraints_arg="--constraint ci/constraints.txt"; \
        fi; \
        /opt/venv/bin/python -m uv pip install -r test/requirements_test.txt $constraints_arg; \
        python3 ./ci/dependency_installation.py; \
        if [ "$reset_packages" -eq 1 ]; then \
            printf "%s\n" "$packages_signature" > "$packages_signature_file"; \
        fi'

# Run the complete test suite. Pass another tag to use a different QGIS image.
# Example: `just test ltr --durations=20`
test tag="ltr" *pytest_args:
    just setup {{ tag }}
    just _qgis {{ tag }} '' '{{ qgis_runtime_environment }}' 'export PATH=/opt/venv/bin:$PATH; /opt/venv/bin/python -m pytest --cov-report term-missing --cov=qaequilibrae test {{ pytest_args }}'

# Run one test file, test node, or parametrized test.
# Example: `just test-one test/test_routing.py::test_route ltr --durations=20`
test-one test_path tag="ltr" *pytest_args:
    just setup {{ tag }}
    just _qgis {{ tag }} '' '{{ qgis_runtime_environment }}' '/opt/venv/bin/python -m pytest --cov-report term-missing --cov=qaequilibrae {{ test_path }} {{ pytest_args }}'

# Profile Python execution for one test path or the complete suite.
# The report shows the 40 functions with the largest cumulative times.
# Example: `just profile test/test_routing.py ltr`
profile test_path="test" tag="ltr" *pytest_args:
    just setup {{ tag }}
    just _qgis {{ tag }} '' '{{ qgis_runtime_environment }}' 'export PATH=/opt/venv/bin:$PATH; profile_file=/tmp/qaequilibrae-pytest.prof; /opt/venv/bin/python -m cProfile -o "$profile_file" -m pytest {{ test_path }} {{ pytest_args }}; pytest_exit=$?; /opt/venv/bin/python -c "import pstats; pstats.Stats(\"$profile_file\").strip_dirs().sort_stats(\"tottime\").print_stats(40)"; exit "$pytest_exit"'

# Run the suite with the LTR QGIS image explicitly.
test-ltr:
    just test ltr

# Open an interactive QGIS container with the test environment on PATH.
# Example: `just shell latest`
shell tag="ltr":
    just setup {{ tag }}
    just _qgis {{ tag }} -it '{{ qgis_runtime_environment }}' 'export PATH=/opt/venv/bin:$PATH; exec bash -i'

# Open an interactive container with the LTR QGIS image.
shell-ltr:
    just shell ltr

# Run the project's formatting and lint checks in the selected QGIS image.
lint tag="ltr":
    just setup {{ tag }}
    just _qgis {{ tag }} '' '' '\
        /opt/venv/bin/ruff check && \
        /opt/venv/bin/black --check .'
