from __future__ import annotations

from pathlib import Path

import pytest
from tixi3 import tixi3wrapper


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "schema" / "cpacs_schema.xsd"

EXCLUDED_EXAMPLES = {
    "toolspecific.xml",
    "leading-edge-devices.xml",
}

EXAMPLE_FILES = [
    path
    for path in sorted((ROOT / "examples").glob("*.xml"))
    if path.name not in EXCLUDED_EXAMPLES
]


@pytest.mark.parametrize(
    "xml_file",
    EXAMPLE_FILES,
    ids=lambda path: path.name,
)
def test_example_file_validates(xml_file: Path) -> None:
    tixi = tixi3wrapper.Tixi3()
    opened = False

    try:
        tixi.open(str(xml_file))
        opened = True

        validation_code = tixi.schemaValidateFromFile(str(SCHEMA))

        assert not validation_code, (
            f'Example "{xml_file.relative_to(ROOT)}" does not validate '
            f'against "{SCHEMA.relative_to(ROOT)}". '
            f"TIXI returned {validation_code!r}."
        )
    finally:
        if opened:
            tixi.close()