Quickstart
==========

UrbanPy lets you download and visualize city boundaries extremely easy:

.. code:: python

    import urbanpy as up

    boundaries = up.download.nominatim_osm('Lima, Peru', expected_position=2)
    boundaries.plot()

Since ``boundaries`` is a GeoDataFrame it can be easily plotted with the
method ``.plot()``. You can also generate hexagons to fill the city
boundaries in a oneliner.

.. code:: python

    hexs = up.geom.gen_hexagons(resolution=9, city=boundaries)

Also check our `example notebooks </notebooks>`__, and if you have
examples or visualizations of your own, we encourage you to share
contribute.
