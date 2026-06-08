from qgis.core import QgsProcessingAlgorithm
from typing import Optional, Callable


class QAequilibraEProcessingAlgorithm(QgsProcessingAlgorithm):
    def __init__(
        self,
        menu_action_func: Optional[Callable] = None,
        name: str = "",
        display_name: str = "",
        group: str = "",
        group_id: str = "",
        help_string: str = "",
        tags: list[str] = None,
    ):
        super().__init__()
        self.menu_action_func = menu_action_func
        self._name = name
        self._display_name = display_name
        self._group = group
        self._group_id = group_id
        self._help_string = help_string
        self._tags = tags if tags is not None else []

    def initAlgorithm(self, config=None):
        pass

    def processAlgorithm(self, parameters, context, feedback):
        if self.menu_action_func is not None:
            self.menu_action_func()
        return {}

    def name(self):
        return self._name

    def displayName(self):
        return self._display_name

    def group(self):
        return self._group

    def groupId(self):
        return self._group_id

    def shortHelpString(self):
        return self._help_string

    def createInstance(self):
        return type(self)(
            self.menu_action_func,
            self._name,
            self._display_name,
            self._group,
            self._group_id,
            self._help_string,
            self._tags,
        )

    def tags(self):
        return self._tags
