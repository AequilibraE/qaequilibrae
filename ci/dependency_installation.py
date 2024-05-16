from qaequilibrae.download_extra_packages_class import DownloadAll


on_latest =  sys.version_info >= (3, 12)
DownloadAll().install(on_latest)
