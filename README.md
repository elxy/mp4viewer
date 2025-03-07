# MP4Viewer

MP4Viewer is an ISO base media file format viewer. It parses the isobmf file and displays the metadata on the console or in a separate window. The definitions of structures used in the code can be found in the publicly available standard [ISO/IEC 14496-12 - ISO base media file format](http://standards.iso.org/ittf/PubliclyAvailableStandards/index.html)

Usage: cd into `src` folder and run

    $ ./showboxes.py [-h] [--debug] [-o {stdout,gui}] [-c {on,off}] iso-base-media-file

    Positional arguments:
      iso-base-media-file   Path to iso media file

    Optional arguments:
      --debug               Enable debug information (also in strict parsing)
      -o {stdout,gui}       Select output format (console or windows)
                            TODO: Add XML output
      -c {on,off}           Turn on/off colors in stdout; on by default.
      -h, --help            Help!

Screenshots:
![shell output](http://3.bp.blogspot.com/-APb-4LsE9LM/UkUoome4U4I/AAAAAAAADFk/ZkTpd7JkF24/s1600/mp4viewer_shell.png)
![window with gtk treeview](http://2.bp.blogspot.com/-4Uu3eMfMPCQ/UkUpUrfTlKI/AAAAAAAADFs/pxQSh5U81lQ/s1600/mp4viewer_gtk.png)

MP4Viewer uses gtk in graphics mode and requires that [PyGObject](https://pygobject.readthedocs.io/en/latest/getting_started.html) be installed in the system for viewing results in a window.

You can find more similar [MP4 tools in this page](https://github.com/video-dev/community-knowledge-base/blob/master/list-of-iso-bmff-mp4-tools.md)
