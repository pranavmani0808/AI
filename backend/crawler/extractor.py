from bs4 import BeautifulSoup
import re
from typing import Dict, Any

def extract_clean_content(html_content: str) -> Dict[str, Any]:
    """
    Parses HTML content using BeautifulSoup and strips page boilerplate.
    - Removes scripts, styles, noscript, nav, header, footer, aside, form tags
    - Extracts title and meta description (if present)
    - Normalizes line breaks and whitespace
    - Returns clean dictionary text
    """
    result = {
        "title": "",
        "description": "",
        "text": "",
        "word_count": 0,
        "success": False,
        "error": None
    }
    
    try:
        # Use lxml parser for performance and reliability
        soup = BeautifulSoup(html_content, "lxml")
        
        # 1. Extract Title
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            result["title"] = title_tag.string.strip()
            
        # 2. Extract Description Meta tag
        desc_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        if desc_tag and desc_tag.get("content"):
            result["description"] = desc_tag.get("content").strip()
            
        # 3. Strip useless tags from tree
        for tag in soup(["script", "style", "noscript", "iframe", "svg", "nav", "header", "footer", "aside", "form", "select", "button"]):
            tag.decompose()
            
        # 4. Extract Text
        # Keep headings and paragraphs separated by newlines
        text_blocks = []
        for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li"]):
            element_text = element.get_text().strip()
            if element_text:
                text_blocks.append(element_text)
                
        # Fallback to general text if no semantic tags are found
        if not text_blocks:
            raw_text = soup.get_text()
            text_blocks = [line.strip() for line in raw_text.splitlines() if line.strip()]
            
        # Join block texts with double newlines
        clean_text = "\n\n".join(text_blocks)
        
        # Clean extra spaces inside paragraphs
        clean_text = re.sub(r'[ \t]+', ' ', clean_text)
        clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
        
        result["text"] = clean_text.strip()
        result["word_count"] = len(result["text"].split())
        result["success"] = True
        
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
        
    return result
