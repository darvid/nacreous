nacreous
~~~~~~~~

**nacreous** is an overkill Python 3.5 utility that downloads tracks
from Soundcloud, tags them, and embeds cover art.

.. image:: https://upload.wikimedia.org/wikipedia/commons/c/cc/Nacreous_clouds_Antarctica.jpg
   :target: https://en.wikipedia.org/wiki/Polar_stratospheric_cloud
   :width: 50%
   :align: center

**nacreous** uses Selenium_ to fetch track URLs, and youtube-dl_ to
download them. You might be befuddled about the choice of dependencies,
but they are the product of frustration with other sync scripts using
the Soundcloud API and incompletely syncing, failing to download certain
tracks, or not tagging effectively or embedding cover art.

Requirements
------------

At this time there is no one-click install or py2exe binaries for every
platform. As such, brave users are required to install the following
dependencies:

* Python_ 3.5 (3.4 and below are not supported)
* Firefox_, because it's the simplest Selenium WebDriver backend to
  install across all platforms.


Installation
------------

.. code:: shell

    $ pip install -r requirements.txt
    $ python setup.py install
    $ nacreous --help


Basic Usage
-----------

Currently, the only support sub-command is ``sync``. The following
command will download all of the given user's likes::

    nacreous sync --likes impendingdave


Alternatives
------------

There are quite a few Soundcloud sync tools/scripts out there if
**nacreous** doesn't fit the bill for you.

* `scdl <https://github.com/joengelm/scdl>`_
* `soundcloud-syncer <https://github.com/Sliim/soundcloud-syncer>`_
* `SoundCloud-Playlist-Sync <https://github.com/StephenCasella/SoundCloud-Playlist-Sync>`_
* `soundcloud-util <https://github.com/DWiechert/soundcloud-util>`_


.. _Selenium: http://www.seleniumhq.org/
.. _youtube-dl: https://rg3.github.io/youtube-dl/
.. _Firefox: https://www.mozilla.org/en-US/firefox/new/
.. _Python: https://www.python.org/downloads/
