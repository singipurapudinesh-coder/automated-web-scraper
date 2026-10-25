import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup, Tag


def parse_html(html_content: str, parser: str = "lxml") -> BeautifulSoup:
    """Parses raw HTML into a BeautifulSoup object."""
    try:
        return BeautifulSoup(html_content, parser)
    except Exception:
        # Fallback to standard html.parser if lxml fails
        return BeautifulSoup(html_content, "html.parser")


def clean_text(text: Optional[str]) -> str:
    """Strips leading/trailing whitespace and collapses internal multiple spaces."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def extract_field(
    element: Tag,
    selector: str,
    attribute: Optional[str] = None,
    default: Any = "",
) -> Any:
    """Extracts text or a specific attribute from a child matching the CSS selector."""
    target = element.select_one(selector)
    if not target:
        return default

    if attribute:
        return target.get(attribute, default)
    return clean_text(target.get_text())


def extract_list(
    element: Tag,
    selector: str,
    attribute: Optional[str] = None,
) -> List[Any]:
    """Extracts a list of texts or attributes matching a CSS selector."""
    targets = element.select(selector)
    results = []
    for t in targets:
        if attribute:
            val = t.get(attribute)
            if val is not None:
                results.append(val)
        else:
            text = clean_text(t.get_text())
            if text:
                results.append(text)
    return results

