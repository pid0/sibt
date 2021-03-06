sibt -- Simple Backup Tool
============================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:
   :hidden:

   manpage


sibt provides a common interface for backup tools like rsync, rdiff-backup, tar, or duplicity while performing many sanity checks and replicating infrastructure and locking to prevent data loss from misconfiguration. It is written using a test-first approach and benefits from an extensive test suite.

Stability
-------------
This being the most important feature for backup software, note that most of the stability comes from rsync, rdiff-backup, etc., which are considered very stable, because sibt never touches data itself but only integrates existing solutions and adding checks on top.

It is production-ready, I use it every day, backup and restore work as they should. Cloning Linux installations from backup is possible without a sweat with
 
 ::

   sibt restore / <version>

Documentation
-------------
For details on usage, see the :doc:`sibt man page <manpage>`.

Installation
-----------------

Archlinux AUR
^^^^^^^^^^^^^^
There is a PKGBUILD available here: https://aur.archlinux.org/packages/sibt-git/.

From Git
^^^^^^^^^
Alternatively, it is easy to just clone the git repo and run install. The master branch is considered 'stable' at all times.

::

  git clone https://github.com/pid0/sibt
  cd sibt
  paver install

License
-----------
GPLv3+. See LICENSE file.

Author
------------
Patrick Plagwitz <patrick_plagwitz@web.de>.

..
  .. py:class:: Synchronizer

    .. py:attribute:: Foo



..
  Indices and tables
  ==================

  * :ref:`genindex`
  * :ref:`modindex`
  * :ref:`search`
