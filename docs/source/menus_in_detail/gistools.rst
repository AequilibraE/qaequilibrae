GIS Tools
=========

QAequilibraE has some tools to allow the user to visualize the data.

.. image:: ../images/menu_gis.png
    :align: center
    :alt: tab gis menu

.. _siouxfalls-desire-lines:

Desire Lines
------------

QAequilibraE is capable of doing two types of desire lines. 

It is possible to use a zone or a node layer, and one can also generate the desire 
lines and Delaunay lines for the demand matrix provided.

.. image:: ../images/desire_lines_gui.png
    :width: 800
    :align: center
    :alt: Desire Lines GUI

After selecting a matrix, the user can choose to un-check the *use all matrices*
box and select which matrix layers/cores they want to use (the list of matrices will only
show if the option is un-checked). Just make sure to select a *zone/node layer* 
and *node id* that is compatible with your matrix.

The user also needs to choose if they want Delaunay lines

.. image:: ../images/delaunay_results.png
    :width: 750
    :align: center
    :alt: delaunay_results

or desire lines

.. image:: ../images/desire_lines_map.png
    :width: 750
    :align: center
    :alt: desire_lines_map

.. _siouxfalls-stacked-bandwidth:

Stacked Bandwidth
-----------------

The tool for plotting link flows you just saw above can be found under the GIS
menu.

You can select a link layer, including Delaunay Lines or desire lines. It is also possible
to choose between solid or gradient colors.

.. image:: ../images/add_band.png
    :width: 760
    :align: center
    :alt: add_band

|

.. image:: ../images/create_bands.png
    :width: 737
    :align: center
    :alt: create_bands

You can also control the overall look of these bands (thickness and separation between AB and
BA flows) in the project properties.

.. image:: ../images/project_properties.png
    :width: 421
    :align: center
    :alt: project_properties

.. image:: ../images/edit_variables.png
    :width: 886
    :align: center
    :alt: edit_variables

And have our map!! (You need to refresh or pan the map for it to redraw after
changing the project variables)

.. image:: ../images/bandwidth_maps.png
    :width: 1142
    :align: center
    :alt: bandwidth_maps

.. _siouxfalls-scenario-comparison:

Scenario Comparison
-------------------

After joining the two assignment results (the original one and the one resulting
from the forecast we just did) to the links layer, one can compare scenarios.

When joining the assignment results, make sure to name them in a way you will
understand.

The scenario configuration requires the user to set AB/BA flows for the two
sets of link flows being compared, as well as the space between AB/BA flows,
and band width.

The user can also select to show a composite flow comparison, where common
flows are also shown on top of the positive and negative differences, which
gives a proper sense of how significative the differences are when compared to
the base flows.

As it was the case for stacked bandwidth formatting, expert mode sets project
variables as levers to change the map formatting.

.. image:: ../images/scenario_comparison_configuration.png
    :width: 473
    :align: center
    :alt: scenario_comparison_configuration

And this is what it looks like

.. image:: ../images/scenario_comparison_map.png
    :width: 778
    :align: center
    :alt: scenario_comparison_map

Simple tag
----------

**GIS > Simple tag** works as a spatial join tool in AequilibraE that allows you
to join useful information between layers.

Suppose you have a nodes layer with a 'name' column only with ``NULL`` values,
and a zoning layer with an analogous column 'name' but filled with actual names.
We can join the information from the zoning layer into the nodes layer using 
Simple tag.

We start selecting the layer and the field from which we want to import the
data, and then selecting the layer and the field we want to 'paste' the data.
Notice that depending on the operation one want to perform, not all methods are
available.

.. image:: ../images/simple_tag.png
    :align: center
    :alt: simple tag UI

Be aware that the existence of triggers in the project database might affect the
performance of Simple tag.