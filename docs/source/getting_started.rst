Getting Started
===============

In this section we describe how you can install AequilibraE's QGIS plugin.

.. note::

    The recommendations on this page are as current as of April 2024.

Installation
------------

AequilibraE is available from the QGIS plugin repository, and we recommend you
download it using the instructions below.

.. index:: installation

Step-by-step installation
~~~~~~~~~~~~~~~~~~~~~~~~~~

The steps for installing AequilibraE are the same as for any QGIS plugin.
Go to the Plugins panel and click on **Manage and Install Plugins**.

.. _fig_plugins_menu:

.. image:: images/getting_started_1.png
    :align: center
    :alt: First step

In the tab *All*, search for QAequilibraE.

.. image:: images/getting_started_2.png
    :align: center
    :alt: Second step

After selecting the plugin installation, you will be faced with the question of whether you
want to download its dependencies, which are required for using most of the
features. This is necessary because AequilibraE's algorithms rely on compiled
extensions, but it is against the QGIS's community guidelines to upload binaries
to the repository.

.. image:: images/getting_started_3.png
    :align: center
    :alt: Third step

If you select to download the packages, QGIS will freeze for a few seconds before
showing the image below.

.. image:: images/getting_started_4.png
    :align: center
    :alt: Fourth step

Otherwise, a message warning about installation problems will be shown, and your
plugin will be non-functional.

.. image:: images/getting_started_5.png
    :align: center
    :alt: Fifth step

.. _plugin_repository:

Plugin Repository
-----------------

With the plugin repository, it is now possible to use the latest version in develop without waiting
for the next release!

To configure it, let's go once again to the Plugins menu, as shown :ref:`here <fig_plugins_menu>`.

Select the **Settings** tab and check the box for **Show also experimental plugins** (step 1). The
versions of QAequilibraE made available at the plugin store are not the versions for release
and are labelled as experimental. 

.. image:: images/getting_started_7.png
    :align: center
    :alt: Plugins settings tab configuration

Then, click on the **Add** button (step 2). A new window will open. Fill the name and URL fields 
with the following data:

.. code-block::
    :caption: Plugin Repository

    name: qaequilibrae
    URL: https://aequilibrae.com/develop/qgis/_static/plugin.xml

Then, just click on the **OK** button.

.. image:: images/getting_started_8.png
    :align: center
    :alt: Plugins settings repository details

The QGIS is going to validate the provided URL. It should be really quick. You'll notice that
qaequilibrae is now appearing at your plugin repositories.

.. image:: images/getting_started_9.png
    :align: center
    :alt: Plugins settings updated plugin repositories

Finally, select the **Upgradeable** tab. You'll notice that QAequilibraE has a newer version to
be installed. Click on **qaequilibrae**, and hit the **Upgrade Experimental Plugin** button.
The installation process should be the same as above, as you need to allow the installation
of external libraries.

.. image:: images/getting_started_10.png
    :align: center
    :alt: Plugins upgradeable

If you have any problems with this step, please check the 
`official QGIS documentation <https://docs.qgis.org/3.40/en/docs/training_manual/qgis_plugins/fetching_plugins.html#follow-along-configuring-additional-plugin-repositories>`_.

Saving as QGIS Project
----------------------

Since version 1.0.1, our users can save their on-going projects directly through the QGIS saving menu! 
This feature allows you to save both your AequilibraE project and temporary layers. The temporary layers
are stored in **qgis_layer.sqlite**, a database automatically created to store these layers. All you have 
to do is go to the Project panel and select **Save** or **Save as**, indicate where you want to store 
your project file, and press save!

.. image:: images/getting_started_6.png
    :align: center
    :alt: Saving file

In the interest of data integrity, if you have open AequilibraE layers into your QGIS Project and close 
the AequilibraE project, these layers are removed from your open QGIS project.

When reopening the QGIS project containing an AequilibraE model, you will notice that the project 
stored is automatically reopened by QAequilibraE.

.. .. _quicktour_video:

.. Quick Tour
.. ----------

.. After installing AequilibraE plugin, you might enjoy this quick tour on QGIS interface.
.. Latest versions of AequilibraE for QGIS have brought substantial changes over to the
.. software operation and interface, which might cause some confusion to old users. For a brief overview
.. of the new interface, we have prepared a little video tour.

.. .. raw:: html

..     <iframe width="560" height="315" src="https://www.youtube.com/embed/oZEcjiBRaok"
..      frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope;
..      picture-in-picture" allowfullscreen></iframe>
