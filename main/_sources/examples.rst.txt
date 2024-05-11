All examples can be found under ``examples`` directory in the repo.

Serial
======

Serial example demonstrates the usage of serial (UART) communication to
receive data from device, parse it and print the data in the terminal.
The data coming from the device shold be in the following format:

.. code-block:: shell

    <data1>,<data2>\n

Example code:

.. literalinclude:: ../examples/serial_example.py
    :language: python
    :linenos:

BLE
===

BLE example demonstrates the usage of BLE communication to
receive data from device, parse the data and print it in the terminal.

The data coming from the device shold be in the following format:

.. code-block:: shell

    <data1>,<data2>\n

Example code:

.. literalinclude:: ../examples/ble_example.py
    :language: python
    :linenos:


Plotter
=======

The plotter example demonstrates how to perform real-time plotting
using `plotting` module.
It simulates data and utilizes this data to create few real-time plots,
including line plots, scatter plots, bar plots and one spectrogram plot
using image plot.

Preview:

.. image:: ../images/plotter_demo.gif
    :alt: Plotter demo preview
    :align: center

Example code:

.. literalinclude:: ../examples/plotter_demo.py
    :language: python
    :linenos:

Custom plotter
==============

The custom plotter example demonstrates how to subclass ``PlotterBase``
to have flexible figure and artists creation, using matplotlib APIs.
It simulates data and utilizes this data to for few real-time plots.

Example code:

.. literalinclude:: ../examples/plotter_base_demo.py
    :language: python
    :linenos:
