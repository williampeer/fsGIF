# Installation

We recommend that the following commands be run in their own virtual environment, to avoid disturbing other packages.
    python3 -m venv fsgif     
    source fsgif/bin/activate

First upgrade `pip` and `setuptools` (depending on your system, some packages may fail to install if you skip this step)
    pip install --upgrade pip
    pip install --upgrade setuptools

Then install the package by navigating to this directory and running
    pip install .
(Add the `-e` option to install in develop mode, which allows modifying the code without requiring a reinstall every time.)

# Running


## Running in other scripts

Code is installed under the name `fsGIF` and can be imported into Python scripts as
    import fsGIF
