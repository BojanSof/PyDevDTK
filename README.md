# Python Device Development Kit (PyDevDTK)

Python package that provides basic tools for device development, including:
- Communication protocols:
	- UART
	- BLE
	- TCP/IP
- Real-time visualizations:
	- Line plots
	- Scatter plots
	- Bar plots
	- Image plots

## Building the wheel package

To build the wheel package, run `python -m build` from the root of the package project.
Ensure that `build` package is installed.
The wheel package can be found under `dist` folder.

## Installing wheel package

Wheel package can be installed by calling `pip install <package.whl>`.