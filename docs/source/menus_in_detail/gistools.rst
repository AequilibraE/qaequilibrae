Mapping Tools
=============

QAequilibraE has some tools to allow the user to visualize the data.

.. image:: ../images/menu_gis.png
    :align: center
    :alt: tab gis menu

.. _data_visualize_data:

Visualize data
--------------

When clicking **Mapping > Visualize data**, a new window with three different tabs opens. The tab *matrices* shows 
the matrices available for the current project (see figure below).

.. image:: ../images/data_visualize_data_matrices.png
    :align: center
    :alt: project data matrices

As for the tab *results* it displays the results of procedures that took place, such as the creation of Delaunay 
Lines, and that are saved in a **results_database.sqlite**.

.. image:: ../images/data_visualize_data_results.png
    :align: center
    :alt: project data results

The tab *non-project data* allows you to open and visualize matrices and datasets in the following extensions: 
\*.omx and \*.aem. **This is the only tab available if no AequilibraE project is open**. Suppose you 
want to check a skim matrix from a previous project. When clicking the **Load data** button, you can point 
AequilibraE the location of the file and its visualization is displayed.

.. _fig_nonproject_data:

.. image:: ../images/data_visualize_data_nonproject_data.png
    :align: center
    :alt: project data load non-project data

Check the figure below to see how the visualization window looks like! General configurations for data displaying
such as the number of decimal places and the usage of thousand separator are available. In case your file has more 
than one view, you can select the desired view using the dropdown buttons at the bottom of the page. In our figure,
they are represented by the dropdowns containing *distance_blended* and *main_index*. To save your current matrix 
into \*.csv format, just click in the *export* button in the lower left corner of the window.

.. _fig_data_visualize_matrices:

.. image:: ../images/data-visualize-loaded-matrix.png
    :align: center
    :alt: data visualize matrices

Additionally, we can visualize how the matrices look like in the map! Using the buttons
*By origin* and *By destination*, it is possible to select the traffic zone by its origin or 
destination. If one select *By origin*, then click on the desired row, and notice that is going
to be highlighted. The *zones* layer (if it exists) is going to be loaded and the corresponding
zones are going to receive a different color shade, according to the color palette selected in
the dropdown menu. One other possibility to select the zone for displaying is directly into the
map canvas: with the *Select features* button enabled, just click on the desired zone in the
layer and you'll notice that the color shades will change accordingly, as well as the row selection
in the matrix.

.. image:: ../images/data-matrix-view-row.png
    :align: center
    :alt: data matrix view by origin

The step-by-step when selecting *By destination*, is identical to the one before. Select the
desired column (destination), notice that it will be highlighted, and the *zones* layer is
going to present a color shade according to the color palette selected. The selection of zones
for displaying is also available for destinations, and the steps are the same as presented above.

.. image:: ../images/data-matrix-view-column.png
    :align: center
    :alt: data matrix view by destination

.. _siouxfalls-desire-lines:

Desire Lines
------------

QAequilibraE is capable of doing two types of desire lines from a zone or a node layer:
'regular' desire lines or Delaunay lines for the demand matrix provided.

.. image:: ../images/desire_lines_gui.png
    :width: 800
    :align: center
    :alt: Desire Lines GUI

After selecting a matrix, the user can choose to un-check the *use all matrices*
box and select which matrix layers/cores they want to use (the list of matrices will only
show if the option is un-checked). Just make sure to select a *zone/node layer* 
and *node id* that is compatible with your matrix.

.. subfigure:: AB
    :subcaptions: below
    :align: center

    .. image:: ../images/delaunay_results.png
        :alt: Delaunay lines
    
    .. image:: ../images/desire_lines_map.png
        :alt: Desire lines

.. _siouxfalls-stacked-bandwidth:

Stacked Bandwidth
-----------------

This is a tool for plotting link flows. It uses a link layer, including Delaunay lines or desire
lines. It is also possible to choose between solid or gradient colors.

.. image:: ../images/stacked_bandwidth_gui.png
    :align: center
    :alt: Stacked bandwidth GUI

Basic workflow
~~~~~~~~~~~~~~

We'll use the traffic assignment result for Sioux Falls in this example. Don't worry if you
haven't done the assignment: you can use any other line layers and flows you want!

Before set up the bandwidth configuration, make sure you have the 'links' and 
'traffic_assignment_result' layers active in the layers list. If you open the links' layer
attribute table, you'll see that the fields of 'traffic_assignment_result' are joined.

Let's proceed with a solid band first. First, we select the line layer (1) and the AB/BA flow
variables (2 and 3). Regarding the color, you can use a random color selected by QAequilibraE 
or choose the one you want. Just click on the dropdown button at the right-hand side of the
color box. To add the band, we click on the *"Add band"* button (4). You'll notice that the
band configuration is now available at the table and the *"Create bands"* button is enabled.
Click on it (5) and the links layer in the canvas will automatically be updated.

.. image:: ../images/stacked_bandwidth_solid_color.png
    :align: center
    :alt: Add stacked bandwidth with solid color

It is also possible to 

.. image:: ../images/stacked_bandwidth_with_color_ramp_1.png
    :align: center
    :alt: Add stacked bandwidth with color ramp - set up

When the color ramp window opens, configure once again the fields and the color ramp you
want to use. We'll use the default 'Blues' in this example.

.. image:: ../images/stacked_bandwidth_color_ramp_config.png
    :align: center
    :alt: Color ramp configuration in stacked bandwidth

Finally, add the configured band to the project table (1) and click on the *"Create bands"*
button (2).

.. image:: ../images/stacked_bandwidth_with_color_ramp_2.png
    :align: center
    :alt: Add stacked bandwidth with color ramp - add band

You can also control the overall look of these bands (thickness and separation between AB and
BA flows) in the project properties. Go to the properties box in the Project menu and click on
the *Variables* tab. We'll edit the ``aeq_band_width`` variable.

.. subfigure:: AB
    :align: center
    :gap: 8px

    .. image:: ../images/project_properties.png
        :alt: Project menu
    
    .. image:: ../images/edit_variables.png
        :alt: Edit project variables

And we're all set! You might need to refresh or pan the map for it to redraw after
changing the project variables.

.. subfigure:: AB
    :subcaptions: below
    :align: center

    .. image:: ../images/bandwidth_maps.png
        :alt: Solid color
    
    .. image:: ../images/bandwidth_maps.png
        :alt: Color ramp

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
