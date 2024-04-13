<p align="center">
<picture>
<img src="https://raw.githubusercontent.com/BojanSof/PyDevDTK/main/images/icon.png" height="256">
</picture>
</p>

Python package that provides basic tools for device development, including:
- Communication protocols:
	- UART
	- BLE
- Real-time visualizations:
	- Line plots
	- Scatter plots
	- Bar plots
	- Image plots
	- *Fully customized figure

More communication protocols and plots are added iteratively.

## Installing

The repository includes github actions which publish the package to PyPI and TestPyPI.
To install the latest release package, run:
```
pip install pydevdtk
```


To install the latest development package, which is published on TestPyPI, run:
```
pip install --index-url https://test.pypi.org/simple pydevdtk
```

If you need to install the package locally for development, run the following command in the root of the repository:
```
pip install -e .
```

## Examples

Examples can be found under `examples` folder.

## Requirements

Requirements can be found under `requirements` directory, which includes:

- `default.txt` - base requirements for the package
- `build.txt` - requirements for building the package
- `doc.txt` - requirements for building the documentation (WIP)
- `dev.txt` - requirements for developing the package, including linters and formaters
