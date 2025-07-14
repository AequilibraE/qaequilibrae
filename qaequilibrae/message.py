from qgis.PyQt.QtCore import QCoreApplication


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
        return f"{a}\r\n{b}"

    @property
    def third_message(self):
        return self.tr("You will probably need to restart QGIS to make it work")

    @property
    def fourth_message(self):
        return self.tr("Without installing the packages, the plugin will be mostly non-functional")

    @property
    def messsage_five(self):
        a = self.tr("QAequilibraE requires Python 3.12.")
        b = self.tr("Please install QGIS version 3.34.10+ or 3.38.2+ to make it work.")
        return f"{a}\r\n{b}"

    @property
    def rp_box_name(self):
        """Box name for run procedures"""
        return self.tr("Missing requirements")

    @property
    def rp_message(self):
        """Message for run procedures"""
        a = self.tr("There are missing requirements to run the procedures.")
        b = self.tr("Do you want us to install these missing Python packages?")
        c = self.tr("Without installing the packages, you cannot use 'Run Procedures'.")
        return f"{a}\r\n{b}\r\n{c}"

    @property
    def rp_error(self):
        """Message for run procedures"""
        return self.tr("Missing 'requirements.txt' file. Please check the project run folder.")

    def tr(self, text):
        return QCoreApplication.translate("messages", text)
