from qgis.PyQt.QtCore import QCoreApplication

# Landing page for the QGIS plugin, which carries the manual installation instructions
FAQ_URL = "https://www.aequilibrae.com/latest/qgis/index.html"


class messages:
    @property
    def first_box_name(self):
        return self.tr("AequilibraE and other dependencies are not installed")

    @property
    def first_message(self):
        a = self.tr("Do you want us to install these missing python packages?")
        b = self.tr("QGIS will be non-responsive for a couple of minutes.")
        return f"{a}\r\n{b}"

    @property
    def second_message(self):
        a = self.tr("Errors may have happened during installation.")
        b = self.tr("Please inspect the messages on your General Log message tab")
        c = self.tr("or go to the QAequilibraE FAQs and check for manual installation.")
        return f"{a}\r\n{b}\r\n{c}"

    @property
    def third_message(self):
        return self.tr("You will probably need to restart QGIS to make it work")

    @property
    def fourth_message(self):
        return self.tr("Without installing the packages, the plugin will be mostly non-functional")

    @property
    def missing_dependencies_box_name(self):
        return self.tr("AequilibraE is not installed")

    @property
    def missing_dependencies_message(self):
        """Shown when a menu entry is used while the plugin is loaded without its dependencies."""
        a = self.tr("This tool needs the Python packages QAequilibraE depends on, which are not installed.")
        b = self.tr("Restart QGIS and accept the offer to install them,")
        c = self.tr("or follow the manual installation instructions at:")
        return f"{a}\r\n\r\n{b}\r\n{c}\r\n{FAQ_URL}"

    @property
    def missing_dependencies_summary(self):
        """One-line version of the message above, for the message bar and the log."""
        a = self.tr("QAequilibraE is loaded without the Python packages it depends on.")
        b = self.tr("See {} for how to install them.").format(FAQ_URL)
        return f"{a} {b}"

    @property
    def messsage_five(self):
        a = self.tr("QAequilibraE requires Python 3.12.")
        b = self.tr("Please install QGIS version 3.34.10+ or 3.38.2+ to make it work.")
        return f"{a}\r\n{b}"

    def tr(self, text):
        return QCoreApplication.translate("messages", text)
