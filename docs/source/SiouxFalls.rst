Sioux Falls
===========

.. toctree::
   :maxdepth: 2

Sioux Falls has long been used as the standard example in transportation
network algorithm studies, and who are we to break that tradition?

Here we present an image-based example on a realistic modelling workflow
for the beginner modeler out there. All the data used here can be downloaded
at the :ref:`tutorial_sample_data` page.

As to not upset those who think that Sioux Falls is not a realist example (you
would be right to think so), the example data is also available for the Chicago
regional model, which has nearly 40,000 links and almost 1,800 zones.


Opening the project
-------------------

.. image:: images/opening_project.png
    :width: 560
    :align: center
    :alt: Opening the project


Traffic assignment with skimming
--------------------------------

.. image:: images/traffic_assignment.png
    :width: 783
    :align: center
    :alt: Calling assignment

.. image:: images/project_overview.png
    :width: 963
    :align: center
    :alt: Project overview

.. image:: images/traffic_open_matrix.png
    :width: 904
    :align: center
    :alt: Calling assignment

Matrices are provided in both OMX and AEM formats, so you are not required to
install openmatrix.

.. image:: images/choose_matrix.png
    :width: 1314
    :align: center
    :alt: Choose matrix

For this example, we only add one traffic class for mode **c** (car)

.. image:: images/add_traffic_class.png
    :width: 951
    :align: center
    :alt: Add traffic class


To select skims, we need to choose which fields/modes we will skim

.. image:: images/skim_field_selection.png
    :width: 896
    :align: center
    :alt: Skim selection

And if we want the skim for the last iteration (like we would for time) or if we
want it averaged out for all iterations (properly averaged, that is).

.. image:: images/skim_blended_versus_final.png
    :width: 898
    :align: center
    :alt: Skim iterations

The final step is to setup the assignment itself.

Here we select the fields for:

* link capacity
* link free flow travel time
* BPR's *alpha*
* BPR's *beta*

We also confirm the Relative gap and maximum number of iterations we want, the
assignment algorithm and the output folder.

.. image:: images/setup_assignment.png
    :width: 898
    :align: center
    :alt: Setup assignment


Plotting the flows
------------------

First we need to add the link flows CSV to the QGIS workspace

.. image:: images/add_layer.png
    :width: 173
    :align: center
    :alt: add_layer

.. image:: images/add_link_flows_to_map.png
    :width: 83
    :align: center
    :alt: add_link_flows_to_map

Then we join it with the link layer by accessing the link layer's properties

.. image:: images/layer_properties.png
    :width: 523
    :align: center
    :alt: layer_properties

.. image:: images/link_join.png
    :width: 1449
    :align: center
    :alt: link_join

Then we plot the flows

.. image:: images/select_stacked_bandwidth.png
    :width: 520
    :align: center
    :alt: select_stacked_bandwidth

.. image:: images/add_band.png
    :width: 760
    :align: center
    :alt: add_band

.. image:: images/create_bands.png
    :width: 737
    :align: center
    :alt: create_bands

And we can algo control the overall look of these bands (thickness and
separation between AB and BA flows) in the propect properties.

.. image:: images/project_properties.png
    :width: 421
    :align: center
    :alt: project_properties

.. image:: images/edit_variables.png
    :width: 886
    :align: center
    :alt: edit_variables

And have our map!! ( You need to refresh or pan the map for it to redraw after
changing the project variables)

.. image:: images/bandwidth_maps.png
    :width: 1142
    :align: center
    :alt: bandwidth_maps








Stacked Bandwidth
-------------------
pass


Scenario Comparison
~~~~~~~~~~~~~~~~
pass
