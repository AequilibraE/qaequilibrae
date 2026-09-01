macOS installation
==================

QAequilibraE installs AequilibraE automatically on macOS. AequilibraE must be compiled
locally because version 1.7.0 does not provide a macOS wheel.

Install Homebrew and the required build tools in Terminal::

    brew install uv llvm libspatialite

If the Apple command-line tools are not installed, run::

    xcode-select --install

The QAequilibraE installer uses ``uv`` to create a temporary Python environment. It builds
the AequilibraE wheel in that environment, outside the signed QGIS Python process. It then
installs the wheel into QAequilibraE.

The installer configures the compiler and SpatiaLite paths automatically. It uses the LLVM
compiler, Homebrew's SpatiaLite library, and the Python version used by QGIS.

The build can take several minutes. QGIS may be unresponsive during this process. Keep the
QGIS **Log Messages** panel open if the installation fails. The **Messages** tab contains the
compiler output.

If the build reports that too many files are open, run this command in Terminal before starting
QGIS::

    ulimit -n 10240

Then start QGIS from that Terminal session.
