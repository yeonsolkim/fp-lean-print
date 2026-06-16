# fp-lean-print

Print-layout support files for producing a Letter-size, book-style PDF of
_Functional Programming in Lean_, tuned to resemble the visual rhythm of the
_Mathematics in Lean_ PDF.

This repository is a small reusable layout layer. It does not include the
original book content. Use it when you already have a generated
`fp-lean-letter-book-html` bundle and want a cleaner print/PDF pass.

## What This Does

- Replaces the generated bundle's `book-print.css` with a Letter-oriented print stylesheet.
- Keeps the page layout close to _Mathematics in Lean_: 1 inch side margins,
  book-like cover spacing, running headers/footers, roomier chapter openers,
  and tighter code blocks.
- Provides an optional Node/Playwright helper for producing a PDF from the
  generated `index.html`.

## Files

- `book-print.css`: print stylesheet to copy into the generated HTML bundle.
- `html_to_pdf.cjs`: optional PDF helper script.
- `index-cache-version.patch`: tiny patch for the generated `index.html`
  cache-busting query strings.
- `package.json`: Node package metadata and Playwright dependency.

## Requirements

- A generated `fp-lean-letter-book-html` bundle for _Functional Programming in Lean_.
- Node.js 18 or newer.
- Playwright, installed with `npm install`.
- Chrome or the Playwright Chromium browser.

Tested during the layout pass on macOS with Chrome-style PDF output. The
stylesheet is intentionally Letter-size only.

## Quick Start

```bash
git clone https://github.com/yeonsolkim/fp-lean-print.git
cd fp-lean-print
npm install

# Copy the stylesheet into your generated bundle.
cp book-print.css /path/to/fp-lean-letter-book-html/book-print.css

# Apply the small cache-busting patch, or make the same two edits manually.
cd /path/to/fp-lean-letter-book-html
patch index.html /path/to/fp-lean-print/index-cache-version.patch

# Generate a PDF with the helper.
cd /path/to/fp-lean-print
npm run pdf -- /path/to/fp-lean-letter-book-html/index.html fp-lean.pdf
```

The expected output is a Letter-size PDF named `fp-lean.pdf`.

## Manual Chrome Print

If you prefer to print manually:

1. Copy `book-print.css` into the generated bundle.
2. Apply `index-cache-version.patch`, or manually change the `book-print.css`
   and `book-setup.js` query strings in `index.html` to `letter16`.
3. Open the generated `index.html`.
4. Click `조판 시작`.
5. Wait for `책 조판 준비 완료`.
6. Print from Chrome.

Recommended print options:

- Destination: Save to PDF
- Pages: All
- Scale: 100
- Background graphics: On
- Headers and footers: Off
- Margins: None

## Known Limitations

- Letter-size output only.
- Optimized for Chrome/Chromium PDF rendering.
- The original _Functional Programming in Lean_ book content is not included.
- `index-cache-version.patch` is only needed to make browsers pick up the new
  `book-print.css`/`book-setup.js` versions when working with a generated bundle.
- The helper script waits for the Korean Paged.js status button text used in
  the current generated bundle.

## Suggested GitHub Metadata

Description:

> Letter-size print layout support for Functional Programming in Lean.

Website:

> https://github.com/yeonsolkim/fp-lean-print

Topics:

`lean`, `lean4`, `functional-programming`, `print-css`, `pagedjs`, `pdf`,
`book-design`, `typography`

## License

The CSS, script, patch, and documentation files in this repository are licensed
under the MIT License. This license applies only to this repository's layout
support files and does not grant rights to the original book content.
