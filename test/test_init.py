"""
This test was originally written by Tim Sutton using unittest. 
We updated its framework to use pytest instead.

__author__ = "Tim Sutton <tim@linfiniti.com>"
__revision__ = "$Format:%H$"
__date__ = "17/10/2010"
__license__ = "GPL"
__copyright__ = "Copyright 2012, Australia Indonesia Facility for "
__copyright__ += "Disaster Reduction"
"""

import configparser
import os

import pytest
from aequilibrae.context import get_logger

LOGGER = get_logger()


@pytest.mark.parametrize("expectation", ["name", "description", "qgisMinimumVersion", "email", "author"])
def test_read_init(expectation):
    """Test that the plugin __init__ will validate on plugins.qgis.org.

    # You should update this list according to the latest in
    https://github.com/qgis/qgis-django/blob/master/qgis-app/plugins/validator.py"""

    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "qaequilibrae/metadata.txt"))
    LOGGER.info(file_path)

    # Read the metadata file
    metadata = []
    parser = configparser.ConfigParser()
    parser.optionxform = str
    parser.read(file_path)

    message = f'Cannot find a section named "general" in {file_path}'
    assert parser.has_section("general"), message
    metadata.extend(parser.items("general"))

    # Check if each required metadata field is present
    message = f'Cannot find metadata "{expectation}" in metadata source ({file_path}).'
    metadata_dict = dict(metadata)
    assert expectation in metadata_dict, message
