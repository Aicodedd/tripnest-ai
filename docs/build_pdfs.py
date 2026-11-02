"""Build PDFs from the Markdown documents with headless Google Chrome, then verify them.

Usage (repo root):  .venv/bin/python docs/build_pdfs.py [name ...]
Checks: MRD has exactly 1 A4 page, PRD exactly 2, every PDF opens, has text, and contains its own title.
"""
import html
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown
from pypdf import PdfReader

DOCS = Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
NAMES = ["MRD", "PRD", "EPICS", "USER_STORIES", "REQUIREMENT_TRACEABILITY", "SYSTEM_ARCHITECTURE", "DATABASE_SCHEMA",
         "API_DOCUMENTATION", "AI_ML_DOCUMENTATION", "TEST_PLAN", "TEST_RESULTS", "DEPLOYMENT_GUIDE", "USER_GUIDE", "JUDGE_DEMO_GUIDE", "SUBMISSION_SUMMARY"]
FONT = {"MRD": 9.6, "PRD": 9.6}      # points; everything else 10.5
PAGES = {"MRD": 1, "PRD": 2}         # exact A4 page counts required by the brief

CSS = """
@page { size: A4; margin: %(margin)s; }
* { box-sizing: border-box; }
body { font-family: "Helvetica Neue", Arial, sans-serif; font-size: %(pt)spt; line-height: %(lh)s; color: #141414; margin: 0; }
h1 { font-size: 1.75em; margin: 0 0 .15em; letter-spacing: -.01em; }
h2 { font-size: 1.22em; margin: .9em 0 .25em; padding-bottom: .12em; border-bottom: 1.5px solid #f2a516; }
h3 { font-size: 1.05em; margin: .7em 0 .2em; }
p { margin: .3em 0; } ul, ol { margin: .25em 0; padding-left: 1.3em; } li { margin: .08em 0; }
table { border-collapse: collapse; width: 100%%; margin: .35em 0; font-size: .94em; page-break-inside: auto; }
th, td { border: 1px solid #d9dcd6; padding: .22em .5em; text-align: left; vertical-align: top; }
th { background: #f2f3f0; } tr { page-break-inside: avoid; }
td:first-child { white-space: nowrap; }
code { font-family: Menlo, monospace; font-size: .9em; background: #f2f3f0; padding: 0 .2em; border-radius: 3px; }
pre { background: #f2f3f0; padding: .5em .7em; overflow: hidden; font-size: .85em; white-space: pre-wrap; border-radius: 4px; }
pre code { background: none; padding: 0; }
blockquote { margin: .4em 0; padding: .2em .8em; border-left: 3px solid #f2a516; background: #fff8e6; }
a { color: #141414; } hr { border: 0; border-top: 1px solid #d9dcd6; margin: .8em 0; }
"""


def build(name: str) -> Path:
    src = DOCS / f"{name}.md"
    body = markdown.markdown(src.read_text(), extensions=["tables", "fenced_code", "sane_lists"])
    margin = "11mm 14mm" if name in PAGES else "16mm 16mm"
    page = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>{html.escape(name)}</title>"
            f"<style>{CSS % {'pt': FONT.get(name, 10.5), 'margin': margin, 'lh': 1.34 if name in PAGES else 1.4}}</style></head><body>{body}</body></html>")
    out = DOCS / f"{name}.pdf"
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / f"{name}.html"
        f.write_text(page)
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={out}", f.as_uri()],
                       check=True, capture_output=True, timeout=120)
    return out


def verify(name: str, pdf: Path) -> str:
    r = PdfReader(str(pdf))
    pages = len(r.pages)
    text = " ".join((p.extract_text() or "") for p in r.pages)
    title = re.sub(r"[#*`]", "", (DOCS / f"{name}.md").read_text().splitlines()[0]).strip()
    problems = []
    if name in PAGES and pages != PAGES[name]:
        problems.append(f"expected {PAGES[name]} page(s), got {pages}")
    if len(text) < 300:
        problems.append("almost no text extracted")
    if title.split(":")[0].lower()[:20] not in text.lower():
        problems.append(f"title '{title}' not found in text")
    w, h = (float(x) for x in r.pages[0].mediabox[2:])
    if abs(w - 595) > 3 or abs(h - 842) > 3:
        problems.append(f"page size {w:.0f}x{h:.0f}pt is not A4")
    return f"{name:<26} {pages} page(s) {len(text):>6} chars  " + ("OK" if not problems else "PROBLEM: " + "; ".join(problems))


def check_test_references() -> list[str]:
    """Every `test_...` name cited in the documents must exist in the backend or browser test files."""
    root = DOCS.parent
    tests = set()
    for f in [*root.glob("backend/tests/test_*.py"), *root.glob("e2e/test_*.py")]:
        tests |= set(re.findall(r"^def (test_\w+)", f.read_text(), re.M))
    missing = []
    for md in DOCS.glob("*.md"):
        for n in set(re.findall(r"`(test_\w+\*?)`", md.read_text())):
            ok = any(t.startswith(n[:-1]) for t in tests) if n.endswith("*") else n in tests
            if not ok:
                missing.append(f"{md.name}: {n}")
    return sorted(missing)


if __name__ == "__main__":
    names = sys.argv[1:] or NAMES
    bad = 0
    stale = check_test_references()
    for m in stale:
        print("STALE TEST REFERENCE", m)
    bad += len(stale)
    for n in names:
        if not (DOCS / f"{n}.md").exists():
            print(f"{n:<26} missing source"); bad += 1; continue
        line = verify(n, build(n))
        print(line); bad += "PROBLEM" in line
    sys.exit(1 if bad else 0)
