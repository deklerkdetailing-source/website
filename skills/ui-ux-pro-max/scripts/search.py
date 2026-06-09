#!/usr/bin/env python3
"""
UI/UX Pro Max Search Tool
Search design system data across domains with TF-IDF-style keyword matching.
"""

import csv
import sys
import argparse
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import datetime

# Data directory relative to this script
DATA_DIR = Path(__file__).parent.parent / "data"


DOMAIN_FILE_MAP = {
    "product": "products",
    "style": "styles",
    "color": "colors",
    "typography": "typography",
    "landing": "landing",
    "chart": "charts",
    "ux": "ux",
    "google-fonts": "google-fonts",
    "react": "react",
    "web": "web",
    "prompt": "prompt",
    "ui-reasoning": "ui-reasoning",
    # Plurals work directly too
    "products": "products",
    "styles": "styles",
    "colors": "colors",
    "charts": "charts",
}


def resolve_domain_file(domain: str) -> str:
    """Resolve domain alias to actual filename (without .csv)."""
    return DOMAIN_FILE_MAP.get(domain.lower(), domain)


def load_csv(filepath: Path) -> List[Dict]:
    """Load CSV file and return list of row dicts."""
    rows = []
    if not filepath.exists():
        return rows
    try:
        with open(filepath, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except Exception as e:
        print(f"Warning: Could not load {filepath}: {e}", file=sys.stderr)
    return rows


def score_row(row: Dict, query_tokens: List[str]) -> float:
    """
    Score a CSV row by TF-IDF-style keyword overlap.
    Score = number of query tokens found in any column / total query tokens
    """
    if not query_tokens:
        return 0.0
    # Combine all column values into lowercase text
    text = " ".join(str(v).lower() for v in row.values())
    matches = sum(1 for token in query_tokens if token in text)
    return matches / len(query_tokens)


def search_domain(
    query: str,
    domain: str,
    max_results: int = 5,
    stack: bool = False
) -> List[Tuple[float, Dict]]:
    """Search a single domain CSV and return ranked results."""
    if stack:
        filepath = DATA_DIR / "stacks" / f"{domain}.csv"
    else:
        resolved = resolve_domain_file(domain)
        filepath = DATA_DIR / f"{resolved}.csv"

    rows = load_csv(filepath)
    if not rows:
        return []

    query_tokens = query.lower().split()
    scored = [(score_row(row, query_tokens), row) for row in rows]
    scored = [(s, r) for s, r in scored if s > 0]
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:max_results]


def apply_reasoning(
    product_result: Optional[Dict],
    all_results: Dict[str, List[Tuple[float, Dict]]]
) -> Dict:
    """
    Apply ui-reasoning.csv rules to boost recommendations
    based on product type match.
    """
    if not product_result:
        return {}

    product_name = product_result.get("name", "").lower()
    product_keywords = product_result.get("keywords", "").lower()
    product_industry = product_result.get("industry", "").lower()

    # Combine product context
    product_context = f"{product_name} {product_keywords} {product_industry}"
    product_tokens = product_context.split()

    reasoning_rows = load_csv(DATA_DIR / "ui-reasoning.csv")
    if not reasoning_rows:
        return {}

    best_reason = None
    best_score = 0.0
    for row in reasoning_rows:
        keyword = row.get("product_keyword", "").lower()
        if any(keyword in token or token in keyword for token in product_tokens):
            score = sum(1 for t in product_tokens if keyword in t or t in keyword)
            if score > best_score:
                best_score = score
                best_reason = row

    return best_reason or {}


def box_wrap(text: str, width: int = 72) -> str:
    """Wrap text to fit inside a box."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= width:
            current = (current + " " + word).strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return "\n".join(lines)


def format_ascii_box(title: str, sections: List[Tuple[str, str]]) -> str:
    """Format output as an ASCII box with sections."""
    width = 74
    inner = width - 2
    lines = []

    # Top border
    lines.append("┌" + "─" * inner + "┐")

    # Title
    title_padded = f" {title} ".center(inner)
    lines.append("│" + title_padded + "│")
    lines.append("├" + "─" * inner + "┤")

    for section_title, content in sections:
        if section_title:
            label = f" ◆ {section_title} "
            lines.append("│" + label + " " * (inner - len(label)) + "│")

        if content:
            for line in content.split("\n"):
                # Handle line wrapping
                if len(line) > inner - 2:
                    wrapped = box_wrap(line, inner - 4)
                    for wl in wrapped.split("\n"):
                        padded = "  " + wl
                        lines.append("│ " + padded + " " * max(0, inner - 1 - len(padded)) + "│")
                else:
                    padded = "  " + line
                    lines.append("│ " + padded + " " * max(0, inner - 1 - len(padded)) + "│")

        lines.append("│" + " " * inner + "│")

    # Bottom border
    lines[-1] = "└" + "─" * inner + "┘"

    return "\n".join(lines)


def format_markdown(title: str, sections: List[Tuple[str, str]]) -> str:
    """Format output as Markdown."""
    lines = [f"# {title}", ""]
    for section_title, content in sections:
        if section_title:
            lines.append(f"## {section_title}")
        if content:
            lines.append(content)
        lines.append("")
    return "\n".join(lines)


def run_design_system(
    query: str,
    project_name: Optional[str] = None,
    output_format: str = "ascii",
    persist: bool = False,
    page: Optional[str] = None
) -> str:
    """
    Generate a complete design system card by searching all domains
    and applying reasoning rules.
    """
    title = f"Design System: {project_name}" if project_name else "Design System"

    # Search all core domains
    domains_to_search = ["products", "styles", "colors", "typography", "landing"]
    results = {}
    for domain in domains_to_search:
        found = search_domain(query, domain, max_results=3)
        if found:
            results[domain] = found

    # Normalize: alias singular to plural keys
    for alias, key in [("product", "products"), ("style", "styles"), ("color", "colors")]:
        if key in results:
            results[alias] = results[key]

    # Get top product match
    top_product = results.get("products", [(0, {})])[0][1] if results.get("products") else {}

    # Apply reasoning rules
    reasoning = apply_reasoning(top_product, results)

    color_results = results.get("colors", [])

    # Build sections
    sections = []

    # --- Product Pattern ---
    product_lines = []
    for score, row in results.get("products", [])[:2]:
        name = row.get("name", "")
        pattern = row.get("pattern", "")
        layout = row.get("layout", "")
        density = row.get("density", "")
        nav = row.get("navigation", "")
        tone = row.get("tone", "")
        industry = row.get("industry", "")
        product_lines.append(
            f"• {name} ({industry})\n"
            f"  Pattern: {pattern} | Layout: {layout} | Density: {density}\n"
            f"  Navigation: {nav} | Tone: {tone}"
        )
    if product_lines:
        sections.append(("Product Pattern", "\n".join(product_lines)))

    # --- Recommended Style ---
    style_lines = []
    # Use reasoning if available
    if reasoning:
        style_lines.append(f"Reasoning: {reasoning.get('reason', '')}")
        style_lines.append(f"Style Match: {reasoning.get('style_match', '')}")
        style_lines.append(f"Color Match: {reasoning.get('color_match', '')}")
        style_lines.append(f"Typography: {reasoning.get('typography_match', '')}")
        anti = reasoning.get("anti_pattern", "")
        if anti:
            style_lines.append(f"Avoid: {anti}")
    else:
        for score, row in results.get("styles", [])[:2]:
            name = row.get("name", "")
            desc = row.get("description", "")
            best_for = row.get("best_for", "")
            effects = row.get("effects", "")
            style_lines.append(
                f"• {name}: {desc}\n"
                f"  Best for: {best_for}\n"
                f"  Effects: {effects}"
            )
    if style_lines:
        sections.append(("Style & Reasoning", "\n".join(style_lines)))

    # --- Style Details ---
    style_detail_lines = []
    for score, row in results.get("styles", [])[:1]:
        name = row.get("name", "")
        border = row.get("border_radius", "")
        shadows = row.get("shadows", "")
        effects = row.get("effects", "")
        css = row.get("css_hints", "")
        avoid = row.get("avoid_for", "")
        style_detail_lines.append(
            f"• {name}\n"
            f"  Border Radius: {border} | Shadows: {shadows}\n"
            f"  Effects: {effects}\n"
            f"  CSS: {css}\n"
            f"  Avoid for: {avoid}"
        )
    if style_detail_lines:
        sections.append(("Style Details", "\n".join(style_detail_lines)))

    # --- Color Palette ---
    color_lines = []
    for score, row in color_results[:2]:
        name = row.get("name", "")
        primary = row.get("primary", "")
        secondary = row.get("secondary", "")
        accent = row.get("accent", "")
        bg = row.get("background", "")
        text = row.get("text", "")
        notes = row.get("notes", "")
        dark_bg = row.get("dark_background", "")
        dark_text = row.get("dark_text", "")
        color_lines.append(
            f"• {name}\n"
            f"  Primary: {primary} | Secondary: {secondary} | Accent: {accent}\n"
            f"  Background: {bg} | Text: {text}\n"
            f"  Dark: bg={dark_bg} text={dark_text}\n"
            f"  Notes: {notes}"
        )
    if color_lines:
        sections.append(("Color Palette", "\n".join(color_lines)))

    # --- Typography ---
    typo_lines = []
    for score, row in results.get("typography", [])[:2]:
        name = row.get("name", "")
        heading = row.get("heading_font", "")
        body = row.get("body_font", "")
        mono = row.get("mono_font", "")
        hw = row.get("heading_weight", "")
        bw = row.get("body_weight", "")
        scale = row.get("scale", "")
        lh = row.get("line_height", "")
        ls = row.get("letter_spacing", "")
        notes = row.get("notes", "")
        best = row.get("best_for", "")
        typo_lines.append(
            f"• {name}\n"
            f"  Heading: {heading} ({hw}) | Body: {body} ({bw}) | Mono: {mono}\n"
            f"  Scale: {scale} | Line Height: {lh} | Tracking: {ls}\n"
            f"  Best for: {best}\n"
            f"  Notes: {notes}"
        )
    if typo_lines:
        sections.append(("Typography", "\n".join(typo_lines)))

    # --- Landing Structure ---
    landing_lines = []
    for score, row in results.get("landing", [])[:1]:
        name = row.get("name", "")
        pattern = row.get("pattern", "")
        sects = row.get("sections", "")
        cta = row.get("cta_placement", "")
        hero = row.get("hero_type", "")
        conv = row.get("conversion_focus", "")
        landing_lines.append(
            f"• {name} ({pattern})\n"
            f"  Sections: {sects}\n"
            f"  CTA: {cta} | Hero: {hero}\n"
            f"  Conversion focus: {conv}"
        )
    if landing_lines:
        sections.append(("Landing Structure", "\n".join(landing_lines)))

    # --- Anti-Patterns Warning ---
    anti_patterns = []
    if reasoning:
        ap = reasoning.get("anti_pattern", "")
        if ap:
            anti_patterns.append(f"From reasoning rules: {ap}")
    for score, row in results.get("styles", [])[:1]:
        av = row.get("avoid_for", "")
        if av:
            anti_patterns.append(f"Style avoid: {av}")
    if anti_patterns:
        sections.append(("Anti-Patterns to Avoid", "\n".join(f"  {ap}" for ap in anti_patterns)))

    # --- Format output ---
    if output_format == "markdown":
        output = format_markdown(title, sections)
    else:
        output = format_ascii_box(title, sections)

    # --- Persist if requested ---
    if persist:
        output_persist(output, project_name, page, output_format)

    return output


def output_persist(content: str, project_name: Optional[str], page: Optional[str], fmt: str):
    """Write design system to markdown files."""
    # Determine base directory (relative to cwd)
    base_dir = Path.cwd() / "design-system"
    base_dir.mkdir(exist_ok=True)

    master_path = base_dir / "MASTER.md"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # Convert to markdown for storage
    if fmt != "markdown":
        # Already have ASCII; store the raw content as code block
        md_content = f"# Design System Master\n\nGenerated: {timestamp}\n\n```\n{content}\n```\n"
    else:
        md_content = f"# Design System Master\n\nGenerated: {timestamp}\n\n{content}\n"

    with open(master_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"\n[Persisted] Written to: {master_path}", file=sys.stderr)

    if page:
        pages_dir = base_dir / "pages"
        pages_dir.mkdir(exist_ok=True)
        safe_page = page.lower().replace(" ", "-")
        page_path = pages_dir / f"{safe_page}.md"
        page_content = (
            f"# Page Override: {page}\n\n"
            f"Generated: {timestamp}\n\n"
            f"_This file overrides MASTER.md rules for the {page} page._\n\n"
            f"## Notes\n\n"
            f"- Add page-specific color overrides here\n"
            f"- Add layout deviations from Master\n"
            f"- Add component-specific rules\n\n"
            f"## Source\n\n"
            f"See design-system/MASTER.md for global rules.\n"
        )
        with open(page_path, "w", encoding="utf-8") as f:
            f.write(page_content)
        print(f"[Persisted] Page override: {page_path}", file=sys.stderr)


def run_domain_search(query: str, domain: str, max_results: int = 5):
    """Search a single domain and print results."""
    results = search_domain(query, domain, max_results=max_results)

    if not results:
        print(f"No results found in domain '{domain}' for query: '{query}'")
        print(f"(Looked for: {DATA_DIR / (domain + '.csv')})")
        return

    print(f"\nSearch results for '{query}' in domain '{domain}':\n")
    print("─" * 70)

    for i, (score, row) in enumerate(results, 1):
        print(f"\n[{i}] Score: {score:.2f}")
        # Print key fields
        for key, value in row.items():
            if value and value.strip():
                print(f"  {key}: {value}")
        print("─" * 40)


def run_stack_search(query: str, stack: str, max_results: int = 10):
    """Search stack-specific guidelines."""
    results = search_domain(query, stack, max_results=max_results, stack=True)

    if not results:
        print(f"No results found in stack '{stack}' for query: '{query}'")
        print(f"(Looked for: {DATA_DIR / 'stacks' / (stack + '.csv')})")
        return

    print(f"\nStack guidelines for '{query}' ({stack}):\n")
    print("─" * 70)

    for i, (score, row) in enumerate(results, 1):
        category = row.get("category", "")
        rule = row.get("rule", "")
        description = row.get("description", "")
        code_hint = row.get("code_hint", "")
        anti_pattern = row.get("anti_pattern", "")

        print(f"\n[{i}] {category}: {rule} (score: {score:.2f})")
        if description:
            print(f"  {description}")
        if code_hint:
            print(f"  Code: {code_hint}")
        if anti_pattern:
            print(f"  Anti-pattern: {anti_pattern}")
        print("─" * 40)


def main():
    parser = argparse.ArgumentParser(
        description="UI/UX Pro Max Design Search Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 search.py "premium automotive" --design-system -p "De Klerk Detailing"
  python3 search.py "glassmorphism dark" --domain style
  python3 search.py "navigation list performance" --stack react-native
  python3 search.py "fintech blue" --domain colors -n 3
  python3 search.py "luxury" --design-system -f markdown --persist -p "Luxury Brand"
        """
    )

    parser.add_argument("query", help="Search query string")
    parser.add_argument(
        "--design-system",
        action="store_true",
        help="Generate full design system card (searches all domains)"
    )
    parser.add_argument(
        "--domain",
        type=str,
        help="Search a single domain CSV (product, style, colors, typography, landing, chart, ux, google-fonts, react, web, prompt)"
    )
    parser.add_argument(
        "--stack",
        type=str,
        help="Search stack-specific guidelines (e.g. react-native)"
    )
    parser.add_argument(
        "-p", "--project",
        type=str,
        help="Project name for design system header"
    )
    parser.add_argument(
        "-f", "--format",
        choices=["ascii", "markdown"],
        default="ascii",
        help="Output format: ascii (default) or markdown"
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Write design-system/MASTER.md (and optionally pages/<page>.md)"
    )
    parser.add_argument(
        "--page",
        type=str,
        help="Page name for page-specific override file (used with --persist)"
    )
    parser.add_argument(
        "-n", "--max-results",
        type=int,
        default=5,
        help="Maximum number of results for domain search (default: 5)"
    )

    args = parser.parse_args()

    if args.design_system:
        output = run_design_system(
            query=args.query,
            project_name=args.project,
            output_format=args.format,
            persist=args.persist,
            page=args.page
        )
        print(output)

    elif args.domain:
        run_domain_search(args.query, args.domain, max_results=args.max_results)

    elif args.stack:
        run_stack_search(args.query, args.stack, max_results=args.max_results)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
