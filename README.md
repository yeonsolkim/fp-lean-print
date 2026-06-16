# fp-lean-print

Print-layout files for preparing a Letter-size, book-style PDF of
_Functional Programming in Lean_, tuned to feel closer to the _Mathematics in
Lean_ PDF layout.

This package intentionally stores the small, reusable layout layer rather
than the full generated HTML bundle. The full local bundle contains generated
search/assets files and the original working directory also includes large
temporary dependencies.

## Included

- `fp-lean-letter-book-html/book-print.css`: the print stylesheet with the
  latest design pass.
- `scripts/html_to_pdf.cjs`: helper script adjusted for Letter output and the
  Paged.js layout-ready flow.
- `patches/index-cache-version.patch`: tiny patch for the generated
  `index.html` cache-busting query strings.

## How to Apply

1. Generate or open the `fp-lean-letter-book-html` bundle.
2. Replace its `book-print.css` with
   `fp-lean-letter-book-html/book-print.css` from this package.
3. Apply `patches/index-cache-version.patch` to the generated `index.html`,
   or manually change the `book-print.css` and `book-setup.js` query strings
   to `letter16`.
4. Open `index.html`, click `조판 시작`, wait for `책 조판 준비 완료`, then
   print from Chrome.

Recommended print options:

- Destination: Save to PDF
- Pages: All
- Scale: 100
- Background graphics: On
- Headers and footers: Off
- Margins: None
