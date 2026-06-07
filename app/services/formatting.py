from markupsafe import Markup, escape


def format_lesson_content(content: str | None) -> Markup:
    if not content or not content.strip():
        return Markup('<p class="muted">No text notes for this lesson yet.</p>')

    lines = content.replace("\r\n", "\n").split("\n")
    html: list[str] = []
    paragraph: list[str] = []
    in_list = False
    in_code = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            text = " ".join(line.strip() for line in paragraph if line.strip())
            if text:
                html.append(f"<p>{escape(text)}</p>")
            paragraph = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            html.append("</ul>")
            in_list = False

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            close_list()
            if in_code:
                html.append(f"<pre><code>{escape('\n'.join(code_lines))}</code></pre>")
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            flush_paragraph()
            close_list()
            continue

        if stripped.startswith("### "):
            flush_paragraph()
            close_list()
            html.append(f"<h4>{escape(stripped[4:].strip())}</h4>")
            continue
        if stripped.startswith("## "):
            flush_paragraph()
            close_list()
            html.append(f"<h3>{escape(stripped[3:].strip())}</h3>")
            continue
        if stripped.startswith("# "):
            flush_paragraph()
            close_list()
            html.append(f"<h2>{escape(stripped[2:].strip())}</h2>")
            continue

        if stripped.startswith("> "):
            flush_paragraph()
            close_list()
            html.append(f"<blockquote>{escape(stripped[2:].strip())}</blockquote>")
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            flush_paragraph()
            if not in_list:
                html.append("<ul>")
                in_list = True
            html.append(f"<li>{escape(stripped[2:].strip())}</li>")
            continue

        paragraph.append(stripped)

    if in_code:
        html.append(f"<pre><code>{escape('\n'.join(code_lines))}</code></pre>")
    flush_paragraph()
    close_list()
    return Markup("\n".join(html))
