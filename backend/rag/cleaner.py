import re

def clean_extracted_text(text: str) -> str:
    """
    Cleans plain text before chunking:
    - Standardizes line breaks and collapses duplicate blank lines (max 2 newlines)
    - Trims leading/trailing line spacing
    - Collapses multiple horizontal spaces or tabs to a single space
    - Strips common boilerplate lines if they repeat heavily (like menu structures)
    - Preserves semantic paragraph structures and heading sections
    """
    if not text:
        return ""
        
    # Split text into lines to perform line-by-line normalization
    raw_lines = text.splitlines()
    clean_lines = []
    
    seen_lines = set()
    for line in raw_lines:
        trimmed = re.sub(r'\s+', ' ', line).strip()
        
        # Skip empty lines
        if not trimmed:
            clean_lines.append("")
            continue
            
        # Strip extremely obvious boilerplate single words or buttons that slip through
        # (e.g., "Home", "Skip to content", "Sign Up", "Log In", "Search...")
        lower_line = trimmed.lower()
        if lower_line in (
            "skip to content", "home", "search", "menu", "sign up", "sign in",
            "log in", "login", "register", "privacy policy", "terms of service",
            "contact us", "cookies", "accept", "decline", "navigation", "nav"
        ):
            continue
            
        # Basic line deduplication for adjacent identical lines to prevent scraper loop noise
        if len(clean_lines) > 0 and clean_lines[-1] == trimmed:
            continue
            
        clean_lines.append(trimmed)
        
    # Join and normalize consecutive empty lines (collapsing multiple empty lines to one)
    normalized_text = "\n".join(clean_lines)
    normalized_text = re.sub(r'\n{3,}', '\n\n', normalized_text)
    
    # Strip any extra leading/trailing spacing from final text string
    return normalized_text.strip()
