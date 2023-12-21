.. _getting_started:

Getting Started
===============

In this section we describe how you can install AequilibraE's QGIS plug-in.

.. note::

    The recommendations on this page are as current as of December 2023.

Installation
------------

AequilibraE is available from the QGIS plugin repository, and we recommend you
download it using the instructions below.

.. index:: installation

Step--by-step installation
~~~~~~~~~~~~~~~~~~~~~~~~~~

The steps for installing AequilibraE are the same as for any QGIS plugin.
Go to the Plugins panel and click on **Manage and Install Plugins**.

.. image:: ../images/install_1.png
    :width: 1181
    :align: center
    :alt: First step

.. image:: ../images/install_2.png
    :width: 1035
    :align: center
    :alt: Second step

.. image:: ../images/install_3.png
    :width: 1226
    :align: center
    :alt: Third step

After installing the plugin, you will be faced with the question of whether you
want to download its dependencies, which are required for using most of the
features. The problem is that many of AequilibraE's algorithms rely on compiled
extensions, but it is against the QGIS's community guidelines to upload binaries
to the repository.

.. image:: ../images/install_4.png
    :width: 400
    :align: center
    :alt: Fourth step

If you select to download the packages, QGIS will freeze for a few seconds before
showing the image below.

.. image:: ../images/install_5.png
    :width: 380
    :align: center
    :alt: Fifth step

Otherwise, a message warning about installation problems will be shown, and your
plugin will be non-functional.

.. image:: ../images/install_6.png
    :width: 492
    :align: center
    :alt: Sixth step

.. _quicktour_video:

Quick Tour
----------

After installing AequilibraE plug-in, you might enjoy this quick tour on QGIS interface.
Latest versions of AequilibraE for QGIS have brought substantial changes over to the
software operation and interface, which might cause some confusion to old users. For a brief overview
of the new interface, we have prepared a little video tour.

.. raw:: html

    <iframe width="560" height="315" src="https://www.youtube.com/embed/oZEcjiBRaok"
     frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope;
     picture-in-picture" allowfullscreen></iframe>
