.. _getting_started:

Getting Started
===============

In this section we describe how you can install AequilibraE's QGIS plug-in.

.. note::

    The recommendations on this page are as current as of May 2023.

Installation
------------

AequilibraE is available from the QGIS plugin repository, and we recommend you
download it using the instructions below.

.. index:: installation

Step--by-step installation
~~~~~~~~~~~~~~~~~~~~~~~~~~

The steps for installing AequilibraE are the same as for any QGIS plugin

.. image:: ../images/install_1.png
    :width: 1181
    :align: center
    :alt: First step


.. image:: ../images/install_2.png
    :width: 1035
    :align: center
    :alt: Second step


.. image:: ../images/install_3.png
    :width: 1062
    :align: center
    :alt: Third step

.. note::
   The latest version of the AequilibraE plugin is released as experimental, and
   stable versions older than 0.5 are substantially less capable than the latest
   version, therefore we recommend you using at least version 0.6, even if that
   means using an experimental one, which you can select by checking the box
   for experimental plugins within the QGIS plugin manager.

.. image:: ../images/install_4.png
    :width: 1234
    :align: center
    :alt: Fourth step


.. image:: ../images/install_5.png
    :width: 1226
    :align: center
    :alt: Fifth step


If you get the message below when you try to run one of AequilibraE's tools, it
is because you are missing some files.


.. image:: ../images/no_binaries_error.png
    :width: 1099
    :align: center
    :alt: no_binaries_error

The problem is that many of AequilibraE's algorithms rely on compiled
extensions, but it is against the QGIS's community guidelines to upload binaries
to the repository.

In order to comply with that rule without losing functionality, we ask you to
download such binaries after installing the QGIS, which can be done in the
AequilibraE menu, but it does require restarting QGIS


.. image:: ../images/install_6.png
    :width: 492
    :align: center
    :alt: Sixth step


.. image:: ../images/install_7.png
    :width: 675
    :align: center
    :alt: Seventh step


.. image:: ../images/install_8.png
    :width: 969
    :align: center
    :alt: Eighth step


Now it is just a matter of re-starting QGIS and starting to use AequilibraE.

.. _importing-omx-matrices:

For those who want to be able to use matrices in the OpenMatrix (*.omx) format,
then you still need to install the openmatrix package.  If you are in Linux or
Mac, then a simple

::

    pip install openmatrix

should suffice.

However, if you are a Windows user, things are a little more convoluted. The
best way of doing it is to run QGIS as an administrator and click on *install*
*extra packages* from the AequilibraE menu, as shown below.

.. image:: ../images/install_extra_packages.png
    :width: 781
    :align: center
    :alt: Extra packages

You will be asked to confirm your actions before AequilibraE attempts to install
openmatrix with the screen shown below.

.. image:: ../images/install_extra_packages_confirmation.png
    :width: 818
    :align: center
    :alt: Confirmation

If you have correctly installed it, the logging screen will clearly state that
the process was successful, as shown below

.. image:: ../images/install_extra_packages_success.png
    :width: 971
    :align: center
    :alt: Success

And it would report failure in case something has gone wrong.

.. image:: ../images/install_extra_packages_failure.png
    :width: 968
    :align: center
    :alt: Failure

A more detailed discussion on how this process works has been presented in the
form of a blog post on
`XL-Optim <https://www.xl-optim.com/displaying-omx-matrix-in-qgis/>`_.

.. _quicktour-video:

Quick Tour
----------

After installing AequilibraE plug-in, you might enjoy this quick tour on QGIS interface.
AequilibraE 0.6 for QGIS has brought substantial changes to the previous graphical
interface, which might cause some confusion to old users. For a brief overview
of the new interface, we have prepared a little video tour.

.. raw:: html

    <iframe width="560" height="315" src="https://www.youtube.com/embed/oZEcjiBRaok"
     frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope;
     picture-in-picture" allowfullscreen></iframe>
