.. _contributing_to_qaequilibrae:

Contributing to AequilibraE for QGIS
====================================

This page presents some initial instructions on how to setup your system to start contributing to AequilibraE and lists
the requirements for all pull-requests to be merged into master.

Software Design and requirements
--------------------------------

The most important piece of AequilibraE's backend is, without a doubt, `NumPy <http://numpy.org>`_.

Whenever vectorization is not possible through the use of NumPy functions, compiled code is developed in order to
accelerate computation. All compiled code is written in `Cython <https://cython.org/>`_.

AequilibraE also observes a strong requirement of only using libraries that are available in the Python installation
used by `QGIS <https://qgis.org/en/site/>`_ on Windows, as the most important use case of this library is as the computational
backend of the AequilibraE GUI for QGIS. This requirement can be relaxed, but it has to be analysed on a base-by-case
basis and CANNOT break current workflow within QGIS.

We have not yet found an ideal source of recommendations for developing AequilibraE, but a good initial take can be
found in `this article <http://www.plosbiology.org/article/info%3Adoi%2F10.1371%2Fjournal.pbio.1001745>`_.

Development Install
-------------------

As it goes with most Python packages, we recommend using a dedicated virtual environment to develop AequilibraE.

AequilibraE is currently tested for Python 3.9, 3.10, 3.11 & 3.12, but we recommend using Python 3.9 or 3.10 for development.

We also assume you are using `PyCharm <https://www.jetbrains.com/pycharm>`_, which is an awesome IDE for Python.

If you are using a different IDE, we would welcome if you could contribute with instructions to set that up.

Cloning the computational engine as submodule
---------------------------------------------

:: 

  git submodule update --init --recursive

  git submodule update --recursive --remote


Non-Windows
~~~~~~~~~~~
::

  ./ci.sh setup_dev

Windows
~~~~~~~

Make sure to clone the AequilibraE repository and run the following from within that cloned repo using an elevated
command prompt.

Python 3.6 needs to be installed, and the following instructions assume you are using `Chocolatey
<https://chocolatey.org/>`_ as a package manager.
::

    cinst python3 --version 3.6.8
    cinst python

    set PATH=C:\Python36;%PATH%
    python -m pip install pipenv
    virtualenv .venv
    python -m pipenv install
    python -m pipenv run pre-commit-install

Setup Pycharm with the virtual environment you just created.

::

    Settings -> Project -> Project Interpreter -> Gear Icon -> Add -> Existing VEnv


Development Guidelines
-----------------------

AequilibraE development (tries) to follow a few standards. Since this is largely an after-the-fact concern, several
portions of the code are still not up to such standards.

Style
~~~~~~

* Python code should follow (mostly) the `pycodestyle style guide <https://pypi.python.org/pypi/pycodestyle>`_
* Python docstrings should follow the `reStructuredText Docstring Format <https://www.python.org/dev/peps/pep-0287/>`_
* We are big fans of auto-code formatting. For that, we use `Black <https://github.com/ambv/black>`_
* Negating some of what we have said so far, we use maximum line length of 120 characters

Imports
~~~~~~~

* Imports should be one per line.
* Imports should be grouped into standard library, third-party, and intra-library imports. 
* Imports of NumPy should follow the following convention:

::

    import numpy as np

Translatable Strings
~~~~~~~~~~~~~~~~~~~~

If you are adding or modifying any piece of QAequilibraE's code that includes translatable strings, which are the
strings displayed in the widget windows, please ensure you use the ``tr`` function to locate the strings. This will 
guarantee that the strings are included in our future translations. Currently, only classes that have a ``self`` method 
support the localization of strings.

::

    # Indicates that the message "You need at least three centroids to route. " will be
    # set for translation.
    qgis.utils.iface.messageBar().pushMessage(self.tr("You need at least three centroids to route. "), "", level=3)

    # In case you have to insert any text into a string, the best way is to use string format
    self.error = self.tr("ID {} is non unique in your selected field").format(str(i_d))

Strings in QAequilibraE Processing Provider can also be translated. To indicate the strings, import the translation
function and configure it to return the context and the message.

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

As for June 2024, QAequilibraE's translations are all hosted in 
`Transifex <https://explore.transifex.com/aequilibrae/qaequilibrae/>`_. Currently, we are targeting translations
in Brazilian Portuguese, Chinese, French, German, Italian, and Spanish. If you want to contribute to QAequilibraE 
by translating the plugin to other languages or reviewing the existing translations, please let us know in our 
`AequilibraE Google Group <https://groups.google.com/forum/#!forum/aequilibrae>`_,
so we can add your language to our translation pool!

In the :ref:`plugin internationalization <plugin_i18n>` page, you can find more information on creating your account and
start translating QAequilibraE.

Contributing to AequilibraE for QGIS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

GitHub has a nice visual explanation on how collaboration is done `GitHub Flow
<https://guides.github.com/introduction/flow>`_. (For us,) The most important points there are:

* The master branch contains the latest working/release version of AequilibraE
* Work is done in an issue/feature branch (or a fork) and then pushed to a new branch
* Automated testing is run using Github Actions. All tests must pass:

  * Unit testing
  * Build/packaging tests
  * Documentation building test

* If the tests pass, then a manual pull request can be approved to merge into master
* The master branch is protected and therefore can only be written to after the code has been reviewed and approved
* No individual has the privileges to push to the master branch

Release versions
~~~~~~~~~~~~~~~~~

AequilibraE uses the de-facto Python standard for `versioning
<http://the-hitchhikers-guide-to-packaging.readthedocs.io/en/latest/specification.html>`_

::

  MAJOR.MINOR[.MICRO]

- MAJOR designates a major revision number for the software. Usually, raising a major revision number means that
  you are adding a lot of features, breaking backward-compatibility or drastically changing the API.

- MINOR usually groups moderate changes to the software like bug fixes or minor improvements. Most of the time, end \
  users can upgrade with no risks their software to a new minor release. In case an API changes, the end users will be \
  notified with deprecation warnings. In other words, API stability is usually a promise between two minor releases.

- Some software use a third level: MICRO. This level is used when the release cycle of minor release is quite long.
  In that case, micro releases are dedicated to bug fixes.

AequilibraE's development is happening mostly within the Minor and Micro levels, as we are still in version 0

Testing
~~~~~~~~

AequilibraE testing is done with three tools:

* `flake8 <https://pypi.org/project/flake8/>`_, a tool to check Python code style
* `pytest <http://pytest.org/latest/>`_, a Python testing tool
* `pytest-cov <https://pytest-cov.readthedocs.io/en/latest/index.html>`_, a tool for measuring test code coverage

To run the tests locally, you will need to figure out what to do...

These same tests are run by GitHub Actions with each push to the repository. These tests need to pass in order to 
somebody manually review the code before merging it into master (or returning for corrections).

In some cases, test targets need to be updated to match the new results produced by the code since these 
are now the correct results. In order to update the test targets, first determine which tests are 
failing and then review the failing lines in the source files. These are easy to identify since each 
test ultimately comes down to one of Python's various types of ``assert`` statements. Once you identify 
which ``assert`` is failing, you can work your way back through the code that creates the test targets in 
order to update it. After updating the test targets, re-run the tests to confirm the new code passes all 
the tests.

Documentation
~~~~~~~~~~~~~~

All the AequilibraE documentation is (unfortunately) written in `reStructuredText
<http://docutils.sourceforge.net/rst.html>`_ and built with `Sphinx <http://www.sphinx-doc.org/en/stable/>`_.
Although Restructured Text is often unnecessarily convoluted to write, Sphinx is capable of converting it to 
standard-looking HTML pages, while also bringing the docstring documentation along for the ride.

To build the documentation, first make sure the required packages are installed::

    pip install sphinx pydata-sphinx-theme sphinx-gallery sphinx-design sphinx-panels sphinx-subfigure

Next, build the documentation in HTML format with the following commands run from the ``root`` folder::

    cd docs
    make html

Releases
~~~~~~~~~

AequilibraE releases are manually (and not often) uploaded to the `Python Package Index
<https://pypi.python.org/pypi/aequilibrae>`_ (pypi).


Finally
~~~~~~~~~

A LOT of the structure around the documentation was borrowed (copied) from the excellent project `ActivitySim
<https://activitysim.github.io/>`_.