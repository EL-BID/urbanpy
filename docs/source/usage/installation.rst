Installation
============

For users
~~~~~~~~~

To install the urbanpy library you can use:

.. code:: sh

    $ pip install urbanpy

Then use ``import urbanpy`` in your python scripts to use the library.

If you plan to use the `OSRM Server <http://project-osrm.org/>`__ route
or distance matrix calculation functionalities\* you must have Docker
installed in your system, refer to Docker
`Installation <https://www.docker.com/products/docker-desktop>`__.

For developers
~~~~~~~~~~~~~~

If you plan to contribute or customize urbanpy first clone this repo and
cd into it. Then, we strongly recommend you to create a virtual
environment. You can use conda, this installation manage some
complicated C spatial library dependencies:

.. code:: sh

    $ conda env create -f environment.yml
    $ conda activate urbanpy

Or if you are more confident about your setup, you can use pip:

.. code:: sh

    $ python3 -m venv .env
    $ source .env/bin/activate
    (.env) $ pip install -r requirements.txt


\*Current support is tested on Linux Ubuntu 18.04 & Mac OS Catalina,

coming soon we will test and support Windows 10.
