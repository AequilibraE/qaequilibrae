macOS installation
==================

For Linux and Windows, AequilibraE builds "wheels", pre-compiled packages of
AequilibraE. On macOS, QAequilibraE build AequlibraE from source. This requires
the same tools that are used to build AequilibraE usually. We install these
first, then the QAequilibraE will build and install the packages it requires.   

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

6. Continue with the `regular installation of QAequilibraE <getting_started.rst>`_.

Troubleshooting
---------------

If the build reports ``too many files are open``, do these steps:

1. Quit QGIS.

2. In Terminal, run::

    ulimit -n 10240

3. In the same Terminal window, start QGIS. Run::

    open -a QGIS

4. Install the QAequilibraE dependencies again.
