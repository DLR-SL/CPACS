import os

import pytest
from tixi3 import tixi3wrapper


def rel_location():
    __location__ = os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__))
    )
    return __location__


@pytest.fixture
def cpacs_examples():
    xml_dir = os.path.join(rel_location(), "../../examples/")
    xml_files = [
        os.path.join(xml_dir, f)
        for f in os.listdir(xml_dir)
        if not "toolspecific.xml" in f and not "seat.stp" in f
    ]
    return xml_files


@pytest.fixture
def cpacs_schema():
    xsd_file = os.path.join(rel_location(), "../../schema/cpacs_schema.xsd")
    return xsd_file


def test_exampleFiles(cpacs_examples, cpacs_schema):

    tixi_h = tixi3wrapper.Tixi3()

    for xml in cpacs_examples:
        tixi_h.open(xml)
        if not tixi_h.schemaValidateFromFile(cpacs_schema):
            validationResult = True
        tixi_h.close()

        assert validationResult
