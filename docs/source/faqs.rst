Frequently Asked Questions (FAQs)
=================================

Installation
------------
.. admonition:: The installation fails when using a firewall

    When operating behind a firewall, the pip dependency installation may fail and result in an
    import error when next starting QGIS. One way to ensure the installation, is using the
    ``DownloadAll`` class in a script, run in the Python terminal.

    .. code::

        # This script is to be executed in the QGIS Python console. Open it via the menu bar ->
        # Plugins -> Python console, or use Ctrl + Alt + P. Then use the "Show Editor" button,
        # paste this script, edit, and press execute. Pasting into the console directly will
        # result in an exception.
        import os
        from qaequilibrae.download_extra_packages_class import DownloadAll

        # Set the environment variables required for pip here
        # os.environ["variable name"] = "variable value"

        # Create an instance of the our downloader class, this handles all the dependencies that
        # qaequilibrae needs and removes packages that conflict with the global QGIS packages.
        installer = DownloadAll()

        # The downloader uses two files to mark when dependencies have need installed, we'll
        # remove those to get it to retry the downloads.
        installer.retry_pkg_install()


User issues
-----------
.. admonition:: I've found a problem, how can I report it?

    After reviewing the documentation and the discussions on our 
    `Google Group <https://groups.google.com/g/aequilibrae>`_, and ensuring that 
    there is an actual bug or documentation issue, you can report it in the following ways:

    * Filing a bug report in the `issue tracker <https://github.com/AequilibraE/qaequilibrae/issues>`_;
    * Creating a post in our `Google Group <https://groups.google.com/g/aequilibrae>`_.
