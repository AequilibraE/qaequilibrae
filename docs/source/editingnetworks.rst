Editing networks
================

.. toctree::
   :maxdepth: 1

.. _tutorial:


Adding centroids
----------------


Starting in version 0.6 of AequilibraE, centroid connectors can now only be
added to
`AequilibraE projects <http://www.aequilibrae.com/python/V.0.6.0/project.html>`_
, and no longer generates new layers during the process.

Before we describe what this tool can do for you, however, let's just remember
that there is a virtually unlimited number of things that can go awfully wrong
when we edit networks with automated procedures, and we highly recommend that
you **BACKUP YOUR DATA** prior to running this procedure and that you inspect
the results of this tool **CAREFULLY**.

The **GUI** for this procedure is fairly straightforward, as shown below.

.. image:: images/add_connectors_to_project.png
    :width: 827
    :align: center
    :alt: Adding connectors

One would notice that nowhere in the **GUI** one can indicate which modes they
want to see the network connected for or how to control how many connectors per
mode will be created.  Although it could be implemented, such a solution would
be convoluted and there is probably no good reason to do so.

Instead, we have chosen to develop the procedure with the following criteria:

* All modes will be connected to links where those modes are allowed.
* When considering number of connectors per centroid, there is no guarantee that
  each and every mode will have that number of connectors. If a particular mode
  only available rather far from the centroid, it is likely that a single
  connector to that mode will be created for that centroid
* When considering the maximum length of connectors, the **GUI** returns to the
  user the list of centroids/modes that could not be connected.

Notice that in order to add centroids and their connectors to the network,
we need to create the set of centroids we want to add to the network in a
separate layer and to have a field that contains unique centroid IDs. These IDs
also cannot exist in the set of node IDs that are already part of the map.

Network editing tricks
======================

We have chosen `Alice Springs <https://en.wikipedia.org/wiki/Alice_Springs>`_ as subject for this example, as that is a
small and isolated city for which quite a bit of data is available and that lacks a transportation model, so actual
practical use might be made of this in the future.

As this tutorial is developed, software other than AequilibraE and QGIS will be used, most notably for the demand
modelling portion of the model.

The files used in this example are available in a separate
`GitHub repository <https://github.com/AequilibraE/AliceSprings>`_

* Reading about the `basic concepts <networkmanipulation.html>`__ behind AequilibraE's networks is probably a good idea


Centroids from area layers
--------------------------

. It turns our that the SA1 layer
provided by the ABS has two multipart SA1s, so we had use the same
Multipart-to-singleparts used to sanitize the network layer.

After this step, creating a centroids layer was a matter of following a few steps.

1. Add a data field with the zone number to the zoning system

2. Extract centroids from the zoning system.  Menu accessible on **Vector > Geometry Tools > Centroids**

.. image:: images/network_edit_centroids_menu.png
    :width: 800
    :align: center
    :alt: Zones to centroids

3. Visually inspect centroids looking for those that were placed in awkward places and move them to more appropriate
   positions

Sourcing the data
~~~~~~~~~~~~~~~~~

* Road Network

For this example we will use Open-Street Maps data, which is the most widely available data out there.
There is an `online tool <http://osm-traffic.com/>`_ that is pretty good to download very target data (such as that for
Alice Springs), you can also download the entire thing from `Geofabrik <http://download.geofabrik.de/>`_

Since AequilibraE for QGIS allows for direct download of OSM data since its 0.5.3 version, you can use the facility
described on `Build a project from OSM <project.html>`__ and then go straight to adding centroids and connectors to
the network, as described further down this tutorial.

* Zoning System:

In this example the zoning system is derived from SA1s, which is the smallest unit in the spatial aggregation made
available by the Australian Bureau of Statistics (ABS). One could decide to go down to meshblocks, but the added
complexity that arise from the lack of full demographic data from the ABS is not justifiable for the development of
this example.


Building the network
~~~~~~~~~~~~~~~~~

When using Spatial OSM data

Dealing with intersection when working with OSM networks is not trivial, as different people code their networks
differently. The main issue here is that there are two possible cases where links intersect on the map:

1. There is an actual intersection there that would need to be represented as a node in the network and the original
   links would need to be split in that point

2. There is NO intersection there, and links are actually on different levels (e.g. tunnel, surface, elevated)

QGIS provides several tools for editing the network, but dealing with the consequences of poorly coded network in QGIS
is just as painful as doing it in any other package.

For this reason we recommend download from geofabrik, as there are clearly labeled fields for tunnels and bridges.


Pre-processing
++++++++++++++

Let's first split all links in the network at all points they cross.

.. image:: images/network_edit_processing_menu.png
    :width: 800
    :align: center
    :alt: Menu access

Here you can if the links to be split are the same set used to split them or not, but that is up to your judgement.

In the case of Alice Springs, all road crossings are at grade, so we split links in all cases where they cross, even
though **many links were tagged as being bridges**, so we used all links for both inputs.

.. image:: images/network_edit_splitting.png
    :width: 800
    :align: center
    :alt: Splits links


If you want to experiment with spliting only links that are not tagged as bridges or tunnels, you can load the same
layer twice and filter one of them no everything except tunnels and bridges.

.. image:: images/network_edit_filter.png
    :width: 800
    :align: center
    :alt: Filtering layer


After spliting the links, we ended up with a link layer with MultiLineString features (where lines are not necessarily
continuous).  As this does not make sense in a transportation network, we used another QGIS feature to obtain only
single part links (non-continuous links are separated in multiple continuous links).

That cool can be accessed in this menu:  **Vector > Geometry Tools > Multipart to Singleparts**, and running it looks
like this:

.. image:: images/network_edit_multipart_to_singlepart.png
    :width: 800
    :align: center
    :alt: Multipart to Singleparts

Other resources
+++++++++++++++

There is an excellent tutorial from Roberta Maletta using AequilibraE 0.4 that is still very much current

.. raw:: html

    <iframe width="560" height="315" src="https://www.youtube.com/embed/mHeCfNuuTkQ" frameborder="0"
    allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

