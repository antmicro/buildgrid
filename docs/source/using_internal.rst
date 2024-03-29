
.. _internal-client:

Internal client
===============

BuildGrid contains a minimal remote execution client that can be used through
the ``bgd`` command line interface.


.. _dummy-test:

Dummy test
----------

In one terminal, start a server:

.. code-block:: sh

   bgd server start data/config/default.conf

In another terminal, upload an action to CAS:

.. code-block:: sh

   bgd cas upload-dummy

Then send a request for work:

.. code-block:: sh

   bgd execute request-dummy

The stage should show as ``QUEUED`` as it awaits a bot to pick up the work:

.. code-block:: sh

   bgd operation list

Create a bot session:

.. code-block:: sh

   bgd bot dummy

Show the work as completed:

.. code-block:: sh

   bgd operation list


.. _simple-build:

Simple build
------------

This example covers a simple build. The user will upload a directory containing
a C file and a command to the CAS. The bot will then fetch the uploaded
directory and command which will then be run inside a temporary directory. The
result will then be uploaded to the CAS and downloaded by the user. This is an
early demo and still lacks a few features such as symlink support and checking
to see if files exist in the CAS before executing a command.

Create a new directory called `test-buildgrid/` and place the following C file
in it called `hello.c`:

.. code-block:: C

   #include <stdio.h>
   int main()
   {
     printf("Hello, World!\n");
     return 0;
   }

Now start a BuildGrid server, passing it a directory it can write a CAS to:

.. code-block:: sh

   bgd server start data/config/default.conf

Start the following bot session:

.. code-block:: sh

   bgd bot host-tools

Upload the directory containing the C file:

.. code-block:: sh

   bgd cas upload-dir /path/to/test-buildgrid

Now we send an execution request to the bot with the name of the expected
``output-file``, a boolean describing if it is executeable, the path to the
directory we uploaded in order to calculate the digest and finally the command
to run on the bot:

.. code-block:: sh

   bgd execute command --output-file hello True /path/to/test-buildgrid -- gcc -Wall hello.c -o hello

The resulting executeable should have returned to a new directory called
``testing``.
