---
paths:
  - "schema/**"
  - "documentation/**"
  - "examples/**"
  - "development/developmentGuidelines.md"
---

# Improving the schema documentation

Rules for reworking the documentation of a type family in `schema/cpacs_schema.xsd` (e.g. `cst2DType`, `standardProfileType`, `guideCurveType`), including figures, equations, XML excerpts and generated examples.

The content rules are in `development/developmentGuidelines.md`, and they take precedence over this file: §8–§15 element documentation, §16–§20 code examples, §21–§25 figures and equations, §26–§28 TiGL notes. Read the relevant sections before writing. This file adds the workflow.

## 1. Understand before writing

- Collect the whole family: the type, its children, the collection type, the users (`grep 'type="<name>"'`) and the figures referenced in `documentation/media.json`.
- Check the existing text against the TiGL implementation in `../tigl/src` to reconstruct the semantics: coordinate definitions, defaults, index bases, point order, scaling, and what happens at the edges. Cite the source location (`file:line`) in your notes.
- Write findings and open questions to `../<typeName>_review/findings.md`, outside the repository. That file is also where TiGL features that are not implemented get recorded; they do not go into the XSD (§27).
- **Decisions that change the meaning of the standard belong to the user:** conventions, value ranges, defaults, or removing elements. Ask, recommend an option, and do not change schema constraints while the task is "only documentation".

## 2. Structure of a documentation page

- **`ddue:summary`:** one line saying what the node *is*, not "X type".
- **`ddue:remarks`**, in this order where applicable:
  1. an introductory paragraph: purpose and the concept in two or three sentences;
  2. topics under bold pseudo-headings (`<ddue:para><ddue:legacyBold>Coordinates</ddue:legacyBold></ddue:para>`), each with its definition; figure or equation right after the sentence it illustrates; after a figure, one paragraph that tells the reader what to see in it (refer to panels as "figure (a)");
  3. rules as a `ddue:list class="bullet"`;
  4. a `ddue:alert class="tigl"` directly after the statement it qualifies, only in the cases of §27;
  5. **Example**: an introductory paragraph stating what the excerpt shows, then the `ddue:code` block (§16–§19).
- **Element documentation:** a plain-text caption with the meaning, range and default. It contains no markup and no symbols like `e_x`.
- **Collection types** (e.g. `profilesType`, `guideCurveProfilesType`): content in one or two sentences and who references it. The generated "Used by" list already exists, so do not repeat it in full.
- **Writing:** in `ddue:para`, one sentence per line. Element names are `ddue:codeInline`. The text is tool-neutral and has no file paths or links to `examples/`; excerpts are self-contained, and the redundancy is accepted.
- **Consistency:** reuse the conventions already documented and say the same thing the same way. Point order and relative circumference are defined in `profileGeometryType` and `guideCurveType`; point indices start at 1. Cross-reference the defining type by name instead of repeating long definitions.
- **Components attached to others:** examples establish the practice that a component references the component it is attached to with `parentUID` (e.g. a wing its fuselage). Say so where the component is documented, and include the parent in the example file so that the reference resolves. Only the translation follows the parent (see `cpacsType`, checked in TiGL 3.5).
- **Compact datasets:** where examples write transformations out in full, say once that elements with default values (rotation and translation 0, scaling 1) may be omitted, but that a point that is given should list all its components.

## 3. Figures, equations, examples: one script per topic

- **One script per topic:** `documentation/scripts/<topic>.py`, with a PEP 723 header pinning `numpy` and `matplotlib`, run with `uv run documentation/scripts/<topic>.py` from the repository root.
- **What the script does:** writes the figures, the equations (`save_equation`) and the example file, and prints the documentation excerpts. Its docstring lists all outputs.
- **One set of data:** define the example data once as module constants and derive the figure, the example file and the excerpt from it, so the three cannot disagree. Illustrative geometry that differs from the example (e.g. an exaggerated thickness or vertical scale) is allowed but must be labelled as such in the figure or comment.
- **Style:** use `figure_style.py` (`figure_style()`, `COLORS`, `LINE`, `FONT_SIZE`, `FULL_WIDTH`, `save_figure`) and reuse existing helpers. Never introduce your own colors or line widths.
- **Example files:** write them with `example_xml.write_cpacs_file(..., generator=Path(__file__))`; further collections go through `extra_components` and `extra_profiles`. Generated files are never edited by hand.
- **Illustrative data:** geometry that only illustrates a concept, e.g. a case TiGL cannot load (a split wingtip) or exaggerated transformation values, is kept as separate module constants, is not written to the example file, and is called an illustration in the text below the figure. Prefer one concrete, recognizable case (a split wingtip) over an abstract one (a step between two elements).
- **Replaced figures:**
  - before removing an old figure, list what it shows and check that the new figures cover each aspect; otherwise the information is lost silently (e.g. `wingelements.jpg` was the only figure showing an element coordinate system translated and rotated within its section);
  - add every new image to `documentation/media.json` in alphabetical order, without reordering existing entries, with a descriptive `alt` text (equations get the formula in plain text);
  - `git rm` replaced images and remove their entries;
  - `grep` for remaining references first.
- **Oblique 3D views:** pick the projection so that the planes and angles the figure explains do not overlap in the image and no axis runs along a data vector; shade each angle as a pale area in its own plane. With an exaggerated vertical scale, draw coordinate axes perpendicular in the image and state the ratio in the figure (§24). Show the state before a transformation as a pale solid contour in `series1Light`, never dashed (§23).
- **Look at every figure** (§24): composite it on both plates `#fefdfb` and `#edeff1` (e.g. with Pillow) and view the result. Iterate until no label touches a curve, another label or the frame, no helper line runs close and parallel to a data line, and the construction is readable at 760 px. Anchor labels of repeated features to the same reference (e.g. the upper edge of an area) so that their distances match.
- **Rerun all scripts** after changing a shared helper. `git status` must show no diff for figures or examples you did not intend to change, which proves reproducibility.

## 4. Verify semantics with TiGL

Whenever the text states geometry, check it with a generated example in TiGL before handing over:

```
pixi exec -c dlr-sc -c conda-forge -s tigl3 -s tixi3 -s numpy -s python=3.11 -- python <script>.py <file>.xml
```

Notes for these scripts:
- Put the scripts in the scratchpad, not in the repository.
- For object access, use `CCPACSConfigurationManager_get_instance().get_configuration(tigl._handle.value)`.
- Use stdlib `xml.etree` inside `pixi exec`, because lxml conflicts there.
- A file with several models is opened per model uID.
- Not everything is wrapped in Python (e.g. fuselage segments have no `get_guide_curves`); look for an alternative accessor on the parent (`dir(obj)`), e.g. `fuselage.get_guide_curve_segment(uid)`.
- Compare numbers (points, tangents, volumes) against the formula in the documentation. Report mismatches as TiGL findings; only inconsistencies of the kind in §27 become TiGL notes, stating the TiGL version.

## 5. Validation before handover

Run from the `cpacs` repository root:

1. `pixi run format-schema`, after every edit of ddue markup. Watch the formatter pitfall in §25: never place an inline element directly before another inline element or at the end of its parent.
2. `pixi run check`: format check, lint and example validation must pass, including the new example.
3. `uv run --project ../cpacs-doc cpacs-doc report schema/cpacs_schema.xsd`: 0 errors, and no new warnings compared to before.
4. Compare every excerpt in the XSD with the script output (dedented CDATA content identical). Excerpts without `...` are additionally validated against the schema inside a minimal CPACS document.
5. Render the pages and look at them: `cpacs-doc build schema/cpacs_schema.xsd --site -o <scratchpad>/doc`, or the user's running `cpacs-doc serve` (port 8000). Take screenshots with headless Chrome via `../cpacs-doc/tests/cdp.py`, using `captureBeyondViewport` and a scroll offset.

## 6. Tooling pitfalls

- **Line endings:** the schema is stored with LF. When rewriting files with Python, use `write_text(..., newline="\n")` and check with `git diff --stat` that the diff is not the whole file.
- **Multi-line text replacements in the XSD:** put them in a Python script file in the scratchpad and assert that each old string occurs exactly once. Create the script with the file-writing tool, not with a heredoc: in heredocs, quotes and escapes such as `\n` break or turn into real line breaks. A failed patch leaves the file unchanged, so check the exit code before judging the result of a following run.
- **Indentation of generated markup:** `pixi run format-schema` indents elements but not text. Write the lines of a multi-line `ddue:para`, its closing tag, the closing `</ddue:code>` and the `<![CDATA[`/`]]>` markers with the indentation of the schema yourself; only the code inside CDATA starts at column 0 (§17). Check that no line of the edited types outside CDATA starts at column 0.
- **PowerShell:** `pixi` writes progress to stderr, which PowerShell reports as an error. Judge success by the output, not by the exit record alone.

## 7. Handover to the user

- Answer in the user's language (German so far). XSD text, scripts and comments are English.
- Report briefly:
  - what changed, per type;
  - what was verified, with the key numbers;
  - open decisions, with a recommendation;
  - new untracked files that need `git add`;
  - a commit one-liner.
- The user commits and pushes. Do not commit.
