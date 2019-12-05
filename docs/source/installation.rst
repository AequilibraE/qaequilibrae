
Installation
============

AequilibraE is available from the QGIS plugin repository, and we recommend you to download using the instructions below.

.. note::
   For now there is only a experimental version of AequilibraE for QGIS 3, but we plan to always have a more stable
   version and an experimental one with all the bleeding edge developments.


.. index:: installation

Step--by-step installation
--------------------------

The steps for installing AequilibraE are the same as for any QGIS plugin

.. image:: images/install_1.png
    :width: 800
    :align: center
    :alt: First step


.. image:: images/install_2.png
    :width: 800
    :align: center
    :alt: Second step


.. image:: images/install_3.png
    :width: 800
    :align: center
    :alt: Third step

.. note::
    In case you are looking for bleeding edge versions of AequilibraE and are not afraid of a crash here and there (or
    want to help by testing these versions), you can do so by checking the box for experimental plugins within the QGIS
    plugin manager.

.. image:: images/install_4.png
    :width: 800
    :align: center
    :alt: Fourth step


.. image:: images/install_5.png
    :width: 800
    :align: center
    :alt: Fifth step


If you get the message below when you try to run one of AequilibraE's tools, it is because you are missing some files.


.. image:: images/no_binaries_error.png
    :width: 800
    :align: center
    :alt: no_binaries_error

The problem is that many of AequilibraE's algorithms rely on compiled extensions, but it is against the QGIS's community
guidelines to upload binaries to the repository.

In order to comply with that rule without losing functionality, we ask you to
download such binaries after installing the QGIS, which can be done in the AequilibraE menu, but it does require
restarting QGIS


.. image:: images/install_6.png
    :width: 800
    :align: center
    :alt: Sixth step


.. image:: images/install_7.png
    :width: 800
    :align: center
    :alt: Seventh step


.. image:: images/install_8.png
    :width: 800
    :align: center
    :alt: Eighth step


Now it is just a matter of re-starting QGIS and starting to use AequilibraE