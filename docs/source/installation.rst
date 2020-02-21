
Installation
============

AequilibraE is available from the QGIS plugin repository, and we recommend you to download using the instructions below.

.. index:: installation

Step--by-step installation
--------------------------

The steps for installing AequilibraE are the same as for any QGIS plugin

.. image:: images/install_1.png
    :width: 1181
    :align: center
    :alt: First step


.. image:: images/install_2.png
    :width: 1035
    :align: center
    :alt: Second step


.. image:: images/install_3.png
    :width: 1062
    :align: center
    :alt: Third step

.. note::
   The latest version of the AequilibraE plugin is released as experimental, and
   stable versions older than 0.5 are substantially less capable than the latest
   version, therefore we recommend you using at least version 0.6, even if that
   means using an experimental one, which you can select by checking the box
   for experimental plugins within the QGIS plugin manager.

.. image:: images/install_4.png
    :width: 1234
    :align: center
    :alt: Fourth step


.. image:: images/install_5.png
    :width: 1226
    :align: center
    :alt: Fifth step


If you get the message below when you try to run one of AequilibraE's tools, it is because you are missing some files.


.. image:: images/no_binaries_error.png
    :width: 1099
    :align: center
    :alt: no_binaries_error

The problem is that many of AequilibraE's algorithms rely on compiled extensions, but it is against the QGIS's community
guidelines to upload binaries to the repository.

In order to comply with that rule without losing functionality, we ask you to
download such binaries after installing the QGIS, which can be done in the AequilibraE menu, but it does require
restarting QGIS


.. image:: images/install_6.png
    :width: 492
    :align: center
    :alt: Sixth step


.. image:: images/install_7.png
    :width: 675
    :align: center
    :alt: Seventh step


.. image:: images/install_8.png
    :width: 800
    :align: center
    :alt: Eighth step


Now it is just a matter of re-starting QGIS and starting to use AequilibraE