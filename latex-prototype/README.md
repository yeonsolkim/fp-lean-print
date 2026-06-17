# LaTeX Track

This directory contains the LuaLaTeX output track. It is the main path for
improving PDF quality.

The goal is to produce a more book-like PDF with stable embedded fonts,
searchable text, cleaner math/font handling, and more coherent Lean code
blocks.

## Generate

From the repository root:

```bash
npm run latex:book
```

This reads `index.html` and writes:

```text
latex-prototype/fp-lean.tex
```

For quick iteration on a five-page sample:

```bash
npm run latex:prototype
```

which writes:

```text
latex-prototype/evaluating-expressions.tex
```

The sample target is the `1.1 Evaluating Expressions` section, because it has
paragraphs, inline Lean, input blocks, output blocks, and error blocks.

## Build

```bash
npm run latex:build:book
```

For the sample target:

```bash
npm run latex:build
```

The build uses LuaLaTeX and writes output under:

```text
latex-prototype/build/
```

The script also keeps TeX/font cache data under `tmp/texmf-var/` so local
permission differences do not affect the first experiment.

## Quality Checks

After building, check the generated PDF:

```bash
npm run latex:validate:book
```

The validation script runs `pdffonts` and `pdftotext`. Look for:

- no Type 3 fonts
- Lean code extracting as text
- Lean symbols such as `←`, `→`, and `:=` surviving copy/search
- code block indentation preserved
- TOC leaders and running footers matching the book direction

## Design Baseline

The prototype uses:

- FreeSerif for body text, falling back to STIX Two Text and Libertinus Serif
- STIX Two Math for math
- FreeSans for headings, falling back to TeX Gyre Heros
- FreeMono for code, falling back to JuliaMono, Iosevka, DejaVu Sans Mono, Noto Sans Mono, then Menlo
- MIL-inspired chapter openers with black rules, compact right-aligned labels, and smaller uppercase titles
- a custom MIL-like table of contents: black sans title, blue sans entries, dark leader dots, bold black page numbers, and TOC-only page furniture
- LaTeX-rendered tables for the structured Lean reference summaries
- a shallow table of contents: chapter and first-level section entries only
- empty blank verso pages in the two-sided print layout
- Pygments-like Lean token coloring for input blocks, with output/error/warning blocks using the same grey-box language and no left border
- adjacent Lean input fragments merged into a single code box where the HTML source emits consecutive one-line blocks
- unnumbered Introduction and Interlude subsections, with release history, author information, and license moved to the back matter
- acknowledgments placed before the table of contents without appearing as a TOC entry

These are intentionally explicit so PDF font embedding can be audited.
