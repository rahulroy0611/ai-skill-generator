import argparse
import json
import os
import re
import sys
import asyncio
import zipfile
import tempfile
from datetime import datetime

import pdfplumber
import httpx
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from urllib.parse import urlparse, urljoin

EMBED_MODEL_NAME = os.environ.get("EMBED_MODEL_NAME", "all-MiniLM-L6-v2")

AGENT_CONFIGS = {
    "opencode":     "AGENTS.md",
    "codex":        "AGENTS.md",
    "cursor":       ".cursorrules",
    "copilot":      "copilot-instructions.md",
    "windsurf":     ".windsurfrules",
    "cline":        ".clinerules",
    "aider":        "CONVENTIONS.md",
    "systemprompt": "system-prompt.txt",
}


# ── Text extraction ──────────────────────────────────────────────────────────

def extract_text_pdf(file_path: str) -> str:
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


def chunk_text(text: str, chunk_size: int = 500) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, current = [], ""
    for sentence in sentences:
        if len(current) + len(sentence) <= chunk_size:
            current += " " + sentence
        else:
            if current:
                chunks.append(current.strip())
            current = sentence
    if current:
        chunks.append(current.strip())
    return chunks


def extract_text_html(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript", "meta", "link"]):
        tag.decompose()
    text = soup.get_text(separator='\n')
    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join(line for line in lines if line)


# ── Web crawler ──────────────────────────────────────────────────────────────

def _normalize_url(base_url: str, link: str):
    if not link:
        return None
    try:
        full = urljoin(base_url, link.strip())
        parsed = urlparse(full)
        path = re.sub(r'/+', '/', parsed.path.rstrip('/')) or '/'
        clean = f"{parsed.scheme}://{parsed.netloc}{path}"
        if parsed.query:
            clean += f"?{parsed.query}"
        return clean
    except Exception:
        return None


def _is_internal(base_url: str, link: str, prefix: str) -> bool:
    if not link:
        return False
    link = link.strip()
    if link.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
        return False
    if link.startswith(('http://', 'https://')):
        parsed = urlparse(link)
        if parsed.netloc != urlparse(base_url).netloc:
            return False
        if prefix and not parsed.path.startswith(prefix):
            return False
    return True


async def _fetch_sitemap(client, base_url: str, prefix: str, headers: dict) -> list[str]:
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    urls, seen = [], set()

    async def parse(sitemap_url):
        if sitemap_url in seen:
            return
        seen.add(sitemap_url)
        try:
            r = await client.get(sitemap_url, headers=headers, timeout=15, follow_redirects=True)
            if r.status_code != 200:
                return
            soup = BeautifulSoup(r.text, 'xml')
            for loc in soup.find_all('sitemap'):
                tag = loc.find('loc')
                if tag and tag.text.strip():
                    await parse(tag.text.strip())
            for loc in soup.find_all('url'):
                tag = loc.find('loc')
                if tag and tag.text.strip():
                    url = _normalize_url(base_url, tag.text.strip())
                    if url and (not prefix or urlparse(url).path.startswith(prefix)):
                        urls.append(url)
        except Exception:
            pass

    for candidate in [f"{root}/sitemap.xml", f"{root}/sitemap_index.xml"]:
        await parse(candidate)
    return urls


async def crawl_website_async(url: str, max_pages: int = None, max_chars: int = None, progress_callback=None):
    visited = set()
    pages_text = []
    fetched = 0
    title = None
    semaphore = asyncio.Semaphore(10)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    parsed_start = urlparse(url)
    path = parsed_start.path
    prefix = ""
    if path and path != '/':
        if not path.endswith('/'):
            path = path.rsplit('/', 1)[0] + '/'
        prefix = path

    async def fetch_page(client, u):
        async with semaphore:
            try:
                r = await client.get(u, headers=headers, timeout=15, follow_redirects=True)
                if r.status_code == 200 and 'text/html' in r.headers.get('content-type', ''):
                    return u, r.text
            except Exception:
                pass
        return None

    async with httpx.AsyncClient() as client:
        sitemap_urls = await _fetch_sitemap(client, url, prefix, headers)
        queue = list(dict.fromkeys([url] + sitemap_urls)) if sitemap_urls else [url]

    async with httpx.AsyncClient() as client:
        while queue:
            if max_pages and len(visited) >= max_pages:
                break
            batch, queue = queue[:20], queue[20:]
            results = await asyncio.gather(*[fetch_page(client, u) for u in batch])

            new_links = []
            for result in results:
                if not result:
                    continue
                page_url, html = result
                if page_url in visited:
                    continue
                visited.add(page_url)
                fetched += 1

                if title is None and page_url == url:
                    soup = BeautifulSoup(html, 'html.parser')
                    tag = soup.find('title')
                    title = tag.text.strip() if tag else None

                text = extract_text_html(html)
                if text.strip():
                    pages_text.append(f"=== {page_url} ===\n{text}\n")

                soup = BeautifulSoup(html, 'html.parser')
                for a in soup.find_all('a', href=True):
                    if _is_internal(page_url, a['href'], prefix):
                        clean = _normalize_url(page_url, a['href'])
                        if clean and clean not in visited and clean not in queue and clean not in new_links:
                            new_links.append(clean)

                if progress_callback:
                    progress_callback(fetched, len(visited))

            queue.extend(new_links)

    full_text = '\n'.join(pages_text)
    if max_chars and len(full_text) > max_chars:
        full_text = full_text[:max_chars] + "\n\n... (truncated)"

    return full_text, title or urlparse(url).netloc


# ── Skill generation ─────────────────────────────────────────────────────────

def generate_skill(name: str, description: str, text: str, output_dir: str = "output"):
    print(f"Loading embedding model: {EMBED_MODEL_NAME}")
    model = SentenceTransformer(EMBED_MODEL_NAME)

    if not text.strip():
        print("Error: No text content extracted")
        sys.exit(1)

    print(f"Extracted {len(text):,} characters")
    print("Chunking text...")
    chunks = chunk_text(text)
    print(f"Created {len(chunks)} chunks")

    print("Generating embeddings...")
    embeddings = model.encode(chunks, convert_to_numpy=True).tolist()

    safe_name = re.sub(r'[^\w\-_. ]', '_', name)
    os.makedirs(output_dir, exist_ok=True)

    knowledge = "\n\n---\n\n".join(chunks)

    # ── .skill (ZIP + SKILL.md — Claude-compatible) ──
    skill_md = f"---\nname: {name}\ndescription: {description}\n---\n\n{knowledge}\n"
    skill_path = os.path.join(output_dir, f"{safe_name}.skill")
    with zipfile.ZipFile(skill_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("SKILL.md", skill_md)
    print(f"  Created: {safe_name}.skill  (Claude-compatible ZIP)")

    # ── .md (portable markdown) ──
    md_path = os.path.join(output_dir, f"{safe_name}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {name}\n\n{description}\n\n---\n\n{knowledge}\n")
    print(f"  Created: {safe_name}.md")

    # ── .json (full data with embeddings) ──
    json_path = os.path.join(output_dir, f"{safe_name}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "name": name,
            "description": description,
            "type": "rag",
            "generated": datetime.now().isoformat(),
            "chunks": [{"index": i, "content": c, "embedding": e} for i, (c, e) in enumerate(zip(chunks, embeddings))],
        }, f, indent=2)
    print(f"  Created: {safe_name}.json")

    # ── Agent exports ──
    agents_dir = os.path.join(output_dir, "agent-exports")
    os.makedirs(agents_dir, exist_ok=True)
    for agent_key, filename in AGENT_CONFIGS.items():
        if agent_key == "systemprompt":
            content = (
                f"You have access to the following knowledge base: {name}\n\n"
                f"{description}\n\n"
                f"{'=' * 60}\n\n{knowledge}"
            )
        else:
            content = (
                f"# {name}\n\n> {description}\n\n"
                f"## Instructions\n\nYou have access to the following knowledge base. "
                f"Use it to answer questions and provide accurate information related to this topic. "
                f"Always ground your responses in this content.\n\n"
                f"## Knowledge Base\n\n{knowledge}\n"
            )
        export_path = os.path.join(agents_dir, f"{safe_name}-{filename}")
        with open(export_path, "w", encoding="utf-8") as f:
            f.write(content)

    print(f"  Created: agent-exports/ ({len(AGENT_CONFIGS)} agent formats)")
    print(f"\nAll files saved to: {output_dir}/")
    return output_dir


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AI Skill Generator CLI — Convert PDFs or URLs to AI skill files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ai-skill-generator document.pdf
  ai-skill-generator https://docs.example.com/en/ -o ./skills
  ai-skill-generator https://hacktricks.wiki/en/ --max-pages 200
  ai-skill-generator document.pdf --description "Security controls reference"
        """
    )
    parser.add_argument("input", help="Path to a PDF file or a URL to crawl")
    parser.add_argument("-o", "--output", default="output", help="Output directory (default: output)")
    parser.add_argument("-d", "--description", default="", help="Short description of the skill")
    parser.add_argument("-m", "--max-pages", type=int, default=None, help="Max pages to crawl for URLs")
    parser.add_argument("-c", "--max-chars", type=int, default=None, help="Max characters to extract")

    args = parser.parse_args()
    is_url = args.input.startswith(("http://", "https://"))

    if is_url:
        print(f"Crawling: {args.input}")
        def progress(fetched, visited):
            print(f"  Crawled {fetched} pages ({visited} discovered)...", end='\r')
        text, title = asyncio.run(crawl_website_async(args.input, args.max_pages, args.max_chars, progress))
        print()
        name = title
        description = args.description or f"Knowledge base extracted from {args.input}"
    else:
        if not os.path.exists(args.input):
            print(f"Error: File not found: {args.input}")
            sys.exit(1)
        if not args.input.lower().endswith(".pdf"):
            print("Error: Only PDF files are supported")
            sys.exit(1)
        print(f"Extracting text from: {args.input}")
        text = extract_text_pdf(args.input)
        name = os.path.splitext(os.path.basename(args.input))[0]
        description = args.description or f"Knowledge base extracted from {os.path.basename(args.input)}"

    if not text.strip():
        print("Error: Could not extract any text from input")
        sys.exit(1)

    try:
        generate_skill(name, description, text, args.output)
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
