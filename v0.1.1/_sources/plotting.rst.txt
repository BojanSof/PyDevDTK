Plotting
========

This section of the documentation describes the plotting tools provided by 
the PyDevDTK. It details various types of plots that can be used for 
real-time data visualization.
It is based on ``PlotterManager`` object which holds ``Plotter`` or
``PlotterBase`` based instance and communicates with this object to provide
real-time data visualization.

Plotter Base
------------

The ``PlotterBase`` class is the base class for plotters that allow to use any
matplotlib functions for visualizing data in real-time. User is responsible for
creating all the artists using matplotlib APIs and providing function for updating
the artists.

.. automodule:: pydevdtk.plotting.plotter_base
   :members:
   :undoc-members:

Plotter
------------

The ``Plotter`` class is simple class that can be used automatically with
``PlotterManager`` APIs for creating plots.

.. automodule:: pydevdtk.plotting.plotter
   :members:
   :undoc-members:

Plotter Manager
---------------

The ``PlotterManager`` class is responsible for managing the plotting process,
including the creation, update, and termination of plots. It communicates with
a separate plotting process to enable real-time data visualization.
The user should provide ``Plotter`` instance if the APIs for creating plots
need to be used, otherwise the instance should be from subclass of ``PlotterBase``.

.. automodule:: pydevdtk.plotting.plotter_manager
   :members:
   :undoc-members:
