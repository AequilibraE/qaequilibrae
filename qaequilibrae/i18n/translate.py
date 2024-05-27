from qgis.core import QgsProcessingAlgorithm


class TranslatableAlgorithm(QgsProcessingAlgorithm):
    def __init__(self, translator):
        super(QgsProcessingAlgorithm, self).__init__()
        self.tr = translator
