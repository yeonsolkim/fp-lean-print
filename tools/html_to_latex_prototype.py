#!/usr/bin/env python3
"""Build LuaLaTeX output from the generated Verso HTML."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path


VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
SKIP_CLASSES = {
    "hover-container",
    "hover-info",
    "permalink-widget",
    "toc-backdrop",
    "tactic-state",
    "tactic-toggle",
}
SKIP_TAGS = {"script", "style", "template", "header", "nav"}


@dataclass
class Node:
    tag: str | None = None
    attrs: dict[str, str] = field(default_factory=dict)
    children: list["Node"] = field(default_factory=list)
    text: str = ""
    parent: "Node | None" = None

    @property
    def classes(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())


class TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node(tag="document")
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(tag=tag.lower(), attrs={k: v or "" for k, v in attrs}, parent=self.stack[-1])
        self.stack[-1].children.append(node)
        if node.tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        while len(self.stack) > 1:
            node = self.stack.pop()
            if node.tag == tag:
                return

    def handle_data(self, data: str) -> None:
        if data:
            self.stack[-1].children.append(Node(text=data, parent=self.stack[-1]))


def parse_html(path: Path) -> Node:
    parser = TreeBuilder()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.root


def has_class(node: Node, name: str) -> bool:
    return name in node.classes


def should_skip(node: Node) -> bool:
    if node.tag in SKIP_TAGS:
        return True
    return bool(node.classes & SKIP_CLASSES)


def walk(node: Node):
    yield node
    for child in node.children:
        yield from walk(child)


def text_content(node: Node, preserve: bool = False) -> str:
    if should_skip(node):
        return ""
    if node.tag is None:
        return node.text
    if node.tag == "br":
        return "\n"
    if preserve:
        if has_class(node, "colon"):
            return " : "
        if has_class(node, "hypothesis"):
            return "".join(text_content(child, preserve=True) for child in node.children).strip() + "\n"
        if has_class(node, "conclusion"):
            return "".join(text_content(child, preserve=True) for child in node.children).strip() + "\n"
        if has_class(node, "goal"):
            goal = "".join(text_content(child, preserve=True) for child in node.children).strip("\n")
            return f"\n{goal}\n" if goal else ""
    text = "".join(text_content(child, preserve=preserve) for child in node.children)
    return text if preserve else re.sub(r"\s+", " ", text)


def find_by_id(root: Node, element_id: str) -> Node | None:
    for node in walk(root):
        if node.attrs.get("id") == element_id:
            return node
    return None


def nearest_section(node: Node) -> Node:
    cur = node
    while cur.parent is not None and cur.tag != "section":
        cur = cur.parent
    return cur


def root_content_section(root: Node) -> Node:
    for node in walk(root):
        if node.tag == "main":
            content = next((child for child in node.children if has_class(child, "content-wrapper")), None)
            section = next((child for child in content.children if child.tag == "section"), None) if content else None
            if section:
                return section
    raise SystemExit("could not find main content section")


def top_sections(root: Node) -> list[Node]:
    return [child for child in root_content_section(root).children if child.tag == "section"]


def first_child_heading(section: Node) -> Node | None:
    return next((child for child in section.children if child.tag in {"h2", "h3"}), None)


def top_section_title(section: Node) -> str:
    heading = first_child_heading(section)
    return text_content(heading).strip() if heading else ""


def strip_number(title: str) -> str:
    return re.sub(r"^\s*\d+(?:\.\d+)*\.\s*", "", title.replace("\xa0", " ")).strip()


def is_numbered_title(title: str) -> bool:
    return bool(re.match(r"^\s*\d+(?:\.\d+)*\.\s+", title.replace("\xa0", " ")))


LATEX_SPECIALS = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "&": r"\&",
    "%": r"\%",
    "#": r"\#",
    "_": r"\_",
    "^": r"\textasciicircum{}",
    "~": r"\textasciitilde{}",
    "✝": r"\textdagger{}",
    "₀": r"\textsubscript{0}",
    "₁": r"\textsubscript{1}",
    "₂": r"\textsubscript{2}",
    "₃": r"\textsubscript{3}",
    "₄": r"\textsubscript{4}",
    "₅": r"\textsubscript{5}",
    "₆": r"\textsubscript{6}",
    "₇": r"\textsubscript{7}",
    "₈": r"\textsubscript{8}",
    "₉": r"\textsubscript{9}",
    "ₙ": r"\textsubscript{n}",
}


def latex_escape(text: str) -> str:
    return "".join(LATEX_SPECIALS.get(ch, ch) for ch in text)


def verbatim_command_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "$": r"\$",
        "&": r"\&",
        "%": r"\%",
        "#": r"\#",
        "_": r"\_",
        "^": r"\textasciicircum{}",
        "~": r"\textasciitilde{}",
        "✝": r"\textdagger{}",
        "₀": r"\textsubscript{0}",
        "₁": r"\textsubscript{1}",
        "₂": r"\textsubscript{2}",
        "₃": r"\textsubscript{3}",
        "₄": r"\textsubscript{4}",
        "₅": r"\textsubscript{5}",
        "₆": r"\textsubscript{6}",
        "₇": r"\textsubscript{7}",
        "₈": r"\textsubscript{8}",
        "₉": r"\textsubscript{9}",
        "ₙ": r"\textsubscript{n}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def inline_code(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    return r"\icode{" + latex_escape(text) + "}"


def is_inline_code_node(node: Node) -> bool:
    return node.tag == "code" and not has_class(node, "block")


def rendered_text(node: Node) -> str:
    return text_content(node, preserve=True)


def should_insert_inline_gap(left: Node, right: Node) -> bool:
    left_text = rendered_text(left)
    right_text = rendered_text(right)
    if not left_text or not right_text:
        return False
    if left_text[-1].isspace() or right_text[0].isspace():
        return False
    if right_text[0] in ",.;:!?)]}":
        return False
    if not (is_inline_code_node(left) or is_inline_code_node(right)):
        return False
    return bool(re.search(r"[\w)\]\"'`}]$", left_text, re.UNICODE)) and bool(re.search(r"^[\w(\"'`{#]", right_text, re.UNICODE))


def render_inline(node: Node) -> str:
    if should_skip(node):
        return ""
    if node.tag is None:
        return latex_escape(re.sub(r"\s+", " ", node.text))
    if node.tag == "br":
        return r"\\"
    if node.tag == "code" and has_class(node, "inline"):
        return inline_code(text_content(node, preserve=True))
    if node.tag == "code" and not has_class(node, "block"):
        return inline_code(text_content(node, preserve=True))
    if node.tag == "em":
        return r"\emph{" + render_children_inline(node).strip() + "}"
    if node.tag == "strong":
        return r"\textbf{" + render_children_inline(node).strip() + "}"
    return render_children_inline(node)


def render_children_inline(node: Node) -> str:
    parts: list[str] = []
    previous: Node | None = None
    for child in node.children:
        rendered_child = render_inline(child)
        if not rendered_child:
            continue
        if previous and should_insert_inline_gap(previous, child):
            parts.append(" ")
        parts.append(rendered_child)
        previous = child
    rendered = "".join(parts)
    rendered = re.sub(r" {2,}", " ", rendered)
    return rendered


def env_block(name: str, content: str) -> str:
    content = content.strip("\n")
    if not content:
        return ""
    return f"\\begin{{{name}}}\n{content}\n\\end{{{name}}}\n"


def env_content(block: str, name: str) -> str | None:
    begin = f"\\begin{{{name}}}\n"
    end = f"\n\\end{{{name}}}\n"
    if block.startswith(begin) and block.endswith(end):
        return block[len(begin) : -len(end)]
    return None


def merge_adjacent_leaninput_blocks(blocks: list[str]) -> list[str]:
    merged: list[str] = []
    pending: list[str] = []

    def flush_pending() -> None:
        if pending:
            merged.append(env_block("leaninput", "\n\n".join(pending)))
            pending.clear()

    for block in blocks:
        content = env_content(block, "leaninput")
        if content is not None:
            pending.append(content.strip("\n"))
            continue
        flush_pending()
        merged.append(block)
    flush_pending()
    return merged


LEAN_KEYWORDS = {
    "#check",
    "#eval",
    "abbrev",
    "by",
    "class",
    "def",
    "deriving",
    "do",
    "else",
    "example",
    "fun",
    "have",
    "if",
    "inductive",
    "instance",
    "let",
    "match",
    "namespace",
    "open",
    "partial",
    "show",
    "structure",
    "then",
    "theorem",
    "where",
    "with",
}


def code_macro(node: Node) -> str | None:
    classes = node.classes
    raw_text = text_content(node, preserve=True).strip()
    can_promote = node.tag == "span" and "token" in classes
    if can_promote and raw_text == "sorry":
        return "leanSorry"
    if can_promote and raw_text in LEAN_KEYWORDS:
        return "leanKeyword"
    if "keyword" in classes:
        return "leanKeyword"
    if "string" in classes:
        return "leanString"
    if "comment" in classes:
        return "leanComment"
    if "sort" in classes:
        return "leanSort"
    if "const" in classes:
        return "leanConst"
    if "typed" in classes:
        return "leanNumber"
    return None


def code_latex(node: Node) -> str:
    if should_skip(node):
        return ""
    if node.tag is None:
        return verbatim_command_escape(node.text)
    if node.tag == "br":
        return "\n"
    if has_class(node, "colon"):
        return " : "
    if has_class(node, "hypothesis"):
        return "".join(code_latex(child) for child in node.children).strip() + "\n"
    if has_class(node, "conclusion"):
        return "".join(code_latex(child) for child in node.children).strip() + "\n"
    if has_class(node, "goal"):
        goal = "".join(code_latex(child) for child in node.children).strip("\n")
        return f"\n{goal}\n" if goal else ""

    rendered = "".join(code_latex(child) for child in node.children)
    macro = code_macro(node)
    if macro and rendered and "\n" not in rendered and not rendered.startswith(r"\lean"):
        return rf"\{macro}{{{rendered}}}"
    return rendered


def code_text(node: Node) -> str:
    text = text_content(node, preserve=True)
    text = text.replace("✝", "†")
    text = re.sub(r"\n[ \t]*\n", "\n", text)
    return text.strip("\n")


def code_block_text(node: Node, highlighted: bool = False) -> str:
    if highlighted:
        text = code_latex(node)
    else:
        text = code_text(node)
    text = re.sub(r"\n[ \t]*\n", "\n", text)
    return text.strip("\n")


def render_eval_steps(node: Node) -> list[str]:
    snippets: list[str] = []
    for child in node.children:
        if child.tag == "code" and has_class(child, "block"):
            snippets.append(code_block_text(child, highlighted=True))
        elif child.tag == "pre" and "lean-output" in child.classes:
            snippets.append(verbatim_command_escape(code_text(child)))
    if not snippets:
        return render_blocks(node.children)
    joined = "\n  ==> \n".join(s for s in snippets if s)
    return [env_block("leaninput", joined)]


BACKMATTER_SECTION_TITLES = {"Release history", "About the Author", "License"}


def render_heading(node: Node, unnumbered: bool = False) -> str:
    title = strip_number(text_content(node).strip())
    level = {"h2": "chapter", "h3": "section", "h4": "subsection", "h5": "subsubsection"}.get(node.tag, "paragraph")
    if unnumbered or is_release_history_heading(node):
        return f"\\{level}*{{{latex_escape(title)}}}\n"
    return f"\\{level}{{{latex_escape(title)}}}\n"


def is_release_history_heading(node: Node) -> bool:
    title = strip_number(text_content(node).strip())
    if title == "Release history":
        return True
    cur = node.parent
    while cur is not None:
        if cur.tag == "section":
            heading = first_child_heading(cur)
            if heading and strip_number(text_content(heading).strip()) == "Release history":
                return True
        cur = cur.parent
    return False


def render_list(node: Node, ordered: bool, unnumbered_headings: bool = False) -> str:
    env = "enumerate" if ordered else "itemize"
    items = []
    for child in node.children:
        if child.tag == "li":
            body = "\n".join(render_blocks(child.children, unnumbered_headings=unnumbered_headings)).strip()
            items.append("\\item " + body)
    return f"\\begin{{{env}}}\n" + "\n".join(items) + f"\n\\end{{{env}}}\n"


def table_cells(row: Node) -> list[Node]:
    return [child for child in row.children if child.tag in {"th", "td"}]


def table_rows(node: Node) -> list[Node]:
    return [child for child in walk(node) if child.tag == "tr"]


def render_table_cell(cell: Node) -> str:
    paragraphs: list[str] = []
    for child in cell.children:
        if child.tag == "p":
            rendered = render_children_inline(child).strip()
            if rendered:
                paragraphs.append(rendered)
    if not paragraphs:
        rendered = render_children_inline(cell).strip()
        if rendered:
            paragraphs.append(rendered)
    return r"\par ".join(paragraphs).replace("\n", " ")


def render_table(node: Node) -> str:
    rows = table_rows(node)
    if not rows:
        return ""

    column_count = max((len(table_cells(row)) for row in rows), default=0)
    if column_count == 0:
        return ""

    header_rows = [row for row in rows if any(cell.tag == "th" for cell in table_cells(row))]
    body_rows = [row for row in rows if row not in header_rows]
    column_spec = "@{}" + "".join([r">{\raggedright\arraybackslash}X" for _ in range(column_count)]) + "@{}"

    def render_row(row: Node, header: bool = False) -> str:
        cells = table_cells(row)
        rendered = [render_table_cell(cell) for cell in cells]
        rendered.extend([""] * (column_count - len(rendered)))
        if header:
            rendered = [r"\textbf{" + cell + "}" if cell else "" for cell in rendered]
        return " & ".join(rendered) + r" \\"

    lines = [
        r"\begin{tableblock}",
        rf"\begin{{tabularx}}{{\textwidth}}{{{column_spec}}}",
        r"\toprule",
    ]
    if header_rows:
        lines.extend(render_row(row, header=True) for row in header_rows)
        lines.append(r"\midrule")
    lines.extend(render_row(row) for row in body_rows)
    lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{tableblock}"])
    return "\n".join(lines) + "\n"


def render_block(node: Node, unnumbered_headings: bool = False) -> list[str]:
    if should_skip(node) or node.tag is None:
        return []
    if node.tag in {"h2", "h3", "h4", "h5"}:
        return [render_heading(node, unnumbered=unnumbered_headings)]
    if node.tag == "p":
        text = render_children_inline(node).strip()
        return [text + "\n"] if text else []
    if node.tag == "code" and has_class(node, "block"):
        return [env_block("leaninput", code_block_text(node, highlighted=True))]
    if node.tag == "pre":
        classes = node.classes
        if "error" in classes:
            return [env_block("leanerror", code_text(node))]
        if "warning" in classes:
            return [env_block("leanwarning", code_text(node))]
        if "lean-output" in classes:
            return [env_block("leanoutput", code_text(node))]
        return [env_block("leaninput", code_text(node))]
    if node.tag == "div" and has_class(node, "eval-steps"):
        return render_eval_steps(node)
    if node.tag == "ul":
        return [render_list(node, ordered=False, unnumbered_headings=unnumbered_headings)]
    if node.tag == "ol":
        return [render_list(node, ordered=True, unnumbered_headings=unnumbered_headings)]
    if node.tag == "table":
        rendered = render_table(node)
        return [rendered] if rendered else []
    if node.tag == "section":
        return render_blocks(node.children, unnumbered_headings=unnumbered_headings)
    if node.tag in {"div", "blockquote", "dl"}:
        return render_blocks(node.children, unnumbered_headings=unnumbered_headings)
    return render_blocks(node.children, unnumbered_headings=unnumbered_headings)


def render_blocks(nodes: list[Node], unnumbered_headings: bool = False) -> list[str]:
    blocks: list[str] = []
    for node in nodes:
        blocks.extend(render_block(node, unnumbered_headings=unnumbered_headings))
    return merge_adjacent_leaninput_blocks(blocks)


PREAMBLE = r"""\documentclass[10pt,letterpaper,twoside,openright]{book}
\usepackage[margin=1in,headheight=14pt,headsep=18pt,footskip=0.38in]{geometry}
\usepackage{fontspec}
\usepackage{unicode-math}
\usepackage[protrusion=true,expansion=true]{microtype}
\usepackage{xcolor}
\usepackage{needspace}
\usepackage{fvextra}
\usepackage[most]{tcolorbox}
\usepackage{array}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{titlesec}
\usepackage{titletoc}
\usepackage{fancyhdr}
\usepackage{enumitem}
\usepackage[hypertexnames=false]{hyperref}
\usepackage{bookmark}

\IfFontExistsTF{FreeSerif}{\setmainfont{FreeSerif}}{\IfFontExistsTF{STIX Two Text}{\setmainfont{STIX Two Text}}{\setmainfont{Libertinus Serif}}}
\IfFontExistsTF{STIX Two Math}{\setmathfont{STIX Two Math}}{\setmathfont{Libertinus Math}}
\IfFontExistsTF{FreeSans}{\setsansfont{FreeSans}}{\IfFontExistsTF{TeX Gyre Heros}{\setsansfont{TeX Gyre Heros}}{\setsansfont{Helvetica Neue}}}
\directlua{luaotfload.add_fallback("fpLeanCodeFallback", {
  "STIX Two Math:mode=harf;",
  "Apple Symbols:mode=harf;"
})}
\IfFontExistsTF{FreeMono}
  {\setmonofont{FreeMono}[Scale=MatchLowercase,RawFeature={fallback=fpLeanCodeFallback}]}
  {\IfFontExistsTF{JuliaMono}
    {\setmonofont{JuliaMono}[Scale=MatchLowercase,RawFeature={fallback=fpLeanCodeFallback}]}
    {\IfFontExistsTF{Iosevka}
      {\setmonofont{Iosevka}[Scale=MatchLowercase,RawFeature={fallback=fpLeanCodeFallback}]}
      {\IfFontExistsTF{DejaVu Sans Mono}
        {\setmonofont{DejaVu Sans Mono}[Scale=MatchLowercase,RawFeature={fallback=fpLeanCodeFallback}]}
        {\IfFontExistsTF{Noto Sans Mono}
          {\setmonofont{Noto Sans Mono}[Scale=MatchLowercase,RawFeature={fallback=fpLeanCodeFallback}]}
          {\setmonofont{Menlo}[Scale=MatchLowercase,RawFeature={fallback=fpLeanCodeFallback}]}}}}}

\definecolor{bookblue}{HTML}{1F5A70}
\definecolor{bookink}{HTML}{1F1F1F}
\definecolor{tocgray}{HTML}{4F6670}
\definecolor{codebg}{HTML}{EDEDED}
\definecolor{outputbg}{HTML}{F0F0F0}
\definecolor{codeborder}{HTML}{A8A8A8}
\definecolor{errorred}{HTML}{9D3A36}
\definecolor{warnorange}{HTML}{8B6A2B}
\definecolor{leadergray}{HTML}{222222}
\definecolor{leankeyword}{HTML}{1F7A3B}
\definecolor{leanstring}{HTML}{245A9C}
\definecolor{leancomment}{HTML}{5F8A8A}
\definecolor{leansort}{HTML}{725A8A}
\definecolor{leanconst}{HTML}{315D6D}
\definecolor{leannumber}{HTML}{755D2E}
\definecolor{leansorry}{HTML}{B33A3A}
\hypersetup{colorlinks=true, linkcolor=bookblue, urlcolor=bookblue, citecolor=bookblue}

\newcommand{\icode}[1]{\texttt{\small #1}}
\newcommand{\leanKeyword}[1]{\textcolor{leankeyword}{\textbf{#1}}}
\newcommand{\leanString}[1]{\textcolor{leanstring}{#1}}
\newcommand{\leanComment}[1]{\textcolor{leancomment}{\textit{#1}}}
\newcommand{\leanSort}[1]{\textcolor{leansort}{#1}}
\newcommand{\leanConst}[1]{\textcolor{leanconst}{#1}}
\newcommand{\leanNumber}[1]{\textcolor{leannumber}{#1}}
\newcommand{\leanSorry}[1]{\textcolor{leansorry}{\textbf{#1}}}
\newcommand{\bookRule}{\noindent\makebox[\linewidth][r]{\rule{\linewidth}{1pt}}}
\newcommand{\chapterword}{%
  \ifcase\value{chapter}ZERO%
  \or ONE%
  \or TWO%
  \or THREE%
  \or FOUR%
  \or FIVE%
  \or SIX%
  \or SEVEN%
  \or EIGHT%
  \or NINE%
  \or TEN%
  \or ELEVEN%
  \or TWELVE%
  \else \thechapter%
  \fi}
\newcommand{\plainchapter}[1]{%
  \cleardoublepage
  \chapter*{#1}
  \addcontentsline{toc}{chapter}{#1}
  \markboth{#1}{#1}
}
\newcommand{\plainchapternotoc}[1]{%
  \cleardoublepage
  \chapter*{#1}
  \markboth{#1}{#1}
}
\newcommand{\interludechapter}[1]{%
  \cleardoublepage
  \phantomsection
  \addcontentsline{toc}{chapter}{#1}
  \markboth{#1}{#1}
  \thispagestyle{plain}
  \vspace*{0.2in}
  {\sffamily\bfseries\raggedleft\color{bookink}
    \bookRule\par\vspace{0.55em}
    {\Large\mbox{INTERLUDE}\par}
    \vspace{0.35em}
    \bookRule\par
    \vspace{0.32in}
    {\LARGE\MakeUppercase{#1}\par}
  }
  \vspace{0.38in}
}
\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt plus 1pt}
\setlist{itemsep=2pt, topsep=4pt}
\raggedbottom
\setcounter{tocdepth}{1}

\makeatletter
\renewcommand{\cleardoublepage}{%
  \clearpage
  \if@twoside
    \ifodd\c@page
    \else
      \hbox{}\thispagestyle{empty}\newpage
      \if@twocolumn\hbox{}\newpage\fi
    \fi
  \fi
}
\makeatother

\titleformat{\chapter}[display]
  {\sffamily\bfseries\raggedleft\color{bookink}}
  {\bookRule\\[0.45em]\Large\mbox{CHAPTER}\\[0.2em]\Large\mbox{\chapterword}\\[0.45em]\bookRule}
  {16pt}
  {\LARGE\MakeUppercase}
\titleformat{name=\chapter,numberless}[display]
  {\sffamily\bfseries\raggedleft\color{bookink}}
  {\bookRule}
  {16pt}
  {\LARGE\MakeUppercase}
\titleformat{\section}{\Needspace{6\baselineskip}\sffamily\Large\bfseries\color{bookblue}}{\thesection}{0.65em}{}
\titleformat{\subsection}{\Needspace{5\baselineskip}\sffamily\large\bfseries\color{bookblue}}{\thesubsection}{0.65em}{}
\titleformat{\subsubsection}{\Needspace{4\baselineskip}\sffamily\normalsize\bfseries\color{bookblue}}{\thesubsubsection}{0.65em}{}
\titlespacing*{\chapter}{0pt}{0.2in}{0.32in}
\titlespacing*{\section}{0pt}{16pt plus 4pt}{6pt}
\titlespacing*{\subsection}{0pt}{12pt plus 3pt}{5pt}
\titlespacing*{\subsubsection}{0pt}{10pt plus 2pt}{4pt}

\renewcommand{\contentsname}{CONTENTS}
\titlecontents{chapter}[0pt]{\addvspace{5pt}\sffamily\bfseries\color{bookblue}\linespread{0.94}\selectfont}
  {\contentslabel{2.2em}}{}{\textcolor{leadergray}{\titlerule*[0.42pc]{.}}\textcolor{bookink}{\bfseries\contentspage}}
\titlecontents{section}[2.7em]{\sffamily\small\color{bookblue}\linespread{0.9}\selectfont}
  {\contentslabel{3em}}{}{\textcolor{leadergray}{\titlerule*[0.42pc]{.}}\textcolor{bookink}{\bfseries\contentspage}}
\titlecontents{subsection}[5.7em]{\sffamily\footnotesize\color{tocgray}\linespread{0.9}\selectfont}
  {\contentslabel{3.4em}}{}{\textcolor{leadergray}{\titlerule*[0.42pc]{.}}\textcolor{bookink}{\contentspage}}

\pagestyle{fancy}
\fancyhf{}
\fancyhead[LE]{\sffamily\scriptsize\bfseries Functional Programming in Lean - Lean 4.26.0}
\fancyhead[RO]{\sffamily\scriptsize\bfseries Functional Programming in Lean - Lean 4.26.0}
\fancyfoot[LE]{\sffamily\small\bfseries\thepage}
\fancyfoot[RE]{\sffamily\small\bfseries\nouppercase{\leftmark}}
\fancyfoot[LO]{\sffamily\small\bfseries\nouppercase{\leftmark}}
\fancyfoot[RO]{\sffamily\small\bfseries\thepage}
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\footrulewidth}{0.4pt}
\renewcommand{\chaptermark}[1]{\markboth{\thechapter.\ #1}{\thechapter.\ #1}}
\renewcommand{\sectionmark}[1]{}
\fancypagestyle{plain}{%
  \fancyhf{}
  \fancyfoot[LE,RO]{\sffamily\small\bfseries\thepage}
  \renewcommand{\headrulewidth}{0pt}
  \renewcommand{\footrulewidth}{0pt}
}
\fancypagestyle{tocplain}{%
  \fancyhf{}
  \fancyfoot[LE,RO]{\sffamily\small\bfseries\thepage}
  \renewcommand{\headrulewidth}{0pt}
  \renewcommand{\footrulewidth}{0.4pt}
}

\makeatletter
\newcommand{\miltableofcontents}{%
  \cleardoublepage
  \begingroup
    \pagestyle{tocplain}
    \thispagestyle{tocplain}
    \phantomsection
    \vspace*{42pt}
    {\sffamily\bfseries\LARGE\raggedleft\color{bookink}\contentsname\par}
    \vspace{36pt}
    \@starttoc{toc}
  \endgroup
}
\makeatother

\fvset{
  fontsize=\small,
  breaklines=true,
  breakanywhere=true,
  tabsize=2,
  obeytabs=true
}
\newenvironment{leaninput}{%
  \VerbatimEnvironment%
  \fvset{commandchars=\\\{\}}%
  \begin{tcolorbox}[
    breakable, enhanced,
    colback=codebg, colframe=codeborder, boxrule=0.35pt, arc=2pt,
    left=6pt, right=6pt, top=4pt, bottom=4pt,
    before skip=6pt, after skip=6pt
  ]%
  \begin{Verbatim}
}{%
  \end{Verbatim}
  \end{tcolorbox}
}
\newenvironment{leanoutput}{%
  \VerbatimEnvironment
  \begin{tcolorbox}[
    breakable, enhanced,
    colback=outputbg, colframe=codeborder, boxrule=0.35pt, arc=2pt,
    left=6pt, right=6pt, top=3pt, bottom=3pt,
    before skip=2pt, after skip=6pt
  ]%
  \begin{Verbatim}
}{%
  \end{Verbatim}
  \end{tcolorbox}
}
\newenvironment{leanerror}{%
  \VerbatimEnvironment
  \begin{tcolorbox}[
    breakable, enhanced,
    colback=outputbg, colframe=codeborder, boxrule=0.35pt, arc=2pt,
    left=6pt, right=6pt, top=4pt, bottom=4pt,
    before skip=4pt, after skip=6pt
  ]%
  \begin{Verbatim}
}{%
  \end{Verbatim}
  \end{tcolorbox}
}
\newenvironment{leanwarning}{%
  \VerbatimEnvironment
  \begin{tcolorbox}[
    breakable, enhanced,
    colback=outputbg, colframe=codeborder, boxrule=0.35pt, arc=2pt,
    left=6pt, right=6pt, top=4pt, bottom=4pt,
    before skip=4pt, after skip=6pt
  ]%
  \begin{Verbatim}
}{%
  \end{Verbatim}
  \end{tcolorbox}
}
\newenvironment{tableblock}{%
  \begin{center}
  \small
  \renewcommand{\arraystretch}{1.2}
}{%
  \end{center}
}

\begin{document}
\begin{titlepage}
\sffamily
\raggedleft
\vspace*{0.9in}
{\color{bookink}\bookRule\par}
\vspace{0.3in}
{\color{bookink}\Huge\bfseries FUNCTIONAL PROGRAMMING IN LEAN\par}
\vspace{0.28in}
{\Large David Thrane Christiansen\par}
\vspace{0.18in}
{\large Lean release 4.26.0 examples\par}
\vfill
{\large Print edition, June 2026\par}
\end{titlepage}
\frontmatter
\tableofcontents
\mainmatter
\chapter{Getting to Know Lean}
"""


DOCUMENT_START = PREAMBLE.split("\\frontmatter", 1)[0]


def build_document(root: Node, section_id: str) -> str:
    heading = find_by_id(root, section_id)
    if heading is None:
        raise SystemExit(f"could not find section id: {section_id}")
    section = nearest_section(heading)
    body = "\n".join(render_blocks(section.children))
    return PREAMBLE + "\n" + body + "\n\\end{document}\n"


def render_section_body(
    section: Node,
    unnumbered_headings: bool = False,
    exclude_section_titles: set[str] | None = None,
) -> str:
    heading = first_child_heading(section)
    children = section.children
    if heading and heading in children:
        children = children[children.index(heading) + 1 :]
    if exclude_section_titles:
        children = [
            child
            for child in children
            if not (child.tag == "section" and strip_number(top_section_title(child)) in exclude_section_titles)
        ]
    return "\n".join(render_blocks(children, unnumbered_headings=unnumbered_headings)).strip()


def child_sections_with_titles(section: Node, titles: set[str]) -> list[tuple[str, Node]]:
    found: list[tuple[str, Node]] = []
    heading = first_child_heading(section)
    children = section.children
    if heading and heading in children:
        children = children[children.index(heading) + 1 :]
    for child in children:
        if child.tag != "section":
            continue
        clean_title = strip_number(top_section_title(child))
        if clean_title in titles:
            found.append((clean_title, child))
    return found


def render_whole_book(root: Node) -> str:
    frontmatter: list[str] = []
    mainmatter: list[str] = []
    backmatter: list[str] = []

    for section in top_sections(root):
        title = top_section_title(section)
        clean_title = strip_number(title)
        if not clean_title or clean_title.lower() in {"table of contents", "contents"}:
            continue
        is_intro = clean_title == "Introduction"
        body = render_section_body(
            section,
            unnumbered_headings=is_intro,
            exclude_section_titles=BACKMATTER_SECTION_TITLES if is_intro else None,
        )
        if not body:
            continue

        if clean_title == "Acknowledgments":
            frontmatter.append(f"\\plainchapternotoc{{{latex_escape(clean_title)}}}\n\n{body}")
        elif clean_title == "Introduction":
            mainmatter.append(f"\\plainchapter{{{latex_escape(clean_title)}}}\n\n{body}")
            for back_title, back_section in child_sections_with_titles(section, BACKMATTER_SECTION_TITLES):
                back_body = render_section_body(back_section, unnumbered_headings=True)
                if back_body:
                    backmatter.append(f"\\plainchapter{{{latex_escape(back_title)}}}\n\n{back_body}")
        elif clean_title.startswith("Interlude"):
            interlude_body = render_section_body(section, unnumbered_headings=True)
            mainmatter.append(f"\\interludechapter{{{latex_escape(clean_title)}}}\n\n{interlude_body}")
        elif is_numbered_title(title):
            mainmatter.append(f"\\chapter{{{latex_escape(clean_title)}}}\n\n{body}")
        else:
            mainmatter.append(f"\\plainchapter{{{latex_escape(clean_title)}}}\n\n{body}")

    return (
        DOCUMENT_START
        + "\\frontmatter\n"
        + "\n\n".join(frontmatter)
        + "\n\\miltableofcontents\n"
        + "\n\\mainmatter\n"
        + "\n\n".join(mainmatter)
        + ("\n\\backmatter\n" + "\n\n".join(backmatter) if backmatter else "")
        + "\n\\end{document}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("index.html"))
    parser.add_argument("--section", default="evaluating")
    parser.add_argument("--book", action="store_true", help="render the whole book instead of a single section sample")
    parser.add_argument("--output", type=Path, default=Path("latex-prototype/evaluating-expressions.tex"))
    args = parser.parse_args()

    root = parse_html(args.input)
    tex = render_whole_book(root) if args.book else build_document(root, args.section)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(tex, encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
