---
title: 'QAequilibraE: a graphical user interface for transportation modeling on QGIS'
tags:
  - QGIS
  - Python
  - transportation modeling
authors:
  - name: Pedro Camargo
    orcid: 0000-0000-0000-0000
    affiliation: 1
  - name: Jamie Cook
    orcid: 0000-0000-0000-0000
    affiliation: 1
  - name: Renata Imai
    orcid: 0000-0000-0000-0000
    affiliation: 1
  - name: Jake Moss
    orcid: 0000-0000-0000-0000
    affiliation: 1
affiliations:
  - name: Outer Loop Consulting, Australia
    index: 1
date: 30 june 2025
# bibliography: paper.bib
---

# Summary

`QAequilibraE` offers a graphical interface for general-purpose transportation modeling built on top
of AequilibraE, a fully-featured Python package. The plugin provides an easy to use GUI for those
taking the first steps on transportation modeling or more experienced users who want to save time
generating data visualization or getting useful insights.

The seed of the current plugin was created in 2014, to overcome an issue that its creator
had as a PhD student as most commercial softwares don't allow low-level access to its outputs.
`QAequilibraE` was born in 2017 to differentiate between the Python package and the QGIS plugin,
whose development was occurring simultaneously within the same tool. Nowadays, `QAequilibraE` not only
follows the QGIS plugin structure but some good practices for Python software development, with
automated workflows for code testing in different platforms and documentation build. 

`QAequilibraE` allows the user to build models from scratch, using existing QGIS layers or
importing data from OpenStreetMaps (OSM). The tools to prepare the network from existing layers,
add traffic zones and centroids are also available. However, the plugin's main computational
features are:

- Trip distribution, with calibration and application of gravity models, and iterative
  proportional fitting (IPF).
- Traffic assignment with all-or-nothing (AoN), method of successive averages (MSA), 
  Frank-Wolfe method (FW) and its modifications conjugate Frank-Wolfe (CFW) and
  bi-conjugate Frank-Wolfe (BFW) methods. 
- Route choice set generation with breadth first search on link elimination (BFS-LE),
  link penalization (LP), or a combination of BFS-LE with link penalization.
- Transit skimming and assignment 

Despite the traffic modelling tools, some features are only available as part of the
QGIS ecosystem, of which:

- Visualization of skims or traffic analysis zones (TAZ) data;
- Run a travelling salesman problem (TSP);
- Graphical scenario comparison;
- Iterative exploration of general transit feed specifications (GTFS);
- Internationalization to other languages rather than English only.

`QAequilibraE`'s development has been at full speed in the past year, with several bug fixes,
continuous integrations, and tooling creation. The latest stable version of the QGIS plugin
can be downloaded and installed through the QGIS plugins menu, and its full documentation is
available at `https://www.aequilibrae.com/develop/qgis/index.html`.

# Usage Examples

![Traffic assignment](traffic_assignment_plot.png)  
*Figure 1: traffic assignment*

![Skim viewer](skim_viewer_plot.png)  
*Figure 2: skim viewer*


# Acknowledgements

We acknowledge contributions from Outer Loop Consulting, ADEME, La Fabrique des Mobilités,
EGIS France, and the Brazilian Institute of Applied Economics Research (IPEA) for 
partially-funding the development of the plugin.

# References
