.. _options_menu:

Options
=======

The **Options** menu holds the QAequilibraE settings that are not tied to a single
procedure. They apply to whichever project is open, and each choice is remembered
across QGIS sessions rather than being stored with the model.

.. _break_links_option:

Break links at nodes while digitizing
-------------------------------------

Ticked, a link drawn across nodes it snapped to along the way is saved as one link per
stretch between them, so the network stays connected at each of those nodes. Unticked,
the link is saved exactly as drawn, as a single feature running over the top of them.

The full behavior, including what it does with attributes and link ids, is described in
:ref:`editing networks <editing_networks>`.
