Data
====

In the data tab the user can check and load the non-geographic data available in the project.

.. image:: ../images/menu_data.png
    :align: center
    :alt: tab data menu

.. _data_visualize_data:

Visualize data
--------------

When clicking **Data > Visualize data**, a new window with three different tabs
opens. The tab *matrices* shows the matrices available for the current project (see figure below).

.. image:: ../images/data_visualize_data_matrices.png
    :align: center
    :alt: project data matrices

As for the tab *results* it displays the results of procedures that took place, such as the
creation of Delaunay Lines, and that are saved in a **results_database.sqlite**.

.. image:: ../images/data_visualize_data_results.png
    :align: center
    :alt: project data results

Finally, the tab *non-project data* allows you to open and visualize matrices and datasets in the following 
extensions: \*.omx, \*.aem, and \*.aed.

.. _fig_nonproject_data:

.. image:: ../images/data_visualize_data_nonproject_data.png
    :align: center
    :alt: project data load non-project data

Suppose you want to check a \*.aem matrix you have previously saved in your computer.
When clicking the **Load data** button, you can point AequilibraE the location of the file and a new
window opens.

Check the figure below to see how the visualization window looks like.
You can configure the number of decimal places to be displayed and if
one wishes to use the thousand separator or not. In case your file has more than one view,
you can select the desired view using the dropdown buttons at the bottom of the page.
In our figure, they are represented by the dropdowns containing *matrix* and 
*main_index*. Finally, if you click in the *export* button in the lower left corner of the 
window, you can also save the current matrix in \*.csv format. 

.. image:: ../images/data-visualize-loaded-matrix.png
    :align: center
    :alt: data visualize matrices

.. _importing_matrices:

Importing matrices to project
-----------------------------

It is also possible for the user to import matrices from an open layer to a project. This can be done by clicking 
**Data > Import Matrices** and properly indicating the fields in the new window. First click *Load*
and then *Save*. A new window will open and you can point to the project matrices folder. To take a look in the
matrix you just imported, you can upload the matrix table and display it as shown in the last topic.

.. image:: ../images/data-matrix_importer.png
    :align: center
    :alt: project data results
