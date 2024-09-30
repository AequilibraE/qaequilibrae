import pytest

from qaequilibrae.modules.gis.simple_tag_dialog import SimpleTagDialog
from qaequilibrae.modules.gis.simple_tag_procedure import SimpleTAG


@pytest.mark.skip
def test_simple_tag(pt_project):
    dialog = SimpleTagDialog(pt_project)

    print(dialog.__dict__)
