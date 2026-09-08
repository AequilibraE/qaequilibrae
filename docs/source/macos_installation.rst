macOS installation
==================

For Linux and Windows, AequilibraE provides pre-compiled wheels. On macOS,
QAequilibraE builds AequilibraE from source. This process requires the same
tools used to build AequilibraE. Install these tools first. QAequilibraE then
builds and installs its required packages.

Install the required tools
--------------------------

1. Open the **Terminal** application.

2. Install the Apple command-line tools. Run::

    xcode-select --install

   Follow the instructions in the installation window. If Terminal says that the tools are already installed, continue to the next step.

3. Install `Homebrew <https://brew.sh/>`_. Follow the installation instructions on the Homebrew website.

4. Make sure that Homebrew is available. Run::

    brew --version

   If this command fails, complete the post-installation steps on the Homebrew website. Then open a new Terminal window and run the command again.

5. Install the tools that QAequilibraE uses to build AequilibraE. Run::

    brew install uv llvm libspatialite

6. Continue with the :doc:`regular installation of QAequilibraE <getting_started>`.

Troubleshooting
---------------

If the build reports ``too many files are open``, do these steps:

1. Quit QGIS.

2. In Terminal, run::

    ulimit -n 10240

3. In the same Terminal window, start QGIS. Run::

    open -a QGIS

4. Install the QAequilibraE dependencies again.
