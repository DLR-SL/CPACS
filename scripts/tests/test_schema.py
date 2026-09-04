from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable

import pytest
from lxml.etree import XMLParser, XMLSyntaxError, _Element, parse

# Make imports work when this test module lives next to syntax_cleanup.py.
TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from syntax_cleanup import ATTRIBUTE_ORDER, BASE_TYPE_NAMES, ORDERED_TAGS  # noqa: E402


DEFAULT_SCHEMA_PATH = TEST_DIR / "../../schema/cpacs_schema.xsd"
SCHEMA_PATH_ENV = "CPACS_SCHEMA_FILE"


def local_name(elem: _Element) -> str | None:
    """Return an XML element's local tag name; comments/PIs return None."""
    tag = elem.tag
    if not isinstance(tag, str):
        return None
    return tag.rsplit("}", 1)[-1]


def top_level_names(root: _Element) -> list[str]:
    """Return the names of all top-level schema entries, excluding comments."""
    return [name for elem in root if (name := elem.get("name"))]


def named_top_level_entries(root: _Element) -> list[_Element]:
    """Return all named top-level schema entries, excluding comments."""
    return [elem for elem in root if elem.get("name")]


def schema_section_comments(root: _Element) -> dict[str, int]:
    """Return indices of known top-level section comments."""
    comments: dict[str, int] = {}
    for index, elem in enumerate(root):
        text = (elem.text or "").strip() if local_name(elem) is None else ""
        if "base types" in text:
            comments["base types"] = index
        elif "custom types" in text:
            comments["custom types"] = index
    return comments


def ordered_schema_children(root: _Element) -> Iterable[_Element]:
    """Yield nodes whose attributes are normalized by the syntax cleaner."""
    return (elem for elem in root.iter() if local_name(elem) in ORDERED_TAGS)


@pytest.fixture(scope="session")
def cpacs_schema_file() -> Path:
    return Path(os.environ.get(SCHEMA_PATH_ENV, DEFAULT_SCHEMA_PATH)).resolve()


@pytest.fixture(scope="session")
def root_tree(cpacs_schema_file: Path) -> _Element:
    parser = XMLParser(strip_cdata=False)
    try:
        return parse(str(cpacs_schema_file), parser=parser).getroot()
    except OSError as exc:
        pytest.fail(f'Failed loading "{cpacs_schema_file}": {exc}')
    except XMLSyntaxError as exc:
        pytest.fail(f'"{cpacs_schema_file}" is not a well-formed XML schema: {exc}')


def test_top_level_sorting_with_base_type_section(root_tree: _Element) -> None:
    """Top-level order: cpacs, cpacsType, pinned base types, custom types A-Z."""
    names = top_level_names(root_tree)
    assert names[:2] == ["cpacs", "cpacsType"]

    present_base_types = [name for name in BASE_TYPE_NAMES if name in names]
    base_start = 2
    base_end = base_start + len(present_base_types)

    assert names[base_start:base_end] == present_base_types

    custom_types = names[base_end:]
    expected_custom_types = sorted(
        (
            name
            for name in names
            if name not in {"cpacs", "cpacsType", *present_base_types}
        ),
        key=str.lower,
    )
    assert custom_types == expected_custom_types


def test_top_level_section_comments(root_tree: _Element) -> None:
    """The generated XSD should contain base/custom section comments."""
    comments = schema_section_comments(root_tree)

    assert "base types" in comments
    assert "custom types" in comments
    assert comments["base types"] < comments["custom types"]

    cpacs_type_index = next(
        index for index, elem in enumerate(root_tree) if elem.get("name") == "cpacsType"
    )
    assert comments["base types"] > cpacs_type_index


def test_type_names_start_lowercase(root_tree: _Element) -> None:
    invalid_names = [
        elem.get("name")
        for elem in named_top_level_entries(root_tree)
        if not elem.get("name", "")[0].islower()
    ]
    assert not invalid_names


def test_type_names_end_with_type_except_root_element(root_tree: _Element) -> None:
    invalid_names = [
        elem.get("name")
        for elem in named_top_level_entries(root_tree)
        if elem.get("name") != "cpacs" and not elem.get("name", "").endswith("Type")
    ]
    assert not invalid_names


def test_attribute_arrangement(root_tree: _Element) -> None:
    """Attributes should follow syntax_cleanup.ATTRIBUTE_ORDER, then A-Z fallback."""
    invalid_attributes: list[tuple[str | None, list[str], list[str]]] = []

    for elem in ordered_schema_children(root_tree):
        attributes = list(elem.keys())
        expected_attributes = sorted(
            attributes,
            key=lambda attr: (ATTRIBUTE_ORDER.get(attr, len(ATTRIBUTE_ORDER)), attr),
        )
        if attributes != expected_attributes:
            invalid_attributes.append((elem.get("name"), attributes, expected_attributes))

    assert not invalid_attributes


@pytest.mark.parametrize("attribute", ["minOccurs", "maxOccurs"])
def test_default_occurrence_attributes_are_omitted(
    root_tree: _Element,
    attribute: str,
) -> None:
    """minOccurs/maxOccurs default value 1 should not be written explicitly."""
    offenders = [
        elem.get("name") or local_name(elem)
        for elem in ordered_schema_children(root_tree)
        if elem.get(attribute) == "1"
    ]
    assert not offenders


def test_no_unused_types(root_tree: _Element) -> None:
    """Every top-level type must be referenced by type, base, or memberTypes."""
    existing_types = {
        elem.get("name")
        for elem in named_top_level_entries(root_tree)
        if elem.get("name") != "cpacs"
    }

    used_types: set[str] = set()
    for elem in root_tree.iter():
        if type_ref := elem.get("type"):
            used_types.add(type_ref)
        if base_ref := elem.get("base"):
            used_types.add(base_ref)
        if member_types := elem.get("memberTypes"):
            used_types.update(member_types.split())

    unused_types = sorted(existing_types - used_types, key=str.lower)
    assert not unused_types
