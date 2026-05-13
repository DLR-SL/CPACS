"""Syntax cleaner for CPACS XSD schema files."""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
import time
from pathlib import Path
from typing import Iterable

from lxml.etree import (
    XMLParser,
    _Element,
    Comment,
    indent,
    parse,
    register_namespace,
    tostring,
)

log = logging.getLogger(__name__)

# Attribute order for xsd:element / xsd:choice / xsd:attribute children.
ATTRIBUTE_ORDER = {
    name: i
    for i, name in enumerate(
        ("name", "minOccurs", "maxOccurs", "default", "use", "fixed", "type")
    )
}

# Tag-local-names whose attributes should be reordered.
ORDERED_TAGS = frozenset({"element", "choice", "attribute"})

# Top-level type names that should be placed before the alphabetically sorted
# custom types. Extend this tuple to pin additional base types in this section.
# Note: This list is not completely alphabetically sorted, since it needs to align
# with CPACSCreator, which expects specific baseTypes first.
BASE_TYPE_NAMES = (
    "complexBaseType",
    # These must come first:
    "stringArrayBaseType",
    "stringVectorBaseType",
    # Continue with remaining base types in alphabetical order:
    "booleanBaseType",
    "dateBaseType",
    "dateTimeBaseType",
    "doubleArrayBaseType",
    "doubleBaseType",
    "doubleConstraintBaseType",
    "doubleVectorBaseType",
    "doubleVectorConstraintBaseType",
    "integerBaseType",
    "posExcl0DoubleBaseType",
    "posExcl0IntBaseType",
    "posIntVectorBaseType",
    "stringBaseType",
    "stringUIDBaseType",
    "timeBaseType",
    "timeConstraintBaseType",
)


def _local_name(elem: _Element) -> str | None:
    """Return the tag's local name (without namespace), or None for comments/PIs."""
    tag = elem.tag
    if not isinstance(tag, str):
        # Comments and processing instructions have non-string tags.
        return None
    return tag.rsplit("}", 1)[-1]


class CPACSXSDSyntaxCleaner:
    NAMESPACES = {
        "xsd": "https://www.w3.org/2001/XMLSchema",
        "ddue": "http://ddue.schemas.microsoft.com/authoring/2003/5",
        "sd": "http://schemas.xsddoc.codeplex.com/schemaDoc/2009/3",
        "xlink": "https://www.w3.org/1999/xlink",
    }
    LICENSE_FILE = "license.txt"

    def __init__(self, schema_file: str | Path, schema_file_new: str | Path | None):
        self.schema_file = Path(schema_file)
        if schema_file_new is None:
            backup = Path(f"backup_{time.strftime('%Y%m%d_%H%M%S')}.xsd")
            shutil.copy(self.schema_file, backup)
            log.debug('Created backup at "%s"', backup)
            self.schema_file_new = self.schema_file
        else:
            self.schema_file_new = Path(schema_file_new)

    # ---------- I/O ----------

    def get_root_tree(self) -> _Element:
        parser = XMLParser(strip_cdata=False)
        tree = parse(str(self.schema_file), parser=parser)
        return tree.getroot()

    def set_namespaces(self) -> None:
        log.debug("\n> Set namespaces ...")
        for prefix, uri in self.NAMESPACES.items():
            register_namespace(prefix, uri)

    def read_license_information(self) -> str:
        license_path = Path(__file__).resolve().parent / self.LICENSE_FILE
        return license_path.read_text(encoding="utf-8")

    # ---------- Transformations ----------

    @staticmethod
    def sort_alphabetic(root: _Element) -> _Element:
        """Sort top-level definitions and add base/custom type sections.

        The top-level order is:
        1. the CPACS root element (`cpacs`)
        2. the root type definition (`cpacsType`)
        3. a base-type section with pinned names from `BASE_TYPE_NAMES`
        4. the remaining top-level definitions sorted alphabetically

        Existing top-level comments are removed because their intended position
        cannot be inferred reliably from the schema.
        """
        log.debug("\n> Alphabetic sorting ...")

        # Pop the two anchor elements; they go back at the top afterwards.
        cpacs_element = next(el for el in reversed(root) if el.get("name") == "cpacs")
        cpacs_type = next(el for el in reversed(root) if el.get("name") == "cpacsType")
        root.remove(cpacs_element)
        root.remove(cpacs_type)

        # Drop comments at the highest level (no `name` attribute).
        elements = [el for el in root if el.get("name") is not None]

        pinned_base_types: list[_Element] = []
        for base_type_name in BASE_TYPE_NAMES:
            base_type = next(
                (el for el in elements if el.get("name") == base_type_name),
                None,
            )
            if base_type is None:
                log.warning(' Base type "%s" not found; skipping.', base_type_name)
                continue
            elements.remove(base_type)
            pinned_base_types.append(base_type)

        root[:] = []
        root.append(cpacs_element)
        root.append(cpacs_type)

        if pinned_base_types:
            root.append(Comment(" ==== base types ==== "))
            root.extend(pinned_base_types)

        root.append(Comment(" ==== custom types ==== "))
        root.extend(sorted(elements, key=lambda el: el.get("name", "").lower()))
        return root

    @staticmethod
    def check_naming_conventions(root: _Element) -> _Element:
        """Enforce: lowercase first letter and `Type` suffix (except `cpacs`)."""
        log.debug("\n> Check for naming conventions ...")

        # Build an index: old name -> list of attribute references to update.
        # One traversal instead of one per renamed type.
        type_refs: dict[str, list[tuple[_Element, str]]] = {}
        for el in root.iter():
            for attr in ("type", "base"):
                value = el.get(attr)
                if value is not None:
                    type_refs.setdefault(value, []).append((el, attr))
            member_types = el.get("memberTypes")
            if member_types:
                # memberTypes is a whitespace-separated list; track each entry.
                for mt in member_types.split():
                    type_refs.setdefault(mt, []).append((el, "memberTypes"))

        for elem in root:
            name = elem.get("name")
            if not name:
                continue

            new_name = name
            if new_name[0].isupper():
                new_name = new_name[0].lower() + new_name[1:]
            if not new_name.endswith("Type") and new_name != "cpacs":
                new_name = new_name + "Type"

            if new_name == name:
                continue

            log.debug(' Renaming "%s" to "%s".', name, new_name)
            elem.set("name", new_name)
            for ref_el, attr in type_refs.get(name, ()):
                if attr == "memberTypes":
                    parts = ref_el.get("memberTypes", "").split()
                    ref_el.set(
                        "memberTypes",
                        " ".join(new_name if p == name else p for p in parts),
                    )
                else:
                    ref_el.set(attr, new_name)
        return root

    @staticmethod
    def arrange_attributes(root: _Element) -> _Element:
        """Reorder attributes on xsd:element, xsd:choice, and xsd:attribute.

        Drops redundant `minOccurs="1"` / `maxOccurs="1"` (they are the default).
        """
        log.debug("\n> Arrange attributes ...")

        for child in root.iter():
            if _local_name(child) not in ORDERED_TAGS:
                continue

            # Snapshot of current attributes; sort by canonical order, fall
            # back on alphabetical order for unknown keys.
            items = list(child.attrib.items())
            items.sort(
                key=lambda kv: (ATTRIBUTE_ORDER.get(kv[0], len(ATTRIBUTE_ORDER)), kv[0])
            )

            child.attrib.clear()
            for key, value in items:
                if key in ("minOccurs", "maxOccurs") and value == "1":
                    continue
                child.attrib[key] = value
        return root

    @staticmethod
    def find_unused_types(root: _Element) -> list[_Element]:
        types_used: set[str] = set()
        for el in root.iter():
            t = el.get("type")
            if t is not None:
                types_used.add(t)
            b = el.get("base")
            if b is not None:
                types_used.add(b)
            mt = el.get("memberTypes")
            if mt:
                types_used.update(mt.split())

        return [
            el
            for el in root
            if el.get("name") not in (None, "cpacs")
            and el.get("name") not in types_used
        ]

    @classmethod
    def remove_unused_types(cls, root: _Element) -> _Element:
        """Iteratively remove types nothing references (cascades)."""
        log.debug("\n> Removing unused types ...")
        while True:
            unused = cls.find_unused_types(root)
            if not unused:
                break
            for el in unused:
                log.debug(' Removing type "%s"', el.get("name"))
                root.remove(el)
        return root

    # ---------- Pipeline ----------

    def get_cleaned_root_tree(self) -> _Element:
        root = self.get_root_tree()
        self.set_namespaces()
        root = self.check_naming_conventions(root)
        root = self.arrange_attributes(root)
        root = self.remove_unused_types(root)
        root = self.sort_alphabetic(root)
        return root

    def pretty_print(self, root: _Element) -> str:
        log.debug("\n> Pretty print ...")

        indent(root, space=" " * 4)

        # Empty line between top-level types.
        for elem in root:
            elem.tail = "\n\n"

        root_str = tostring(root).decode("utf-8")

        # Tabs -> 4 spaces, strip trailing whitespace per line.
        root_str = root_str.replace("\t", " " * 4)
        root_str = "\n".join(line.rstrip() for line in root_str.splitlines()) + "\n"

        # Fix indent of complexType / simpleType blocks (lxml's indent does
        # not handle these top-level type definitions the way we want).
        root_str = root_str.replace("<xsd:complexType", "    <xsd:complexType")
        root_str = root_str.replace(
            "<xsd:simpleType name=", "    <xsd:simpleType name="
        )

        cpacs_license = self.read_license_information()
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + cpacs_license + root_str

    def write_cleaned_schema_file(self, root_str: str) -> None:
        log.debug('\n> Write schema to "%s" ...', self.schema_file_new)
        self.schema_file_new.write_text(root_str, encoding="utf-8")

    def run(self) -> None:
        log.debug("\n\n%s\nCPACS Syntax formatting", "=" * 70)
        root = self.get_cleaned_root_tree()
        root_str = self.pretty_print(root)
        self.write_cleaned_schema_file(root_str)


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="syntax_cleanup",
        description="Syntax cleaner for CPACS XSD Schema",
    )
    parser.add_argument("schema_input", help="Path to input schema file")
    parser.add_argument(
        "schema_output",
        nargs="?",
        default=None,
        help="Path to output schema file (optional; a backup is created if omitted)",
    )
    parser.add_argument("--log", default="DEBUG", help="Log level (default: DEBUG)")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(
        level=args.log.upper(),
        format="%(message)s",
        stream=sys.stdout,
    )
    CPACSXSDSyntaxCleaner(args.schema_input, args.schema_output).run()


if __name__ == "__main__":
    main()
