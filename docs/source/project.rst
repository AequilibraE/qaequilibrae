AequilibraE Project
===================

.. toctree::
   :maxdepth: 2

The AequilibraE project is the newest portion of the `aequilibrae API <www.aequilibrae.com/python>`_ , and
therefore the least mature. However, its first feature is the capability of importing networks directly
from `Open Street Maps <www.openstreetmap.org>`_ into AequilibraE's efficient TranspoNet format.

The API will soon bring much more sophisticated features, but this capability inside QGIS is probably the
most relevant for most users for now.

This is also time to give a HUGE shout out to `Geoff Boeing <http://www.geoffboeing.com/>`_, creator of
the widely used Python package `OSMNx <https://github.com/gboeing/osmnx>`_ . For months I worked with
Geoff in reformatting OSMNx in order to be able to include it as a submodule or dependency for AequilibraE,
but its deep integration with `GeoPandas <www.geopandas.org>`_ and all the packages it depends on (Pandas,
Shapely, Fiona, RTree, etc.), means that we would have to rebuild OSMNx from the ground up in order to use
it with AequilibraE within QGISm since its Windows distribution does not include all those dependencies.

For this reason, I have ported some of Geoff's code into AequilibraE (modifications were quite heavy,
however), and was ultimately able to bring this feature to life.

Network Import from OSM
~~~~~~~~~~~~~~~~~~~~~~~

pass
