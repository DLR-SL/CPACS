#!/usr/bin/env python3
"""CPACS-oriented XML Schema formatter, checker, linter, and migration tool.

The tool deliberately separates safe, semantics-preserving formatting from
schema-changing migrations:

* ``format`` normalizes representation only.
* ``check`` verifies that a schema already matches the normalized form.
* ``lint`` reports CPACS conventions and XSD consistency problems.
* ``rename-types`` explicitly normalizes global type names and their references.
* ``prune-unused`` explicitly removes unreachable global type definitions.

The implementation focuses on the XSD constructs used by the monolithic CPACS
schema while also understanding the common reference attributes ``type``,
``base``, ``itemType``, ``memberTypes``, ``ref``, and ``substitutionGroup``.
Project-specific naming, ordering, formatting, reachability, and lint policies are
loaded from the adjacent ``schema_rules.toml`` file or an explicit ``--rules``
path.
"""

from __future__ import annotations

import argparse
import copy
import difflib
import os
import re
import shutil
import sys
import tempfile
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

from lxml import etree

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:  # pragma: no cover - handled by load_policy
        tomllib = None  # type: ignore[assignment]


XSD_NS = "http://www.w3.org/2001/XMLSchema"
XLINK_NS = "http://www.w3.org/1999/xlink"
XSD = f"{{{XSD_NS}}}"

DEFAULT_RULES_PATH = Path(__file__).resolve().with_name("schema_rules.toml")
ALLOWED_SEVERITIES = frozenset({"error", "warning", "info"})

# XSD particles for which minOccurs="1" and maxOccurs="1" are redundant.
PARTICLE_TAGS = frozenset({"element", "group", "all", "choice", "sequence"})

GLOBAL_COMPONENT_KIND: Mapping[str, str] = {
    "complexType": "type",
    "simpleType": "type",
    "element": "element",
    "attribute": "attribute",
    "group": "group",
    "attributeGroup": "attributeGroup",
    "notation": "notation",
}

PRELUDE_TAGS = frozenset(
    {"annotation", "include", "import", "redefine", "override", "defaultOpenContent"}
)

REF_KIND_BY_OWNER = {
    "element": "element",
    "attribute": "attribute",
    "group": "group",
    "attributeGroup": "attributeGroup",
}

TYPE_REFERENCE_ATTRIBUTES = frozenset({"type", "base", "itemType"})


@dataclass(frozen=True, order=True)
class ComponentKey:
    kind: str
    name: str


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: str
    message: str
    line: int | None = None
    xpath: str | None = None

    def __str__(self) -> str:
        location_parts: list[str] = []
        if self.line is not None:
            location_parts.append(f"line {self.line}")
        if self.xpath:
            location_parts.append(self.xpath)
        location = f" ({', '.join(location_parts)})" if location_parts else ""
        return f"{self.severity.upper()} {self.code}{location}: {self.message}"


class SchemaToolError(RuntimeError):
    """Expected user-facing schema-tool failure."""


@dataclass(frozen=True)
class LintRulePolicy:
    enabled: bool
    severity: str


@dataclass(frozen=True)
class SchemaPolicy:
    source: Path
    root_element: str
    root_type: str
    indent_size: int
    remove_redundant_occurs_one: bool
    attribute_order: tuple[str, ...]
    base_types_comment: str
    custom_types_comment: str
    base_types: tuple[str, ...]
    type_first_character: str
    type_required_suffix: str
    type_exceptions: frozenset[str]
    reachability_keep: tuple[str, ...]
    xsd_prefix: str
    xlink_prefix: str
    rules: Mapping[str, LintRulePolicy]
    explicit_type_renames: Mapping[str, str]

    @property
    def attribute_rank(self) -> Mapping[str, int]:
        return {name: index for index, name in enumerate(self.attribute_order)}

    @property
    def base_type_rank(self) -> Mapping[str, int]:
        return {name: index for index, name in enumerate(self.base_types)}

    @property
    def generated_section_comments(self) -> frozenset[str]:
        return frozenset(
            value
            for value in (self.base_types_comment, self.custom_types_comment)
            if value
        )

    def rule(
        self,
        code: str,
        *,
        default_severity: str,
    ) -> LintRulePolicy:
        return self.rules.get(
            code,
            LintRulePolicy(enabled=True, severity=default_severity),
        )


def _mapping(table: Mapping[str, Any], key: str, *, path: str) -> Mapping[str, Any]:
    value = table.get(key)
    if not isinstance(value, Mapping):
        raise SchemaToolError(f"Missing or invalid TOML table [{path}].")
    return value


def _get(
    table: Mapping[str, Any],
    *keys: str,
    default: Any = None,
) -> Any:
    for key in keys:
        if key in table:
            return table[key]
    return default


def _required_string(
    table: Mapping[str, Any],
    *keys: str,
    path: str,
) -> str:
    value = _get(table, *keys)
    if not isinstance(value, str) or not value.strip():
        joined = " or ".join(repr(key) for key in keys)
        raise SchemaToolError(f"{path} must define a non-empty string {joined}.")
    return value


def _string_list(value: Any, *, path: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise SchemaToolError(f"{path} must be an array of strings.")
    duplicates = sorted({item for item in value if value.count(item) > 1})
    if duplicates:
        raise SchemaToolError(
            f"{path} contains duplicate values: {', '.join(repr(x) for x in duplicates)}"
        )
    return tuple(value)


def load_policy(path: Path) -> SchemaPolicy:
    """Load and validate CPACS policy from TOML."""
    if tomllib is None:
        raise SchemaToolError(
            "TOML support is unavailable. With Python 3.10 install tomli>=2,<3; "
            "Python 3.11 and newer provide tomllib."
        )
    if not path.is_file():
        raise SchemaToolError(f"Schema rules file not found: {path}")

    try:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise SchemaToolError(f"Cannot read schema rules {path}: {exc}") from exc

    schema = _mapping(raw, "schema", path="schema")
    formatting = _mapping(raw, "format", path="format")
    naming = _mapping(raw, "naming", path="naming")
    naming_types = _mapping(naming, "types", path="naming.types")
    reachability = _mapping(raw, "reachability", path="reachability")
    prefixes = _mapping(raw, "prefixes", path="prefixes")
    raw_rules = _mapping(raw, "rules", path="rules")
    renames = _mapping(raw, "renames", path="renames")
    rename_types = _mapping(renames, "types", path="renames.types")

    indent_size = _get(formatting, "indent_size", "indent-size")
    if not isinstance(indent_size, int) or isinstance(indent_size, bool) or indent_size < 1:
        raise SchemaToolError("format.indent_size must be a positive integer.")

    remove_occurs = _get(
        formatting,
        "remove_redundant_occurs_one",
        "remove-redundant-occurs-one",
    )
    if not isinstance(remove_occurs, bool):
        raise SchemaToolError(
            "format.remove_redundant_occurs_one must be true or false."
        )

    first_character = _required_string(
        naming_types,
        "first_character",
        "first-character",
        path="naming.types",
    )
    if first_character not in {"lower", "unchanged"}:
        raise SchemaToolError(
            "naming.types.first_character must be 'lower' or 'unchanged'."
        )

    rule_policies: dict[str, LintRulePolicy] = {}
    for code, value in raw_rules.items():
        if not isinstance(value, Mapping):
            raise SchemaToolError(f"rules.{code} must be a TOML table.")
        enabled = value.get("enabled", True)
        severity = value.get("severity", "warning")
        if not isinstance(enabled, bool):
            raise SchemaToolError(f"rules.{code}.enabled must be true or false.")
        if not isinstance(severity, str) or severity not in ALLOWED_SEVERITIES:
            raise SchemaToolError(
                f"rules.{code}.severity must be one of: "
                + ", ".join(sorted(ALLOWED_SEVERITIES))
            )
        rule_policies[str(code)] = LintRulePolicy(enabled, severity)

    explicit_renames: dict[str, str] = {}
    for old, new in rename_types.items():
        if not isinstance(old, str) or not isinstance(new, str) or not new.strip():
            raise SchemaToolError(
                "Every entry in [renames.types] must map a name to a non-empty string."
            )
        explicit_renames[old] = new

    policy = SchemaPolicy(
        source=path.resolve(),
        root_element=_required_string(
            schema, "root_element", "root-element", path="schema"
        ),
        root_type=_required_string(schema, "root_type", "root-type", path="schema"),
        indent_size=indent_size,
        remove_redundant_occurs_one=remove_occurs,
        attribute_order=_string_list(
            _get(formatting, "attribute_order", "attribute-order"),
            path="format.attribute_order",
        ),
        base_types_comment=str(
            _get(
                formatting,
                "base_types_comment",
                "base-types-comment",
                default="",
            )
        ),
        custom_types_comment=str(
            _get(
                formatting,
                "custom_types_comment",
                "custom-types-comment",
                default="",
            )
        ),
        base_types=_string_list(
            _get(formatting, "base_types", "base-types"),
            path="format.base_types",
        ),
        type_first_character=first_character,
        type_required_suffix=_required_string(
            naming_types,
            "required_suffix",
            "required-suffix",
            path="naming.types",
        ),
        type_exceptions=frozenset(
            _string_list(
                _get(naming_types, "exceptions", default=[]),
                path="naming.types.exceptions",
            )
        ),
        reachability_keep=_string_list(
            _get(reachability, "keep", default=[]),
            path="reachability.keep",
        ),
        xsd_prefix=_required_string(prefixes, "xsd", path="prefixes"),
        xlink_prefix=_required_string(prefixes, "xlink", path="prefixes"),
        rules=rule_policies,
        explicit_type_renames=explicit_renames,
    )

    if policy.root_type in policy.base_types:
        raise SchemaToolError(
            "schema.root_type must not also be listed in format.base_types."
        )
    return policy


def local_name(node: etree._Element) -> str | None:
    """Return an element/attribute local name, or ``None`` for comments/PIs."""
    tag = node.tag
    if not isinstance(tag, str):
        return None
    return etree.QName(tag).localname


def namespace_uri(node: etree._Element) -> str | None:
    tag = node.tag
    if not isinstance(tag, str):
        return None
    return etree.QName(tag).namespace


def is_comment(node: etree._Element) -> bool:
    return isinstance(node, etree._Comment)


def normalized_comment_text(node: etree._Element) -> str:
    return " ".join((node.text or "").split())


def parser() -> etree.XMLParser:
    return etree.XMLParser(
        strip_cdata=False,
        remove_comments=False,
        remove_pis=False,
        resolve_entities=False,
        no_network=True,
        huge_tree=True,
    )


def parse_schema(path: Path) -> etree._ElementTree:
    if not path.is_file():
        raise SchemaToolError(f"Schema file not found: {path}")

    try:
        tree = etree.parse(str(path), parser())
    except (OSError, etree.XMLSyntaxError) as exc:
        raise SchemaToolError(f"Cannot parse XML schema {path}: {exc}") from exc

    root = tree.getroot()
    if root.tag != f"{XSD}schema":
        raise SchemaToolError(
            f"Root element must be {{{XSD_NS}}}schema, found {root.tag!r}."
        )
    return tree


def clone_tree(tree: etree._ElementTree) -> etree._ElementTree:
    return etree.ElementTree(copy.deepcopy(tree.getroot()))


def xpath_for(node: etree._Element) -> str | None:
    try:
        return node.getroottree().getpath(node)
    except (ValueError, AttributeError):
        return None


def diagnostic(
    code: str,
    severity: str,
    message: str,
    node: etree._Element | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=severity,
        message=message,
        line=node.sourceline if node is not None else None,
        xpath=xpath_for(node) if node is not None else None,
    )


def validate_schema(tree: etree._ElementTree) -> list[Diagnostic]:
    """Compile the document as XML Schema and return diagnostics."""
    try:
        etree.XMLSchema(tree)
        return []
    except etree.XMLSchemaParseError as exc:
        result: list[Diagnostic] = []
        for entry in exc.error_log:
            result.append(
                Diagnostic(
                    code="XSD001",
                    severity="error",
                    message=entry.message,
                    line=entry.line or None,
                )
            )
        if not result:
            result.append(Diagnostic("XSD001", "error", str(exc)))
        return result


def expanded_attr_local_name(attribute_name: str) -> str:
    if attribute_name.startswith("{"):
        return etree.QName(attribute_name).localname
    return attribute_name


def arrange_attributes(root: etree._Element, policy: SchemaPolicy) -> None:
    """Normalize XSD attribute order and optional occurrence defaults."""
    attribute_rank = policy.attribute_rank
    for node in root.iter():
        if namespace_uri(node) != XSD_NS:
            continue

        lname = local_name(node)
        attributes = list(node.attrib.items())
        attributes.sort(
            key=lambda item: (
                attribute_rank.get(
                    expanded_attr_local_name(item[0]), len(attribute_rank)
                ),
                expanded_attr_local_name(item[0]).casefold(),
                item[0],
            )
        )

        node.attrib.clear()
        for key, value in attributes:
            attr_local = expanded_attr_local_name(key)
            if (
                policy.remove_redundant_occurs_one
                and lname in PARTICLE_TAGS
                and attr_local in {"minOccurs", "maxOccurs"}
                and value == "1"
            ):
                continue
            node.set(key, value)


def declaration_sort_key(
    node: etree._Element, policy: SchemaPolicy
) -> tuple[int, int, str, str]:
    lname = local_name(node) or ""
    name = node.get("name", "")
    base_type_rank = policy.base_type_rank

    if lname == "element" and name == policy.root_element:
        return (0, 0, "", "")
    if lname in {"complexType", "simpleType"} and name == policy.root_type:
        return (1, 0, "", "")
    if lname in {"complexType", "simpleType"} and name in base_type_rank:
        return (2, base_type_rank[name], "", "")
    return (3, 0, name.casefold(), lname)


def sort_top_level(root: etree._Element, policy: SchemaPolicy) -> None:
    """Sort global declarations while preserving comments attached to them.

    Existing non-generated comments immediately preceding a declaration travel
    with that declaration. Prelude constructs such as xsd:annotation/import are
    kept before global declarations and unknown constructs are retained after
    them rather than being silently discarded.
    """
    children = list(root)
    for child in children:
        root.remove(child)

    prelude: list[etree._Element] = []
    declaration_blocks: list[tuple[list[etree._Element], etree._Element]] = []
    trailing: list[etree._Element] = []
    pending: list[etree._Element] = []
    declarations_started = False

    for child in children:
        if is_comment(child) and normalized_comment_text(child) in policy.generated_section_comments:
            continue

        lname = local_name(child)
        is_global_declaration = (
            namespace_uri(child) == XSD_NS
            and lname in GLOBAL_COMPONENT_KIND
            and child.get("name") is not None
        )

        if is_comment(child) or lname is None:
            pending.append(child)
            continue

        if not declarations_started and namespace_uri(child) == XSD_NS and lname in PRELUDE_TAGS:
            prelude.extend(pending)
            pending.clear()
            prelude.append(child)
            continue

        if is_global_declaration:
            declarations_started = True
            declaration_blocks.append((pending, child))
            pending = []
            continue

        # Preserve unsupported or unnamed top-level content instead of deleting it.
        trailing.extend(pending)
        pending.clear()
        trailing.append(child)

    trailing.extend(pending)

    declaration_blocks.sort(key=lambda block: declaration_sort_key(block[1], policy))

    root.extend(prelude)

    inserted_base_marker = False
    inserted_custom_marker = False
    for comments, declaration in declaration_blocks:
        key = declaration_sort_key(declaration, policy)
        if key[0] == 2 and policy.base_types_comment and not inserted_base_marker:
            root.append(etree.Comment(f" {policy.base_types_comment} "))
            inserted_base_marker = True
        if key[0] == 3 and policy.custom_types_comment and not inserted_custom_marker:
            root.append(etree.Comment(f" {policy.custom_types_comment} "))
            inserted_custom_marker = True
        root.extend(comments)
        root.append(declaration)

    root.extend(trailing)


def normalize_whitespace(root: etree._Element, policy: SchemaPolicy) -> None:
    indent_size = policy.indent_size
    etree.indent(root, space=" " * indent_size)

    # One empty line between global components and section comments while
    # retaining the indentation of the following top-level child.
    children = list(root)
    for index, child in enumerate(children):
        child.tail = "\n" if index == len(children) - 1 else "\n\n" + " " * indent_size


def read_license_text(input_path: Path) -> str:
    """Read the repository license header, falling back to the input preamble."""
    license_path = Path(__file__).resolve().parent / "license.txt"
    if license_path.is_file():
        return license_path.read_text(encoding="utf-8").rstrip() + "\n"

    raw = input_path.read_text(encoding="utf-8")
    declaration_end = raw.find("?>")
    search_start = declaration_end + 2 if declaration_end >= 0 else 0
    schema_match = re.search(
        r"<(?:[A-Za-z_][\w.-]*:)?schema\b", raw[search_start:]
    )
    if schema_match is None:
        return ""
    schema_start = search_start + schema_match.start()
    preamble = raw[search_start:schema_start].strip()
    return preamble + "\n" if preamble else ""


def serialize_schema(
    tree: etree._ElementTree, input_path: Path, policy: SchemaPolicy
) -> str:
    root = tree.getroot()
    root_text = etree.tostring(
        root,
        encoding="unicode",
        pretty_print=False,
        with_tail=False,
    )
    root_text = root_text.replace("\t", " " * policy.indent_size)
    root_text = "\n".join(line.rstrip() for line in root_text.splitlines()) + "\n"

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        + read_license_text(input_path)
        + root_text
    )


def formatted_tree(
    tree: etree._ElementTree, policy: SchemaPolicy
) -> etree._ElementTree:
    result = clone_tree(tree)
    root = result.getroot()
    arrange_attributes(root, policy)
    sort_top_level(root, policy)
    normalize_whitespace(root, policy)
    return result


def parse_text_as_schema(text: str, source_name: str = "<memory>") -> etree._ElementTree:
    try:
        root = etree.fromstring(text.encode("utf-8"), parser=parser(), base_url=source_name)
    except etree.XMLSyntaxError as exc:
        raise SchemaToolError(f"Generated schema is not well-formed XML: {exc}") from exc
    return etree.ElementTree(root)


def validate_generated_text(text: str, source_name: str) -> None:
    generated_tree = parse_text_as_schema(text, source_name)
    errors = validate_schema(generated_tree)
    if errors:
        details = "\n".join(str(item) for item in errors[:20])
        raise SchemaToolError(
            "Generated output does not compile as XML Schema:\n" + details
        )


def write_atomic(
    text: str,
    target: Path,
    *,
    source: Path,
    backup: bool,
    validate: bool,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)

    if validate:
        validate_generated_text(text, str(target))

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(text)

    try:
        if backup and target.exists():
            backup_path = target.with_suffix(target.suffix + ".bak")
            shutil.copy2(target, backup_path)
            print(f"Created backup: {backup_path}")
        os.replace(temp_path, target)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    if target.resolve() == source.resolve():
        print(f"Updated schema in place: {target}")
    else:
        print(f"Wrote schema: {target}")


def resolve_output_target(
    input_path: Path,
    output: str | None,
    in_place: bool,
) -> Path | None:
    if in_place and output:
        raise SchemaToolError("Use either an output path or --in-place, not both.")
    if in_place:
        return input_path
    if output:
        target = Path(output)
        if target.resolve() == input_path.resolve():
            raise SchemaToolError(
                "Refusing to overwrite the input without the explicit --in-place option."
            )
        return target
    return None


def output_schema_text(
    text: str,
    *,
    input_path: Path,
    output: str | None,
    in_place: bool,
    backup: bool,
    validate: bool,
) -> None:
    target = resolve_output_target(input_path, output, in_place)
    if target is None:
        if validate:
            validate_generated_text(text, str(input_path))
        sys.stdout.write(text)
        return
    write_atomic(text, target, source=input_path, backup=backup, validate=validate)


def normalized_type_name(name: str, policy: SchemaPolicy) -> str:
    explicit = policy.explicit_type_renames.get(name)
    if explicit is not None:
        return explicit
    if name in policy.type_exceptions:
        return name

    result = name
    if (
        policy.type_first_character == "lower"
        and result
        and result[0].isupper()
    ):
        result = result[0].lower() + result[1:]
    if policy.type_required_suffix and not result.endswith(policy.type_required_suffix):
        result += policy.type_required_suffix
    return result


def global_components(root: etree._Element) -> dict[ComponentKey, etree._Element]:
    components: dict[ComponentKey, etree._Element] = {}
    for child in root:
        if namespace_uri(child) != XSD_NS:
            continue
        lname = local_name(child)
        kind = GLOBAL_COMPONENT_KIND.get(lname or "")
        name = child.get("name")
        if kind is None or name is None:
            continue
        key = ComponentKey(kind, name)
        if key in components:
            raise SchemaToolError(
                f"Duplicate global {kind} component named {name!r}."
            )
        components[key] = child
    return components


def split_lexical_qname(value: str) -> tuple[str | None, str]:
    if ":" in value:
        prefix, local = value.split(":", 1)
        return prefix, local
    return None, value


def resolve_lexical_qname(
    value: str, context: etree._Element
) -> tuple[str | None, str, str | None]:
    prefix, local = split_lexical_qname(value)
    uri = context.nsmap.get(prefix) if prefix is not None else context.nsmap.get(None)
    return uri, local, prefix


def is_local_component_reference(
    uri: str | None, root: etree._Element
) -> bool:
    target_namespace = root.get("targetNamespace")
    if target_namespace:
        return uri == target_namespace
    return uri is None


def iter_qname_references(
    component: etree._Element,
    schema_root: etree._Element,
) -> Iterator[tuple[ComponentKey, etree._Element, str, str]]:
    """Yield referenced global components understood by this tool."""
    for node in component.iter():
        for attribute_name in TYPE_REFERENCE_ATTRIBUTES:
            value = node.get(attribute_name)
            if not value:
                continue
            uri, name, _prefix = resolve_lexical_qname(value, node)
            if uri == XSD_NS or not is_local_component_reference(uri, schema_root):
                continue
            yield ComponentKey("type", name), node, attribute_name, value

        member_types = node.get("memberTypes")
        if member_types:
            for value in member_types.split():
                uri, name, _prefix = resolve_lexical_qname(value, node)
                if uri == XSD_NS or not is_local_component_reference(uri, schema_root):
                    continue
                yield ComponentKey("type", name), node, "memberTypes", value

        ref = node.get("ref")
        owner_kind = REF_KIND_BY_OWNER.get(local_name(node) or "")
        if ref and owner_kind:
            uri, name, _prefix = resolve_lexical_qname(ref, node)
            if uri != XSD_NS and is_local_component_reference(uri, schema_root):
                yield ComponentKey(owner_kind, name), node, "ref", ref

        substitution_group = node.get("substitutionGroup")
        if substitution_group:
            uri, name, _prefix = resolve_lexical_qname(substitution_group, node)
            if uri != XSD_NS and is_local_component_reference(uri, schema_root):
                yield (
                    ComponentKey("element", name),
                    node,
                    "substitutionGroup",
                    substitution_group,
                )


def reachable_components(
    root: etree._Element,
    components: Mapping[ComponentKey, etree._Element],
    start: Iterable[ComponentKey],
) -> tuple[set[ComponentKey], list[tuple[ComponentKey, etree._Element, str, str]]]:
    reachable: set[ComponentKey] = set()
    unresolved: list[tuple[ComponentKey, etree._Element, str, str]] = []
    queue: deque[ComponentKey] = deque(start)

    while queue:
        key = queue.popleft()
        if key in reachable:
            continue
        component = components.get(key)
        if component is None:
            unresolved.append((key, root, "root", key.name))
            continue
        reachable.add(key)

        for dependency, node, attribute, lexical_value in iter_qname_references(
            component, root
        ):
            if dependency not in components:
                unresolved.append((dependency, node, attribute, lexical_value))
            elif dependency not in reachable:
                queue.append(dependency)

    return reachable, unresolved


def unused_type_components(
    root: etree._Element,
    *,
    root_element: str,
    keep: Iterable[str] = (),
) -> tuple[list[ComponentKey], list[tuple[ComponentKey, etree._Element, str, str]]]:
    components = global_components(root)
    start: list[ComponentKey] = [ComponentKey("element", root_element)]

    for name in keep:
        matching = [key for key in components if key.name == name]
        if not matching:
            raise SchemaToolError(f"--keep component not found: {name}")
        start.extend(matching)

    reachable, unresolved = reachable_components(root, components, start)
    unused = sorted(
        key
        for key in components
        if key.kind == "type" and key not in reachable
    )
    return unused, unresolved


def lint_schema(
    tree: etree._ElementTree,
    policy: SchemaPolicy,
    include_unused: bool = True,
) -> list[Diagnostic]:
    root = tree.getroot()
    result: list[Diagnostic] = []
    result.extend(validate_schema(tree))

    def emit(
        code: str,
        message: str,
        *,
        node: etree._Element | None = None,
        default_severity: str = "warning",
    ) -> None:
        rule = policy.rule(code, default_severity=default_severity)
        if not rule.enabled:
            return
        result.append(diagnostic(code, rule.severity, message, node))

    try:
        components = global_components(root)
    except SchemaToolError as exc:
        emit("CPACS001", str(exc), default_severity="error")
        return result

    root_key = ComponentKey("element", policy.root_element)
    root_element = components.get(root_key)
    if root_element is None:
        emit(
            "CPACS002",
            f"Missing global root element {policy.root_element!r}.",
            default_severity="error",
        )
    else:
        root_type = root_element.get("type")
        _uri, root_type_local, _prefix = (
            resolve_lexical_qname(root_type, root_element)
            if root_type
            else (None, "", None)
        )
        if root_type_local != policy.root_type:
            emit(
                "CPACS003",
                f"Root element {policy.root_element!r} must use type "
                f"{policy.root_type!r}, found {root_type!r}.",
                node=root_element,
                default_severity="error",
            )

    type_components = {
        key: node for key, node in components.items() if key.kind == "type"
    }

    final_names: dict[str, list[str]] = {}
    for key, node in type_components.items():
        expected = normalized_type_name(key.name, policy)
        final_names.setdefault(expected, []).append(key.name)
        if expected != key.name:
            emit(
                "CPACS004",
                f"Global type {key.name!r} does not follow the configured CPACS "
                f"naming convention; expected {expected!r}.",
                node=node,
                default_severity="error",
            )

    for expected, originals in sorted(final_names.items()):
        if len(originals) > 1:
            emit(
                "CPACS005",
                f"Type-name normalization collision for {expected!r}: "
                + ", ".join(repr(name) for name in originals),
                default_severity="error",
            )

    for base_type in policy.base_types:
        if ComponentKey("type", base_type) not in components:
            emit(
                "CPACS006",
                f"Configured CPACS base type {base_type!r} is missing.",
                default_severity="warning",
            )

    if policy.remove_redundant_occurs_one:
        for node in root.iter():
            lname = local_name(node)
            if namespace_uri(node) == XSD_NS and lname in PARTICLE_TAGS:
                for attr in ("minOccurs", "maxOccurs"):
                    if node.get(attr) == "1":
                        emit(
                            "CPACS007",
                            f'Explicit {attr}="1" is redundant.',
                            node=node,
                            default_severity="warning",
                        )

    seen_unresolved: set[tuple[ComponentKey, int | None, str, str]] = set()
    for component in components.values():
        for key, node, attribute, lexical_value in iter_qname_references(
            component, root
        ):
            if key in components:
                continue
            marker = (key, node.sourceline, attribute, lexical_value)
            if marker in seen_unresolved:
                continue
            seen_unresolved.add(marker)
            emit(
                "CPACS008",
                f"Unresolved local {key.kind} reference {lexical_value!r} "
                f"in @{attribute}.",
                node=node,
                default_severity="error",
            )

    if include_unused and root_element is not None:
        try:
            unused, _unresolved = unused_type_components(
                root,
                root_element=policy.root_element,
                keep=policy.reachability_keep,
            )
            for key in unused:
                emit(
                    "CPACS009",
                    f"Global type {key.name!r} is not reachable from "
                    f"the {policy.root_element!r} root element or configured "
                    "reachability roots.",
                    node=components[key],
                    default_severity="warning",
                )
        except SchemaToolError as exc:
            emit("CPACS009", str(exc), default_severity="error")

    xsd_prefix_uri = root.nsmap.get(policy.xsd_prefix)
    if xsd_prefix_uri != XSD_NS:
        emit(
            "CPACS010",
            f"The configured XSD prefix {policy.xsd_prefix!r} must resolve to "
            f"{XSD_NS!r}, found {xsd_prefix_uri!r}.",
            default_severity="error",
        )

    xlink_prefix_uri = root.nsmap.get(policy.xlink_prefix)
    if xlink_prefix_uri is not None and xlink_prefix_uri != XLINK_NS:
        emit(
            "CPACS011",
            f"The configured XLink prefix {policy.xlink_prefix!r} must resolve "
            f"to {XLINK_NS!r}, found {xlink_prefix_uri!r}.",
            default_severity="error",
        )

    return result


def rewrite_type_qname(
    lexical_value: str,
    context: etree._Element,
    schema_root: etree._Element,
    rename_map: Mapping[str, str],
) -> str:
    uri, local, prefix = resolve_lexical_qname(lexical_value, context)
    if uri == XSD_NS or not is_local_component_reference(uri, schema_root):
        return lexical_value
    replacement = rename_map.get(local)
    if replacement is None:
        return lexical_value
    return f"{prefix}:{replacement}" if prefix else replacement


def apply_type_renames(
    root: etree._Element,
    rename_map: Mapping[str, str],
) -> None:
    for child in root:
        if (
            namespace_uri(child) == XSD_NS
            and local_name(child) in {"complexType", "simpleType"}
        ):
            name = child.get("name")
            if name in rename_map:
                child.set("name", rename_map[name])

    for node in root.iter():
        for attribute_name in TYPE_REFERENCE_ATTRIBUTES:
            value = node.get(attribute_name)
            if value:
                node.set(
                    attribute_name,
                    rewrite_type_qname(value, node, root, rename_map),
                )

        member_types = node.get("memberTypes")
        if member_types:
            node.set(
                "memberTypes",
                " ".join(
                    rewrite_type_qname(value, node, root, rename_map)
                    for value in member_types.split()
                ),
            )


def rename_plan(
    root: etree._Element, policy: SchemaPolicy
) -> dict[str, str]:
    components = global_components(root)
    type_names = sorted(key.name for key in components if key.kind == "type")

    unknown_explicit_sources = sorted(
        set(policy.explicit_type_renames).difference(type_names)
    )
    if unknown_explicit_sources:
        raise SchemaToolError(
            "Configured [renames.types] source names are not global types: "
            + ", ".join(repr(name) for name in unknown_explicit_sources)
        )

    rename_map = {
        name: normalized_type_name(name, policy)
        for name in type_names
        if normalized_type_name(name, policy) != name
    }

    final_to_originals: dict[str, list[str]] = {}
    for name in type_names:
        final_name = rename_map.get(name, name)
        final_to_originals.setdefault(final_name, []).append(name)

    collisions = {
        final: originals
        for final, originals in final_to_originals.items()
        if len(originals) > 1
    }
    if collisions:
        details = "; ".join(
            f"{final!r} <- {', '.join(repr(name) for name in originals)}"
            for final, originals in sorted(collisions.items())
        )
        raise SchemaToolError(f"Cannot rename types due to collisions: {details}")

    return rename_map


def command_format(args: argparse.Namespace) -> int:
    input_path = Path(args.schema)
    tree = parse_schema(input_path)
    result = formatted_tree(tree, args.policy)
    text = serialize_schema(result, input_path, args.policy)
    output_schema_text(
        text,
        input_path=input_path,
        output=args.output,
        in_place=args.in_place,
        backup=args.backup,
        validate=not args.no_validate,
    )
    return 0


def command_check(args: argparse.Namespace) -> int:
    input_path = Path(args.schema)
    tree = parse_schema(input_path)
    result = formatted_tree(tree, args.policy)
    formatted = serialize_schema(result, input_path, args.policy)
    original = input_path.read_text(encoding="utf-8")

    if not args.no_validate:
        errors = validate_schema(tree)
        if errors:
            for item in errors:
                print(item, file=sys.stderr)
            return 2
        try:
            validate_generated_text(formatted, str(input_path))
        except SchemaToolError as exc:
            print(exc, file=sys.stderr)
            return 2

    if original == formatted:
        print("Schema formatting OK. The schema is in canonical form.")
        return 0

    print("Schema formatting differs from the canonical representation.", file=sys.stderr)
    print("Run the format command and review the changes.", file=sys.stderr)
    diff = difflib.unified_diff(
        original.splitlines(),
        formatted.splitlines(),
        fromfile=str(input_path),
        tofile=f"{input_path} (formatted)",
        lineterm="",
        n=3,
    )
    for line_number, line in enumerate(diff):
        if line_number >= args.diff_lines:
            print("... diff truncated ...", file=sys.stderr)
            break
        print(line, file=sys.stderr)
    return 1


def command_lint(args: argparse.Namespace) -> int:
    tree = parse_schema(Path(args.schema))
    diagnostics = lint_schema(
        tree, args.policy, include_unused=not args.no_unused
    )
    diagnostics.sort(
        key=lambda item: (
            0 if item.severity == "error" else 1,
            item.code,
            item.line or 0,
            item.message,
        )
    )

    for item in diagnostics:
        stream = sys.stderr if item.severity == "error" else sys.stdout
        print(item, file=stream)

    errors = sum(item.severity == "error" for item in diagnostics)
    warnings = sum(item.severity == "warning" for item in diagnostics)
    print(f"Lint result: {errors} error(s), {warnings} warning(s).")

    if errors:
        return 1
    if warnings and args.warnings_as_errors:
        return 1
    return 0


def command_rename_types(args: argparse.Namespace) -> int:
    input_path = Path(args.schema)
    tree = parse_schema(input_path)
    rename_map = rename_plan(tree.getroot(), args.policy)

    if not rename_map:
        print("All global type names already follow the CPACS convention.")
        return 0

    print("Proposed type renames:")
    for old, new in sorted(rename_map.items()):
        print(f"  {old} -> {new}")

    if not args.apply:
        print("Dry run only. Re-run with --apply to write the migration.")
        return 0

    apply_type_renames(tree.getroot(), rename_map)
    result = formatted_tree(tree, args.policy)
    text = serialize_schema(result, input_path, args.policy)
    output_schema_text(
        text,
        input_path=input_path,
        output=args.output,
        in_place=args.in_place,
        backup=args.backup,
        validate=not args.no_validate,
    )
    return 0


def command_prune_unused(args: argparse.Namespace) -> int:
    input_path = Path(args.schema)
    tree = parse_schema(input_path)
    root = tree.getroot()
    root_element = args.root_element or args.policy.root_element
    keep = tuple(args.policy.reachability_keep) + tuple(args.keep)
    unused, unresolved = unused_type_components(
        root,
        root_element=root_element,
        keep=keep,
    )

    if unresolved:
        print("Unresolved references prevent safe pruning:", file=sys.stderr)
        for key, node, attribute, lexical_value in unresolved[:50]:
            print(
                diagnostic(
                    "CPACS008",
                    "error",
                    f"Unresolved local {key.kind} reference {lexical_value!r} "
                    f"in @{attribute}.",
                    node,
                ),
                file=sys.stderr,
            )
        return 2

    if not unused:
        print("No unreachable global types found.")
        return 0

    print("Unreachable global types:")
    for key in unused:
        print(f"  {key.name}")

    if not args.apply:
        print("Dry run only. Re-run with --apply to remove these types.")
        return 0

    components = global_components(root)
    for key in unused:
        root.remove(components[key])

    result = formatted_tree(tree, args.policy)
    text = serialize_schema(result, input_path, args.policy)
    output_schema_text(
        text,
        input_path=input_path,
        output=args.output,
        in_place=args.in_place,
        backup=args.backup,
        validate=not args.no_validate,
    )
    return 0


def add_rules_argument(parser_: argparse.ArgumentParser) -> None:
    parser_.add_argument(
        "--rules",
        type=Path,
        default=DEFAULT_RULES_PATH,
        help=(
            "CPACS policy TOML file "
            f"(default: {DEFAULT_RULES_PATH})."
        ),
    )


def add_write_arguments(parser_: argparse.ArgumentParser) -> None:
    parser_.add_argument(
        "output",
        nargs="?",
        help="Output schema path. Without output or --in-place, write to stdout.",
    )
    parser_.add_argument(
        "--in-place",
        action="store_true",
        help="Replace the input schema atomically.",
    )
    parser_.add_argument(
        "--backup",
        action="store_true",
        help="Create <schema>.bak before an in-place replacement.",
    )
    parser_.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip XSD compilation of the generated output.",
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser_ = argparse.ArgumentParser(
        prog="schema_tool",
        description="Format, check, lint, and explicitly migrate the CPACS XSD schema.",
    )
    subparsers = parser_.add_subparsers(dest="command", required=True)

    format_parser = subparsers.add_parser(
        "format",
        help="Apply safe, deterministic formatting without renaming or pruning.",
    )
    format_parser.add_argument("schema", help="Input XSD file")
    add_rules_argument(format_parser)
    add_write_arguments(format_parser)
    format_parser.set_defaults(handler=command_format)

    check_parser = subparsers.add_parser(
        "check",
        help="Check whether the schema matches the canonical formatted form.",
    )
    check_parser.add_argument("schema", help="Input XSD file")
    add_rules_argument(check_parser)
    check_parser.add_argument(
        "--diff-lines",
        type=int,
        default=200,
        help="Maximum number of unified-diff lines to print (default: 200).",
    )
    check_parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip XSD compilation.",
    )
    check_parser.set_defaults(handler=command_check)

    lint_parser = subparsers.add_parser(
        "lint",
        help="Check CPACS conventions, references, reachability, and XSD validity.",
    )
    lint_parser.add_argument("schema", help="Input XSD file")
    add_rules_argument(lint_parser)
    lint_parser.add_argument(
        "--no-unused",
        action="store_true",
        help="Do not report types unreachable from the CPACS root element.",
    )
    lint_parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="Return a failing exit code when warnings are present.",
    )
    lint_parser.set_defaults(handler=command_lint)

    rename_parser = subparsers.add_parser(
        "rename-types",
        help="Explicitly normalize global type names and update type references.",
    )
    rename_parser.add_argument("schema", help="Input XSD file")
    add_rules_argument(rename_parser)
    rename_parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the migration. Without this flag, only print the plan.",
    )
    add_write_arguments(rename_parser)
    rename_parser.set_defaults(handler=command_rename_types)

    prune_parser = subparsers.add_parser(
        "prune-unused",
        help="Explicitly remove global types unreachable from a root element.",
    )
    prune_parser.add_argument("schema", help="Input XSD file")
    add_rules_argument(prune_parser)
    prune_parser.add_argument(
        "--root-element",
        default=None,
        help=(
            "Override the global root element used for reachability. "
            "The policy value is used by default."
        ),
    )
    prune_parser.add_argument(
        "--keep",
        action="append",
        default=[],
        metavar="NAME",
        help="Keep an additional public component by name; may be repeated.",
    )
    prune_parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the migration. Without this flag, only print the plan.",
    )
    add_write_arguments(prune_parser)
    prune_parser.set_defaults(handler=command_prune_unused)

    return parser_


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    try:
        args.policy = load_policy(Path(args.rules))
        return int(args.handler(args))
    except SchemaToolError as exc:
        print(f"schema_tool: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("schema_tool: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
