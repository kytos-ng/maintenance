|Tag| |License| |Build| |Coverage| |Quality|

.. raw:: html

  <div align="center">
    <h1><code>kytos/maintenance</code></h1>

    <strong>NApp that manages maintenance windows</strong>

    <h3><a href="https://kytos-ng.github.io/api/maintenance.html">OpenAPI Docs</a></h3>
  </div>


Overview
========

This NApp creates maintenance windows, allowing the maintenance of network
devices (a switch, a board, a link) without receiving alerts. The circuits
using those devices will be moved to another path during the maintenance, if
possible. Notifications about those devices will be disabled during the
maintenance.

Installing
==========

To install this NApp, make sure to have the same venv activated as you have ``kytos`` installed on:

.. code:: shell

   $ git clone https://github.com/kytos-ng/maintenance.git
   $ cd maintenance
   $ python3 setup.py develop


Events
======

Published
---------

kytos/maintenance.(start|end)_(switch|uni|link}
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Event reporting when a maintenance starts and ends for a switch, uni or link.

Content:

.. code-block:: python3

   {
     'switches|unis|links': List of <object>s,
   }


.. TAGs

.. |License| image:: https://img.shields.io/github/license/kytos-ng/kytos.svg
   :target: https://github.com/kytos-ng/ /blob/master/LICENSE
.. |Build| image:: https://scrutinizer-ci.com/g/kytos-ng/maintenance/badges/build.png?b=master
  :alt: Build status
  :target: https://scrutinizer-ci.com/g/kytos-ng/maintenance/?branch=master
.. |Coverage| image:: https://scrutinizer-ci.com/g/kytos-ng/maintenance/badges/coverage.png?b=master
  :alt: Code coverage
  :target: https://scrutinizer-ci.com/g/kytos-ng/maintenance/?branch=master
.. |Quality| image:: https://scrutinizer-ci.com/g/kytos-ng/maintenance/badges/quality-score.png?b=master
  :alt: Code-quality score
  :target: https://scrutinizer-ci.com/g/kytos-ng/maintenance/?branch=master
.. |Stable| image:: https://img.shields.io/badge/stability-stable-green.svg
   :target: https://github.com/kytos-ng/maintenance
.. |Tag| image:: https://img.shields.io/github/tag/kytos-ng/maintenance.svg
   :target: https://github.com/kytos-ng/maintenance/tags
