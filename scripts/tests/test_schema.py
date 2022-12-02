import logging
import os
import sys

import pytest
from lxml.etree import XMLParser, indent, parse, register_namespace, tostring

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler(sys.stdout))


def get_elem_type(elem):
    try:
        return elem.tag.split("}")[-1]
    except Exception as e:
        log.debug(e)
        return None


@pytest.fixture
def rel_location():
    __location__ = os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__))
    )
    return __location__


@pytest.fixture
def cpacs_schema_file(rel_location):
    return os.path.join(rel_location, "../../schema/cpacs_schema.xsd")


@pytest.fixture
def get_root_tree(cpacs_schema_file):
    """
    Returns all elements of the schema
    """
    parser = XMLParser(strip_cdata=False)
    try:
        tree = parse(cpacs_schema_file, parser=parser)
        root = tree.getroot()
        return root
    except:
        pytest.fail(
            'Failed loading "%s"! Maybe it is not well formed schema file...'
            % cpacs_schema_file
        )


def test_alphabetic_sorting(get_root_tree):
    """
    The list of types should be ordered alphabetically. The only exception is that the
    first tag is always the root element "cpacs" followed by "cpacsType".
    """
    root = get_root_tree
    elements = [el.get("name") for el in root if el.get("name")]
    elements_sorted = elements.copy()
    elements_sorted.sort(key=lambda el: el.lower())
    elements_sorted = ["cpacs", "cpacsType"] + [
        el for el in elements_sorted if el != "cpacs" and el != "cpacsType"
    ]
    assert elements == elements_sorted


def test_lowerCase_typeNames(get_root_tree):
    """
    Types names must begin with lower case letter. The following list parses for the first
    letter of each element and returns True if it starts with lower case.
    """
    root = get_root_tree

    lower_case_letters = [el.get("name")[0].islower() for el in root if el.get("name")]
    assert all(lower_case_letters)


def test_typeNames_endingWithType(get_root_tree):
    """
    Types must end with "None"
    """
    root = get_root_tree

    ends_with_type = [el.get("name")[-4:] == "Type" for el in root if el.get("name")]
    assert True


def test_attribute_arrangement(get_root_tree):
    """
    Attributes must occur in the following sequence:
        elements: name, minOccurs, maxOccurs, default, type
        attributes: name, default, use, fixed
        choice: minOccurs, maxOccurs
    """
    root = get_root_tree

    attributes_order = {
        key: i
        for i, key in enumerate(
            ["name", "minOccurs", "maxOccurs", "default", "use", "fixed", "type"]
        )
    }

    for elem in root:
        children = [
            child
            for child in list(elem.iter())
            if get_elem_type(child) in {"element", "choice", "attribute"}
        ]
        for child in children:
            attributes = child.keys()
            attributes_sorted = sorted(attributes, key=lambda d: attributes_order[d])
            assert attributes == attributes_sorted


def test_default_attributes(get_root_tree):
    """
    Attributes with default values should not be specified in the schema, for example:
    minOccurs="1", maxOccurs="1"
    """
    root = get_root_tree

    for elem in root:
        children = [
            child
            for child in list(elem.iter())
            if get_elem_type(child) in {"element", "choice", "attribute"}
        ]
        for child in children:
            attributes = child.keys()
            if "minOccurs" in child.keys():
                if child.attrib["minOccurs"] == "1":
                    assert False
            if "maxOccurs" in child.keys():
                if child.attrib["maxOccurs"] == "1":
                    assert False


def test_unused_types(get_root_tree):
    """
    There must not be unused types in the schema
    """
    root = get_root_tree

    types_exist = [el for el in root if el.get("name") != "cpacs" and el.get("name")]
    types_used = set(
        [el.attrib["type"] for el in list(root.iter()) if "type" in el.keys()]
        + [el.attrib["base"] for el in list(root.iter()) if "base" in el.keys()]
    )
    types_unused = [
        t.attrib["name"] for t in types_exist if not t.attrib["name"] in types_used
    ]

    assert len(types_unused) == 0
