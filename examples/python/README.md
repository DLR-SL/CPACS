# Python examples

Scripts showing how to work with CPACS datasets from Python. They use the XML examples of the
parent folder and are run from this folder:

```cmd
cd examples/python
python toolspecific_lxml.py
```

| Script | Shows | Requires |
| ---------- | ---------- | ---------- |
| `toolspecific_lxml.py` | Reading, writing and validating tool-specific data | `lxml` |
| `toolspecific_tixi.py` | The same with TiXI | `tixi3` |

The scripts are divided into cells by `# %%` comment lines, so that editors such as VS Code or
Jupyter can also run them step by step. Files the scripts write stay in this folder and are
ignored by git.

The rules the data follows are documented in the CPACS schema; for tool-specific data, see
`toolspecificType`. All scripts are run by `scripts/tests/test_examples.py`, e.g. via
`pixi run test-examples`, whose environment provides both libraries.
