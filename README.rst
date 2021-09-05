############
navtools
############

Python-based tools for simple navigation calculations.

See http://slott56.github.io/navtools/.

Installation
============

The NavTools distribution includes the following.

-   ``navtools``. The Python code which gets installed.

-   ``igrf11coeffs.txt``. Data used to compute magnetic deviation.
    This is from http://www.ngdc.noaa.gov/IAGA/vmod/igrf11coeffs.txt

-   ``docs``.  The RST-formatted documentation files.

Clone the Git repository (or download the .zip archive).

..  code-block:: bash

    git clone https://github.com/slott56/navtools

Run the ``setup.py`` to install the package.

..  code-block:: bash

    python setup.py install

For details, see http://slott56.github.io/navtools/installation.html.
This is not available in PyPI, so a simple ``python -m pip install navtools`` isn't supported.

Use
====

There are several applications that process ``.gpx`` or ``.csv``
files:

-   Route Planning.
    Computes a schedule for arrival at the various waypoints.
    This, in turn, can be used to build a float plan to share with others.

-   Track Analysis.
    Annotates a historical log with distance and speed.

-   OpenCPN Conversion.
    Transforms an OpenCPN route planning table into
    more useful content for spreadsheet use and float plan creation.

-   Waypoint Merge.
    Determines the differences among waypoints from multiple sources.

These provide a number of navigation planning and analysis capabilities.
These are not intended for use while sailing, however, that is better
done by tools like OpenCPN, iNavX, and chartplotters.

Jupyter Lab
===========

While there is a lot of file processing, the essence of route planning
is thinking and tinkering the speeds, destinations, departure times, and
the like. While a spreadsheet is useful, Jupyter Lab is -- perhaps -- much better.

The idea is to create Notebook with the plan details.
In some cases, you may even want to create the seed
for a data collection log book that can be updated with details of the actual voyage.

You'll need to start JupyterLab with the navtools directory on the Python path.

-   Install navtools.

-   ``PYTHONPATH=/path/to/navtools jupyter lab`` to start the lab with the extra path setting.
    Often this becomes ``PYTHONPATH=$(pwd) jupyter lab`` if you change to the navtools checkout.

It's best to create a unique notebook for each specific voyage. When this involves multiple legs,
then there may be multiple float plans generated from a single notebook source document.

There are two publication options for the plan details.

1.  A cell of the notebook creates a Markdown file with boilerplate and itinerary for a specific plan.
    This is processed through pandoc. This is a pleasant approach because other formats
    (like plain text) can be made from the Markdown source.

    ::

        pandoc --from markdown+pipe_tables "plan.md" -o "plan.pdf"

2.  A separate notebook is built from boilerplate and itinerary.
    This is processed through NBConvert.

    ::

        jupyter nbconvert "plan.ipynb" --to pdf --no-input

The results are similar, and are small PDF's that can be shared widely.

Documentation
=============

::

    cd docs
    make html

Development
============

The development environment relies on PlantUML to create the diagrams.
See https://plantuml.com.

The Sphinx-PlantUML plugin is used to transform ``..  uml::`` markup into a diagram.

-   Use **conda** to install ``graphviz``, as well as installing the ``plantuml-markdown`` tools.
    and the Sphinx-PlantUML extension.
    The ``markdown_py`` application can create an HTML draft of a Markdown doc.
    It needs to be installed separately, if this is needed.

    ::

        conda install graphviz
        python -m pip install plantuml-markdown sphinxcontrib-plantuml

-   Older PlantUML versions require a ``GRAPHVIZ_DOT`` environment variable
    to name the conda virtual environment where ``graphviz`` was installed.
    The macOS and Linux users can update ``~/.zshrc`` or ``~/.bashrc`` file, depending on which shell is in use.
    Windows users should set their system environment variables.

-   It may be necessary to create a ``plantuml`` shell script in ``/usr/local/bin``.
    See https://github.com/mikitex70/plantuml-markdown for details on installation.
    This may be done automatically by the plantuml-markdown installation. If not,
    it needs to be added.

A tool like https://pypi.org/project/py2puml/ can be used to create PlantUML text
from the source code.

Additionally, plantuml can also be incorporated into a markdown processing plug-in used by the PyCharm IDE.
The plugin depends on **graphviz**.

- Add the Markdown tool to PyCharm.

- In the preferences for Markdown, install and enable PlantUML.

While this can be useful for documents created with Markdown, this project's documentation is in RST.
