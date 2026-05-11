import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import Optional, List, Set
from urllib.parse import urljoin, urlparse
import re


class WebsiteExtractor:
    def __init__(self, max_pages: int = None, max_chars: int = None):
        self.max_pages = max_pages
        self.max_chars = max_chars
        self.visited: Set[str] = set()
        self.base_path_prefix: str = ""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        self.semaphore = asyncio.Semaphore(10)

    def _get_domain(self, url: str) -> str:
        return urlparse(url).netloc

    def _is_internal_link(self, base_url: str, link: str) -> bool:
        if not link:
            return False
        link = link.strip()
        if link.startswith('#') or link.startswith('mailto:') or link.startswith('tel:') or link.startswith('javascript:'):
            return False
        if link.startswith('http://') or link.startswith('https://'):
            parsed = urlparse(link)
            if parsed.netloc != self._get_domain(base_url):
                return False
            if self.base_path_prefix and not parsed.path.startswith(self.base_path_prefix):
                return False
            return True
        return True

    def _is_under_prefix(self, url: str) -> bool:
        if not self.base_path_prefix:
            return True
        return urlparse(url).path.startswith(self.base_path_prefix)

    def _normalize_url(self, base_url: str, link: str) -> Optional[str]:
        if not link:
            return None
        link = link.strip()
        if not link:
            return None
        try:
            full_url = urljoin(base_url, link)
            parsed = urlparse(full_url)
            path = parsed.path
            if not path or path == '/':
                path = '/'
            path = re.sub(r'/+', '/', path)
            if path.endswith('/') and len(path) > 1:
                path = path[:-1]
            clean_url = f"{parsed.scheme}://{parsed.netloc}{path}"
            if parsed.query:
                clean_url += f"?{parsed.query}"
            return clean_url
        except Exception:
            return None

    def _extract_links(self, base_url: str, html: str) -> List[str]:
        soup = BeautifulSoup(html, 'html.parser')
        links = set()
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if self._is_internal_link(base_url, href):
                clean_url = self._normalize_url(base_url, href)
                if clean_url and clean_url not in self.visited:
                    links.add(clean_url)
        
        for area in soup.find_all('area', href=True):
            href = area['href']
            if self._is_internal_link(base_url, href):
                clean_url = self._normalize_url(base_url, href)
                if clean_url and clean_url not in self.visited:
                    links.add(clean_url)
        
        return list(links)

    def _extract_text_from_html(self, html: str) -> str:
        soup = BeautifulSoup(html, 'html.parser')
        
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript", "meta", "link"]):
            tag.decompose()
        
        for tag in soup.find_all(True):
            if tag.name in ['script', 'style']:
                continue
            if tag.string:
                continue
            text = tag.get_text(separator=' ', strip=True)
            if text:
                tag.string = text
        
        text = soup.get_text(separator='\n')
        
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join([line for line in lines if line])
        
        return text

    async def _fetch_sitemap_urls(self, client: httpx.AsyncClient, base_url: str) -> List[str]:
        parsed = urlparse(base_url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        candidates = [f"{root}/sitemap.xml", f"{root}/sitemap_index.xml"]
        urls = []
        seen_sitemaps: Set[str] = set()

        async def parse_sitemap(sitemap_url: str):
            if sitemap_url in seen_sitemaps:
                return
            seen_sitemaps.add(sitemap_url)
            try:
                resp = await client.get(sitemap_url, headers=self.headers, timeout=15, follow_redirects=True)
                if resp.status_code != 200:
                    return
                soup = BeautifulSoup(resp.text, 'xml')
                # sitemap index — recurse into sub-sitemaps
                for loc in soup.find_all('sitemap'):
                    loc_tag = loc.find('loc')
                    if loc_tag and loc_tag.text.strip():
                        await parse_sitemap(loc_tag.text.strip())
                # regular sitemap
                for loc in soup.find_all('url'):
                    loc_tag = loc.find('loc')
                    if loc_tag and loc_tag.text.strip():
                        page_url = self._normalize_url(base_url, loc_tag.text.strip())
                        if page_url and self._is_under_prefix(page_url):
                            urls.append(page_url)
            except Exception:
                pass

        for c in candidates:
            await parse_sitemap(c)

        return urls

    async def _fetch_page(self, client: httpx.AsyncClient, url: str) -> Optional[tuple]:
        async with self.semaphore:
            try:
                response = await client.get(url, headers=self.headers, timeout=15, follow_redirects=True)
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'text/html' in content_type:
                        return (url, response.text)
            except Exception:
                pass
        return None

    async def crawl_async(self, url: str, progress_callback=None) -> tuple[str, str]:
        self.visited.clear()

        # Set path prefix so crawl stays under the given URL's path
        parsed_start = urlparse(url)
        path = parsed_start.path
        if path and path != '/':
            # e.g. /en/ → keep prefix as /en/
            if not path.endswith('/'):
                path = path.rsplit('/', 1)[0] + '/'
            self.base_path_prefix = path
        else:
            self.base_path_prefix = ""

        pages_text = []
        fetched = 0
        title: Optional[str] = None

        async with httpx.AsyncClient() as client:
            # Seed from sitemap first for complete coverage
            sitemap_urls = await self._fetch_sitemap_urls(client, url)
            if sitemap_urls:
                queue = list(dict.fromkeys([url] + sitemap_urls))  # deduplicated, start URL first
            else:
                queue = [url]

        async with httpx.AsyncClient() as client:
            while queue:
                if self.max_pages and len(self.visited) >= self.max_pages:
                    break

                batch = queue[:20]
                queue = queue[20:]

                tasks = [self._fetch_page(client, u) for u in batch]
                results = await asyncio.gather(*tasks)

                new_links = []
                for result in results:
                    if result:
                        page_url, html = result
                        if page_url in self.visited:
                            continue
                        self.visited.add(page_url)
                        fetched += 1

                        # Extract title from the start URL's HTML — no extra HTTP request needed
                        if title is None and page_url == url:
                            soup = BeautifulSoup(html, 'html.parser')
                            tag = soup.find('title')
                            title = tag.text.strip() if tag else None

                        text = self._extract_text_from_html(html)
                        if text.strip():
                            pages_text.append(f"=== {page_url} ===\n{text}\n")

                        links = self._extract_links(page_url, html)
                        for link in links:
                            if link not in self.visited:
                                if link not in queue and link not in new_links:
                                    new_links.append(link)

                        if progress_callback:
                            progress_callback(fetched, len(self.visited))

                queue.extend(new_links)

        full_text = '\n'.join(pages_text)

        if self.max_chars and len(full_text) > self.max_chars:
            full_text = full_text[:self.max_chars] + "\n\n... (truncated)"

        return full_text, title or url

    @staticmethod
    def extract_text(url: str, max_pages: int = None, max_chars: int = None, progress_callback=None) -> tuple[str, str]:
        extractor = WebsiteExtractor(max_pages=max_pages, max_chars=max_chars)
        return asyncio.run(extractor.crawl_async(url, progress_callback))
    
