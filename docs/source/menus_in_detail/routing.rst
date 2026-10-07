.. _routing_menu:

Routing
=======

Open **AequilibraE > Routing > Traveling salesman problem** from the menubar or dock panel.
This dialog finds a tour through selected network nodes or centroids.

Select the stops, network mode, cost field, and starting node.
For Sioux Falls, you can use the centroids, car mode, and distance, starting at node 1.
Select the option to display the result in a new layer.

.. image:: ../images/processing_provider/tsp-prompt-box.png
    :align: center
    :alt: Interactive traveling salesman configuration

The procedure report summarizes the result.
Use its export button to save the report as a text file.
The TSP stops layer also contains the stop sequence.

.. image:: ../images/processing_provider/tsp-procedure-report.png
    :align: center
    :alt: Traveling salesman procedure report

The output map labels stops in tour order.

.. image:: ../images/processing_provider/tsp-solution.png
    :align: center
    :alt: Traveling salesman tour and stop sequence

Computation time increases with the number of stops.
Start with a small set when exploring this tool.
