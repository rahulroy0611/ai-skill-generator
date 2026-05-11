import argparse
import json
import os
import re
import sys
import asyncio
import tempfile
from datetime import datetime

import pdfplumber
import httpx
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from urllib.parse import urlparse

EMBED_MODEL_NAME = os.environ.get("EMBED_MODEL_NAME", "all-MiniLM-L6-v2")


def extract_text_pdf(file_path: str) -> str:
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


def chunk_text(text: str, chunk_size: int = 500) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += " " + sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks


def extract_title(url: str) -> str:
    try:
        response = httpx.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10, follow_redirects=True)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find('title')
        return title.text.strip() if title else urlparse(url).netloc
    except Exception:
        return urlparse(url).netloc


def extract_text_html(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript", "meta", "link"]):
        tag.decompose()
    text = soup.get_text(separator='\n')
    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join([line for line in lines if line])


def is_internal_link(base_url: str, link: str, base_path_prefix: str = "") -> bool:
    if not link or link.startswith('#') or link.startswith('mailto:') or link.startswith('tel:'):
        return False
    link = link.strip()
    if link.startswith('http://') or link.startswith('https://'):
        parsed = urlparse(link)
        if parsed.netloc != urlparse(base_url).netloc:
            return False
        if base_path_prefix and not parsed.path.startswith(base_path_prefix):
            return False
        return True
    return True


def normalize_url(base_url: str, link: str) -> str:
    from urllib.parse import urljoin
    if not link:
        return None
    link = link.strip()
    try:
        full_url = urljoin(base_url, link)
        parsed = urlparse(full_url)
        path = re.sub(r'/+', '/', parsed.path.rstrip('/')) or '/'
        clean_url = f"{parsed.scheme}://{parsed.netloc}{path}"
        if parsed.query:
            clean_url += f"?{parsed.query}"
        return clean_url
    except Exception:
        return None


async def crawl_website_async(url: str, max_pages: int = None, max_chars: int = None, progress_callback=None):
    visited = set()
    pages_text = []
    fetched = 0
    semaphore = asyncio.Semaphore(10)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    parsed_start = urlparse(url)
    base_path_prefix = ""
    path = parsed_start.path
    if path and path != '/':
        if not path.endswith('/'):
            path = path.rsplit('/', 1)[0] + '/'
        base_path_prefix = path

    async def fetch_page(client, u):
        async with semaphore:
            try:
                response = await client.get(u, headers=headers, timeout=15, follow_redirects=True)
                if response.status_code == 200 and 'text/html' in response.headers.get('content-type', ''):
                    return u, response.text
            except Exception:
                pass
        return None

    queue = [url]

    async with httpx.AsyncClient() as client:
        while queue:
            if max_pages and len(visited) >= max_pages:
                break

            batch = queue[:20]
            queue = queue[20:]

            tasks = [fetch_page(client, u) for u in batch]
            results = await asyncio.gather(*tasks)

            new_links = []
            for result in results:
                if result:
                    page_url, html = result
                    if page_url in visited:
                        continue
                    visited.add(page_url)
                    fetched += 1

                    text = extract_text_html(html)
                    if text.strip():
                        pages_text.append(f"=== {page_url} ===\n{text}\n")

                    soup = BeautifulSoup(html, 'html.parser')
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        if is_internal_link(page_url, href, base_path_prefix):
                            clean = normalize_url(page_url, href)
                            if clean and clean not in visited and clean not in queue and clean not in new_links:
                                new_links.append(clean)

                    if progress_callback:
                        progress_callback(fetched, len(visited))

            queue.extend(new_links)

    full_text = '\n'.join(pages_text)
    if max_chars and len(full_text) > max_chars:
        full_text = full_text[:max_chars] + "\n\n... (truncated)"

    return full_text, extract_title(url)


def generate_skill(name: str, text: str, output_dir: str = "output"):
    print(f"Loading embedding model: {EMBED_MODEL_NAME}")
    model = SentenceTransformer(EMBED_MODEL_NAME)

    if not text.strip():
        print("Error: No text content extracted")
        sys.exit(1)

    print(f"Extracted {len(text)} characters")
    print("Generating chunks...")
    chunks = chunk_text(text)
    print(f"Created {len(chunks)} chunks")

    print("Generating embeddings...")
    embeddings = model.encode(chunks, convert_to_numpy=True).tolist()

    safe_name = re.sub(r'[^\w\-_. ]', '_', name)
    skill_dir = os.path.join(output_dir, f"{safe_name}_skills")
    os.makedirs(skill_dir, exist_ok=True)

    skill_data = {
        "name": name,
        "type": "rag",
        "generated": datetime.now().isoformat(),
        "chunks": [{"index": i, "content": chunk, "embedding": emb} for i, (chunk, emb) in enumerate(zip(chunks, embeddings))]
    }

    md_content = f"# {name}\n\n" + "\n\n---\n\n".join(chunks)
    with open(os.path.join(skill_dir, f"{safe_name}.md"), "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"  Created: {safe_name}.md")

    with open(os.path.join(skill_dir, f"{safe_name}.json"), "w", encoding="utf-8") as f:
        json.dump(skill_data, f, indent=2)
    print(f"  Created: {safe_name}.json")

    skill_text = f"""SKILL METADATA
============
name: {name}
type: rag
generated: {datetime.now().isoformat()}

KNOWLEDGE BASE (with embeddings)
============
"""
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        skill_text += f"\n---
CHUNK #{i+1}
EMBEDDING: {json.dumps(emb)}
---
{chunk}\n"

    with open(os.path.join(skill_dir, f"{safe_name}.skill"), "w", encoding="utf-8") as f:
        f.write(skill_text)
    print(f"  Created: {safe_name}.skill")

    print(f"\nSkill files generated in: {skill_dir}")
    return skill_dir


def main():
    parser = argparse.ArgumentParser(description="AI Skill Generator CLI - Convert PDFs or URLs to AI skills")
    parser.add_argument("input", help="Path to PDF file or URL to crawl")
    parser.add_argument("-o", "--output", default="output", help="Output directory (default: output)")
    parser.add_argument("-m", "--max-pages", type=int, default=None, help="Max pages to crawl for URLs (default: unlimited)")
    parser.add_argument("-c", "--max-chars", type=int, default=None, help="Max characters to extract (default: unlimited)")

    args = parser.parse_args()

    is_url = args.input.startswith(("http://", "https://"))

    if is_url:
        print(f"Extracting content from URL: {args.input}")
        def progress(fetched, visited):
            print(f"  Crawled {fetched} pages, discovered {visited} links...", end='\r')
        text, title = asyncio.run(crawl_website_async(args.input, args.max_pages, args.max_chars, progress))
        print()
        name = title
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

    if not text.strip():
        print("Error: Could not extract text from input")
        sys.exit(1)

    try:
        generate_skill(name, text, args.output)
    except KeyboardInterrupt:
        print("\nCancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()