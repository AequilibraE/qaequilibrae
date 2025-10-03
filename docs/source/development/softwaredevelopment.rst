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

Este caso é bem específico para features que são desenvolvidas simultâneamente no pacote Python
e na interface do QGIS. Aqui, precisamos criar um link simbólico que reflita as mudanças no
AequilibraE dentro do QGIS. O passo-a-passo a seguir é realizado em um sistema operacional
Windows (caso utilize outro sistema operacional a contribuição para esta documentação é bem-vinda).

Primeiramente, vamos criar um ambiente virtual para o AequilibraE. 

.. code-block::

    python3 -m venv .venv
    . .venv/bin/activate

    # Check the branch you are going to install
    git status
    git pull

    # Install AequilibraE in QAequilibraE
    pip install . -t /mnt/c/Users/renat/Documents/GitHub/qaequilibrae/qaequilibrae/packages

Abra o PowerShell como administrador.

.. code-block::

    # Navigate to where your QGIS plugins are
    cd C:\Users\renat\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins

    # Create the symbolic link
    New-Item -Path ./qaequilibrae -ItemType SymbolicLink -Value C:\Users\renat\Documents\GitHub\qaequilibrae\qaequilibrae

Depois disso, prossiga com a instalação do QAequilibraE em QGIS normalmente.

Esta abordagem de instalação do AequilibraE no QAequilibraE apresenta uma grande desvantagem:
sempre que houver mudança no AequilibraE, é necessário reinstalá-lo, porém é a configuração
mais simples para este caso.

Developing QAequilibraE with AequilibraE's develop
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

São dois cenários diferentes 1) você vai desenvolver atualizações no QAequilibraE com base na
develop do AequilibraE ou 2) você vai testar no QGIS (software) se o que você fez na área de
desenvolvimento de fato funciona.

O primeiro caso é muito simples: instalamos a branch develop na pasta ``qaequilibrae/packages``
e limpamos a instalação de pacotes redundantes no QGIS. "Nossa Renata, mas não é mais fácil só
instalar o AequilibraE direto no ambiente virtual e correr pro abraço"? Sim, mas dessa forma,
não estaríamos desenvolvendo e testando o plugin da forma como ele é utilizado.

.. code-block::

    python -m uv pip install "git+https://github.com/AequilibraE/aequilibrae@develop" --target qaequilibrae/packages
    python -c "from qaequilibrae.download_extra_packages_class import DownloadAll; DownloadAll().clean_packages('qaequilibrae/packages')" 

Para o segundo caso, estou presumindo que você vai testar a instalação a partir do ZIP do
QAequilibraE. Se não me engano, essas operações de instalar a partir do git não são permitidas
no QGIS, logo uma alternativa é instalar o binário do AequilibraE, disponível como um artefato
na página de `execução dos testes de construção do pacote <https://github.com/AequilibraE/aequilibrae/actions/workflows/build_wheels.yml>`_.
Procure o que corresponde a develop e se encaixa no seu sistema operacional.

E como vamos instalar isso no QGIS? A alternativa é instalar o QAequilibraE a partir de um arquivo
ZIP e, no primeiro momento, cancelar a instalação dos pacotes adicionais. Uma mensagem de erro
reportando que o QAequilibraE não funcionará é mostrada, mas podemos ignorá-la por hora. Aproveite
e feche o QGIS também. As próximas operações são feitas no terminal do OS4GEO.

.. code-block::
    
    # Check the QGIS python version to be sure which wheel is going to be installed
    python --version

    # Navigate to where your wheels are stored
    cd C:\Users\renat\Downloads\aequilibrae_wheels

    # And install it at the 'packages' folder inside QAequilibraE, just like we did before.
    python -m pip install aequilibrae-1.5.0-cp312-cp312-win_amd64.whl --target "C:\Users\renat\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\qaequilibrae\packages"

Reabra o QGIS. O QAequilibraE te perguntará novamente se deseja a instalação dos pacotes
adicionais. Desta vez responda que sim e deixe o QAequilibraE remover a instalação de pacotes
duplicados automaticamente. Se sua instalação correr sem erros, o plugin estará disponível
para uso contendo a versão da develop do AequilibraE, caso contrário, verifique a mensagem
de erro na tela.

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

To build the documentation, first make sure the required packages are installed::

    pip install sphinx pydata-sphinx-theme sphinx-design sphinx-panels sphinx-subfigure

Next, build the documentation in HTML format with the following commands run from the ``root`` folder::

    cd docs
    make html

Finally
~~~~~~~

A LOT of the structure around the documentation was borrowed (copied) from the excellent project `ActivitySim
<https://activitysim.github.io/>`_.