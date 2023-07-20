def run_about(qgisproject):
    from qaequilibrae.modules.common_tools.about_dialog import AboutDialog

    dlg2 = AboutDialog(qgisproject)
    dlg2.show()
    dlg2.exec_()
