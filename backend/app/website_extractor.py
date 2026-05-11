import httpx
from bs4 import BeautifulSoup
from typing import Optional


class WebsiteExtractor:
    @staticmethod
    def extract_text(url: str, max_chars: int = 50000) -> str:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Get text
            text = soup.get_text(separator='\n')
            
            # Clean up whitespace
            lines = [line.strip() for line in text.split('\n')]
            text = '\n'.join([line for line in lines if line])
            
            # Limit to max_chars
            if len(text) > max_chars:
                text = text[:max_chars] + "..."
            
            return text
        except Exception as e:
            raise ValueError(f"Failed to extract from website: {str(e)}")
    
    @staticmethod
    def get_title(url: str) -> Optional[str]:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = httpx.get(url, headers=headers, timeout=10, follow_redirects=True)
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.find('title')
            return title.text.strip() if title else None
        except:
            return None