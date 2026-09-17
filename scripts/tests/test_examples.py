from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest
from lxml import etree
from tixi3 import tixi3wrapper


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples"
SCHEMA = ROOT / "schema" / "cpacs_schema.xsd"

TOOLSPECIFIC_EXAMPLE = EXAMPLES / "toolspecific.xml"
TOOLSPECIFIC_SCHEMA = ROOT / "schema" / "toolspecific_template.xsd"
TOOLSPECIFIC_COMBINED_SCHEMA = EXAMPLES / "toolspecific_combined.xsd"
PYTHON_EXAMPLES = EXAMPLES / "python"
TOOLSPECIFIC_SCRIPTS = ["toolspecific_tixi.py", "toolspecific_lxml.py"]

EXCLUDED_EXAMPLES = {
    # Validated together with its tool schema, see the tests below.
    TOOLSPECIFIC_EXAMPLE.name,
}

EXAMPLE_FILES = [
    path
    for path in sorted(EXAMPLES.glob("*.xml"))
    if path.name not in EXCLUDED_EXAMPLES
]

DDUE = "http://ddue.schemas.microsoft.com/authoring/2003/5"
XSD = "http://www.w3.org/2001/XMLSchema"


def validate(xml_file: Path, schema: Path) -> None:
    """Validate with TIXI; raises Tixi3Exception if the file does not comply."""
    tixi = tixi3wrapper.Tixi3()
    opened = False

    try:
        tixi.open(str(xml_file))
        opened = True

        validation_code = tixi.schemaValidateFromFile(str(schema))

        assert not validation_code, (
            f'Example "{xml_file.relative_to(ROOT)}" does not validate '
            f'against "{schema}". '
            f"TIXI returned {validation_code!r}."
        )
    finally:
        if opened:
            tixi.close()


@pytest.mark.parametrize(
    "xml_file",
    EXAMPLE_FILES,
    ids=lambda path: path.name,
)
def test_example_file_validates(xml_file: Path) -> None:
    validate(xml_file, SCHEMA)


def test_toolspecific_example_validates_with_its_tool_schema() -> None:
    validate(TOOLSPECIFIC_EXAMPLE, TOOLSPECIFIC_COMBINED_SCHEMA)


def test_toolspecific_example_requires_its_tool_schema() -> None:
    """The tool data is validated strictly, so the CPACS schema alone rejects it.

    The documentation of `toolspecificType` states this behaviour. Should the
    wildcard in `toolType` change, update that documentation with this test.
    """
    with pytest.raises(tixi3wrapper.Tixi3Exception):
        validate(TOOLSPECIFIC_EXAMPLE, SCHEMA)


@pytest.fixture
def repository_copy(tmp_path: Path) -> Path:
    """The files the toolspecific scripts use, in the layout of the repository.

    The scripts run in examples/python and write their result there, so they
    are run on a copy.
    """
    scripts = tmp_path / "examples" / "python"
    scripts.mkdir(parents=True)
    (tmp_path / "schema").mkdir()
    for path in [TOOLSPECIFIC_EXAMPLE, EXAMPLES / "basicWing.xml", TOOLSPECIFIC_COMBINED_SCHEMA]:
        shutil.copy(path, tmp_path / "examples" / path.name)
    for name in TOOLSPECIFIC_SCRIPTS:
        shutil.copy(PYTHON_EXAMPLES / name, scripts / name)
    for path in [SCHEMA, TOOLSPECIFIC_SCHEMA]:
        shutil.copy(path, tmp_path / "schema" / path.name)
    return scripts


@pytest.mark.parametrize("script", TOOLSPECIFIC_SCRIPTS)
def test_toolspecific_script_writes_valid_tool_data(script: str, repository_copy: Path) -> None:
    result = subprocess.run(
        [sys.executable, script], cwd=repository_copy, capture_output=True, text=True
    )
    assert result.returncode == 0, f"{script} failed:\n{result.stderr}"
    validate(repository_copy / "basicWing_with_tool_data.xml", repository_copy.parent / TOOLSPECIFIC_COMBINED_SCHEMA.name)


def documented_code_block(title: str) -> str:
    """The code of a block in the toolspecificType documentation, as the generator shows it."""
    schema = etree.parse(str(SCHEMA), etree.XMLParser(strip_cdata=False)).getroot()
    tool_type = schema.find(f"{{{XSD}}}complexType[@name='toolspecificType']")
    for code in tool_type.iter(f"{{{DDUE}}}code"):
        if code.get("title") == title:
            return dedent(code.text).strip("\n")
    raise AssertionError(f"toolspecificType has no code block titled {title!r}")


def test_toolspecific_documentation_shows_the_combined_schema() -> None:
    documented = documented_code_block("Schema combining the CPACS schema and a tool schema")
    assert documented == TOOLSPECIFIC_COMBINED_SCHEMA.read_text(encoding="utf-8").strip("\n")


def test_toolspecific_documentation_shows_the_example_file() -> None:
    """Compared without the whitespace between tags, since the file is indented differently."""
    compact = lambda xml: re.sub(r">\s+<", "><", xml.strip())
    documented = documented_code_block("Data of a single tool")
    in_file = re.search(r"<toolspecific>.*</toolspecific>", TOOLSPECIFIC_EXAMPLE.read_text(encoding="utf-8"), re.S)
    assert compact(documented) == compact(in_file.group())
