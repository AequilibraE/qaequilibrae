:orphan:

.. _contributing_to_qaequilibrae:

Contributing to AequilibraE for QGIS
====================================

This page presents some initial instructions on how to setup your system to start contributing to QAequilibraE 
and lists the requirements for all pull-requests to be merged into main.

Software Design and requirements
--------------------------------

QAequilibraE is built on top of AequilibraE's main features, and the most important piece of AequilibraE's backend 
is, without a doubt, `NumPy <http://numpy.org>`_.

The user might not see or know, but whenever vectorization is not possible through the use of NumPy functions, 
compiled code written in `Cython <https://cython.org/>`_ is developed in order to accelerate computation.

QAequilibraE also observes a strong requirement of only using libraries that are available in
the Python installation used by `QGIS <https://qgis.org/en/site/>`_ on Windows.

We have not yet found an ideal source of recommendations for developing QAequilibraE, but a
good initial take can be found in `this article <https://doi.org/10.1371/journal.pbio.1001745>`_.

Please notice that QAequilibraE installation MUST WORK at least in the most recent long-term
release (LTR).

Developing QAequilibraE
-----------------------

We recommend using a dedicated virtual environment to develop QAequilibraE, using the
version of Python related to the most recent QGIS long-term release. When this section
was updated (October/2025),LTR 3.40.12 was coming with a default 3.12.11 Python environment.

We also assume you are using one of `PyCharm <https://www.jetbrains.com/pycharm>`_ or 
`VSCode <https://code.visualstudio.com/>`_, which are good IDEs for Python. If you are using
a different IDE, we would welcome if you could contribute with instructions to set that up.

(For us,) The easiest way of developing a QGIS plugin is using a Docker container to build
an image containing a QGIS installation. When cloning QAequilibraE repository into your local
machine you will find a ``Dockerfile`` with this recipe. ::

  git clone https://github.com/AequilibraE/qaequilibrae.git

Then all you have to do is activate the virtual environment and adding the environmental variables.
Without adding these variables, your installation of AequilibraE in QGIS is goint to be useless.

We understood that the creation of a virtual development environment within a container would be
redundant, however after facing some developing issues related to 
`PEP 668 <https://peps.python.org/pep-0668/>`_, we believe that using a virtual environment would
be a good practice.

.. code-block::

    . .venv/bin/activate
    export PYTHONPATH=$(pwd)/qaequilibrae/packages:$PYTHONPATH
    export QT_QPA_PLATFORM=offscreen

If you have to test changes in QAequilibraE after its installed in QGIS, we strongly recommend
using the `Plugin Reloader <https://plugins.qgis.org/plugins/plugin_reloader/>`_, a plugin to
reload another plugins.

Developing QAequilibraE and AequilibraE simultaneously
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a very specific case for features that are being developed simultaneously in the Python
package and in the QGIS interface. Here, we need to create a symbolic link that reflects the
changes in AequilibraE within QGIS. The following step-by-step instructions are for a Windows
operating system (if you are using a different operating system, contributions to this
documentation are welcome).

First, let's create a virtual environment for AequilibraE.

.. code-block::

    python -m venv .venv
    . .venv/bin/activate
    pip install -U pip uv

    # Check the branch you are going to install
    git status
    git pull

    # Install AequilibraE in an editable version
    uv pip install -e .

Open PowerShell as administrator.

.. code-block::

    # Navigate to where your QGIS plugins are
    cd C:\Users\renat\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins

    # Create the symbolic link
    New-Item -Path ./qaequilibrae -ItemType SymbolicLink -Value C:\Users\renat\Documents\GitHub\qaequilibrae\qaequilibrae

Proceed with the QAequilibraE installation in QGIS normally. Then, navigate to the folder
where your plugin was installed and delete the AequilibraE folders. Return to the AequilibraE
virtual environment.

.. code-block::

    # Install AequilibraE in QAequilibraE
    uv pip install . --target C:\Users\renat\Documents\GitHub\qaequilibrae\qaequilibrae\packages --no-deps

This approach for installing AequilibraE in QAequilibraE has a major disadvantage: whenever
there is a change in AequilibraE, it is necessary to reinstall it, however this is the
simplest configuration for this case.

Developing QAequilibraE with AequilibraE's develop
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are two different scenarios: 1) you will develop updates in QAequilibraE based on
AequilibraE's develop branch, or 2) you will test in QGIS (software) whether what you did in
the development environment actually works.

The first case is very simple: we install the develop branch in the qaequilibrae/packages
folder and clean up the installation of redundant packages in QGIS. "But wouldn't it be 
easier to just install AequilibraE directly in the virtual environment and call it a day?" 
Yes, but this way, we wouldn't be developing and testing the plugin in the way it is actually
used.

.. code-block::

    python -m uv pip install "git+https://github.com/AequilibraE/aequilibrae@develop" --target qaequilibrae/packages
    python -c "from qaequilibrae.download_extra_packages_class import DownloadAll; DownloadAll().clean_packages('qaequilibrae/packages')" 

For the second case, I'm assuming you will test the installation from the QAequilibraE ZIP file.
If I'm not mistaken, these git installation operations are not permitted in QGIS, so an
alternative is to install the AequilibraE binary, available as an artifact of the 
`Build workflow <https://github.com/AequilibraE/aequilibrae/actions/workflows/build_wheels.yml>`_.
Look for the one that corresponds to develop and matches your operating system.

And how do we install this in QGIS? The alternative is to install QAequilibraE from a ZIP file and,
initially, cancel the installation of additional packages. An error message reporting that
QAequilibraE will not work is displayed, but we can ignore it for now. Go ahead and close QGIS as
well. The next operations are performed in the OS4GEO shell.

.. code-block::
    
    # Check the QGIS python version to be sure which wheel is going to be installed
    python --version

    # Navigate to where your wheels are stored
    cd C:\Users\renat\Downloads\aequilibrae_wheels

    # And install it at the 'packages' folder inside QAequilibraE, just like we did before.
    python -m pip install aequilibrae-1.5.0-cp312-cp312-win_amd64.whl --target "C:\Users\renat\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\qaequilibrae\packages"

Reopen QGIS. QAequilibraE will ask you again if you want to install the additional packages.
This time answer yes and let QAequilibraE automatically remove the installation of duplicate
packages. If your installation runs without errors, the plugin will be available for use
containing the develop version of AequilibraE; otherwise, check the error message on the screen.

Development Guidelines
----------------------

QAequilibraE development (tries) to follow a few standards. A huge effort is being undertaken
by the development team to update several portions of the code are still not up to such standards.

We try as much as possible to use built-in QGIS tools to develop QAequilibraE. If you need
a guide to develop, try the 
`QGIS testing developer cookbook <https://docs.qgis.org/testing/pdf/en/QGIS-testing-PyQGISDeveloperCookbook-en.pdf>`_
or the `QGIS Python API documentation <https://qgis.org/pyqgis/3.40/#>`_. These two are
going to be your development life jackets.

Style
~~~~~

* Python code should follow (mostly) the `pycodestyle style guide <https://pycodestyle.pycqa.org/en/latest/>`_.
* Python docstrings should follow the `reStructuredText Docstring Format <https://www.python.org/dev/peps/pep-0287/>`_.
* We are big fans of auto-code formatting. For that, we use `Black <https://black.readthedocs.io/en/stable/>`_.
* Negating some of what we have said so far, we use maximum line length of 120 characters.

Imports
~~~~~~~

* Imports should be one per line.
* Imports should be grouped into standard library, third-party, and intra-library imports. 
* Imports of NumPy should follow the following convention:

::

    import numpy as np

Translatable Strings
~~~~~~~~~~~~~~~~~~~~

If you are adding or modifying any piece of QAequilibraE's code that includes translatable strings,
which are the strings displayed in the widget windows, please ensure you use the ``tr`` function
to locate the strings. This will guarantee that the strings are included in our future
translations. Currently, only classes that have a ``self`` method support the localization of
strings.

::

    # Indicates that the message "You need at least three centroids to route." will be
    # set for translation.
    self.iface_error_message(self.tr("You need at least three centroids to route."))

    # In case you have to insert any text into a string, the best way is to use string format
    self.error = self.tr("ID {} is non unique in your selected field").format(str(id))

Strings in QAequilibraE Processing Provider can also be translated. To indicate the strings,
import the translation function and configure it to return the context and the message.

::
  
   from qaequilibrae.i18n.translate import trlt

   class YourClassHere():
      ...
      # YourClassHere functions
      ...
      def processAlgorithm(self, parameters, context, model_feedback):
        ...
        feedback.pushInfo(self.tr("Running assignment"))  # indicates the translatable string
        ...

      def tr(self, message):
        return trlt("TrafficAssignYAML", message)

QAequilibraE's translations are all hosted in 
`Transifex <https://explore.transifex.com/aequilibrae/qaequilibrae/>`_. If you want to contribute
to QAequilibraE by translating the plugin to other languages or reviewing the existing
translations, please let us know in our 
`AequilibraE Google Group <https://groups.google.com/forum/#!forum/aequilibrae>`_. Feel free to
request another languages for translation!

In the :ref:`plugin internationalization <plugin_i18n>` page, you can find more information on
creating your account and start translating QAequilibraE.

Contributing to AequilibraE for QGIS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

GitHub has a nice visual explanation on how collaboration is done `GitHub Flow
<https://guides.github.com/introduction/flow>`_. (For us,) The most important points there are:

* The main branch contains the latest working/release version of QAequilibraE
* Work is done in an issue/feature branch (or a fork) and then pushed to a new branch
* Automated testing is run using Github Actions. All tests must pass:

  * Unit testing
  * Build/packaging tests
  * Documentation building test

* If the tests pass, then a manual pull request can be approved to merge into main
* The main branch is protected and therefore can only be written to after the code has been
  reviewed and approved
* No individual has the privileges to push to the main branch

Release versions
~~~~~~~~~~~~~~~~

For the past few years, QAequilibraE's release versioning was related to the major and minor
releases in AequilibraE. If you frequently update your plugin, you might have noticed that
we recently jumped from v1.3.1 to v1.4.3, without any micro releases in between, just because
these were the most recent AequilibraE version when the releases happened.

To add the :ref:`Plugin Repository <plugin_repository>` feature, the development team decided
to change how the QAequilibraE versioning is done. We'll move from version tags based on
AequilibraE, for time-based tags when the release is made (so don't be scared if you see a 
version such as 25.192.23).

We'll continue using the de-facto Python standard for
`versioning <https://the-hitchhikers-guide-to-packaging.readthedocs.io/en/latest/specification.html>`_,
but with a different version scheme. 

::

  MAJOR.MINOR[.MICRO]

- MAJOR designates the year of the release

- MINOR designates the number of the day in the year

- MICRO designates the hour of the day the release was made

Testing
~~~~~~~

QAequilibraE testing is done with some tools:

* `Black <https://black.readthedocs.io/en/stable/>`_, the uncompromising code formatter
* `Ruff <https://docs.astral.sh/ruff/>`_, a linter and code formatter
* `pytest <http://pytest.org/latest/>`_, a Python testing tool
* `pytest-cov <https://pytest-cov.readthedocs.io/en/latest/index.html>`_, a tool for measuring test code coverage
* `pytest-qt <https://pytest-qt.readthedocs.io/en/latest/index.html>`_, a tool for testing PyQt5 applications
* `pytest-qgis <https://pypi.org/project/pytest-qgis/>`_, a tool for writing QGIS tests

To run the tests locally, you will need to figure out what to do...

These same tests are run by GitHub Actions with each push to the repository. These tests need to pass in order to 
somebody manually review the code before merging it into main (or returning for corrections).

In some cases, test targets need to be updated to match the new results produced by the code since these 
are now the correct results. In order to update the test targets, first determine which tests are 
failing and then review the failing lines in the source files. These are easy to identify since each 
test ultimately comes down to one of Python's various types of ``assert`` statements. Once you identify 
which ``assert`` is failing, you can work your way back through the code that creates the test targets in 
order to update it. After updating the test targets, re-run the tests to confirm the new code passes all 
the tests.

.. tip::

    If you want to check if the test values are at the right place in the UI, `qtbot` can help you.
    Add `qtbot` in the function definition and take a screenshot of the UI. To visualize it, don't
    forget to use a print statement.

    .. code-block::

        path = qtbot.screenshot(dialog)
        print(path)

Documentation
~~~~~~~~~~~~~

All the QAequilibraE documentation is (unfortunately) written in `reStructuredText
<http://docutils.sourceforge.net/rst.html>`_ and built with `Sphinx <http://www.sphinx-doc.org/en/stable/>`_.
Although reStructuredText is often unnecessarily convoluted to write, Sphinx is capable of converting it to 
standard-looking HTML pages, while also bringing the docstring documentation along for the ride.

Build the documentation in HTML format with the following commands run from the ``root`` folder.
The Dockerfile has already installed the documentation packages in your virtual environment.

.. code-block::

    . .venv/bin/activate
    
    # Replace the variables if needed
    export LANG=C.UTF-8
    export LC_ALL=C.UTF-8

    cd docs
    make html

Finally
~~~~~~~

A LOT of the structure around the documentation was borrowed (copied) from the excellent project `ActivitySim
<https://activitysim.github.io/>`_.