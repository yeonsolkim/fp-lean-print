# fp-lean-print

LuaLaTeX-based print/PDF tooling for
[_Functional Programming in Lean_](https://lean-lang.org/functional_programming_in_lean/).

The current track treats LaTeX as the main output path. The goal is a
book-like PDF with embedded fonts, searchable Lean text, stable code block
layout, a compact table of contents, and running page furniture inspired by the
_Mathematics in Lean_ PDF.

## Files

- `index.html`: generated source HTML used as the converter input.
- `tools/html_to_latex_prototype.py`: HTML-to-LaTeX book converter.
- `tools/validate_latex_pdf.py`: `pdffonts` and `pdftotext` validation helper.
- `latex-prototype/evaluating-expressions.tex`: smaller generated sample target.
- `latex-prototype/README.md`: notes for the LaTeX track.

## Requirements

- Python 3.
- LuaLaTeX and `latexmk`.
- Poppler tools: `pdffonts` and `pdftotext`.
- `npm` is optional, but the repository scripts use it as a convenient command
  runner.

## Build

Generate the whole-book LaTeX candidate from `index.html`:

```bash
npm run latex:book
```

This writes `latex-prototype/fp-lean.tex`.

Build the PDF:

```bash
npm run latex:build:book
```

Validate embedded fonts and text extraction:

```bash
npm run latex:validate:book
```

For faster iteration on a smaller sample:

```bash
npm run latex:prototype
npm run latex:build
npm run latex:validate
```

Generated PDFs and TeX auxiliary files are written under
`latex-prototype/build/`, which is ignored by Git. The build also keeps TeX
cache files under `tmp/texmf-var/` to avoid system cache permission issues.

## Quality Checks

After building, check that:

- no Type 3 fonts appear in `pdffonts`
- Lean code is searchable in `pdftotext`
- Lean symbols such as `←`, `→`, `:=`, and theorem-state markers extract cleanly
- code block indentation and table of contents spacing remain stable
