set shell := ["bash", "-uc"]

qgis_image := "qaequilibrae-qgis"
workspace := justfile_directory()

# The LTR QGIS image provides the PyQt5 bindings required by the plugin.
# List available recipes.
default:
    @just --list

# Run a command in a QGIS container with its image-provided test environment.
_qgis tag tty command:
    docker run --rm --init {{ tty }} \
        -v "{{ workspace }}:/workspace" \
        -v "qaequilibrae-{{ tag }}-packages:/workspace/qaequilibrae/packages" \
        -w /workspace \
        {{ qgis_image }}:{{ tag }} \
        bash -lc '{{ command }}'

# Build the local QGIS image from the corresponding public QGIS image.
_qgis-image tag:
    docker build --pull \
        --build-arg QGIS_BASE_IMAGE="qgis/qgis:{{ tag }}" \
        --tag {{ qgis_image }}:{{ tag }} \
        .

# Create or update the plugin packages for a QGIS image.
# The named volume keeps Linux packages out of the working tree.
setup tag="ltr":
    just _qgis-image {{ tag }}
    just _qgis {{ tag }} '' '\
        set -euo pipefail; \
        qgis_python_version=$(/opt/venv/bin/python -c "import sys; print(f\"{sys.version_info.major}.{sys.version_info.minor}\")"); \
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
        /opt/venv/bin/python ./ci/dependency_installation.py; \
        if [ "$reset_packages" -eq 1 ]; then \
            printf "%s\n" "$packages_signature" > "$packages_signature_file"; \
        fi'

# Run the complete test suite. Pass another tag to use a different QGIS image.
# Example: `just test ltr --durations=20`
test tag="ltr" *pytest_args:
    just setup {{ tag }}
    just _test {{ tag }} {{ pytest_args }}

# Run one test file, test node, or parametrized test.
# Example: `just test-one test/test_routing.py::test_route ltr --durations=20`
test-one test_path tag="ltr" *pytest_args:
    just setup {{ tag }}
    just _qgis {{ tag }} '' 'python -m pytest --cov-report term-missing --cov=qaequilibrae {{ test_path }} {{ pytest_args }}'

# Profile Python execution for one test path or the complete suite.
# The report shows the 40 functions with the largest cumulative times.
# Example: `just profile test/test_routing.py ltr`
profile test_path="test" tag="ltr" *pytest_args:
    just setup {{ tag }}
    just _qgis {{ tag }} '' 'profile_file=/tmp/qaequilibrae-pytest.prof; python -m cProfile -o "$profile_file" -m pytest {{ test_path }} {{ pytest_args }}; pytest_exit=$?; python -c "import pstats; pstats.Stats(\"$profile_file\").strip_dirs().sort_stats(\"tottime\").print_stats(40)"; exit "$pytest_exit"'

# Run the suite with the LTR QGIS image explicitly.
test-ltr:
    just test ltr

# Open an interactive QGIS container with the image-provided test environment on PATH.
# Example: `just shell latest`
shell tag="ltr":
    just setup {{ tag }}
    just _qgis {{ tag }} -it 'exec bash -i'

# Open an interactive container with the LTR QGIS image.
shell-ltr:
    just shell ltr

# Run the project's formatting and lint checks in a prepared QGIS image.
_lint tag:
    just _qgis {{ tag }} '' '\
        ruff check && \
        ruff format --check --diff'

# Run the complete test suite in a prepared QGIS image.
_test tag *pytest_args:
    just _qgis {{ tag }} '' 'python -m pytest --cov-report term-missing --cov=qaequilibrae test {{ pytest_args }}'

# Run the project's formatting and lint checks in the selected QGIS image.
lint tag="ltr":
    just setup {{ tag }}
    just _lint {{ tag }}

# Run the local equivalent of the Linux CI checks without preparing QGIS twice.
check tag="ltr" *pytest_args:
    just setup {{ tag }}
    just _lint {{ tag }}
    just _test {{ tag }} {{ pytest_args }}
