Editing networks
================

.. toctree::
   :maxdepth: 1

.. _tutorial:


Adding centroids
----------------


New in version 0.6 of AequilibraE, centroid connectors can now only be added to
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

Instead, we have chosen to develop the procedure with the following criteira:

* All modes will be connected to links where those modes are allowed.
* When considering number of connectors per centroid, there is no guarantee that
  each and every mode will have that number of connectors. If a particular mode
  only available rather far from the centroid, it is likely that a single
  connector to that mode will be created for that centroid
* When considering the maximum length of connectors, the **GUI** returns to the
  user the list of centroids/modes that could not be connected.

Before adding connectors to the network, however, we need to create the set of centroids we want to add to the network.
It turns our that the SA1 layer provided by the ABS has two multipart SA1s, so we had use the same
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

4. Manually adding centroids for external stations (external flows) and special generators (i.e. correctional facility
   and military base)


With the centroids layer created, it was time to create the final link and node layers by adding the centroids to the
node layer and creating centroid connectors from the centroids to their closest nodes.

AequilibraE has a tool specifically for that, which takes three layers (links, nodes and centroids) and allows the user
to specify maximum length of the connectors and a number of connectors per zone.  In our case we will leave the
maximum distance unrestricted and add a single connector per zone.

.. image:: images/network_edit_adding_connectors.png
    :width: 800
    :align: center
    :alt: Adding connectors

