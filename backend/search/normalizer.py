from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

def normalize_url(url: str) -> str:
    """
    Standardize a URL to prevent duplicate crawls of the same logical page.
    - Lowers hostnames
    - Removes fragments (#section)
    - Removes common tracking query parameters (utm_*, fbclid, etc.)
    - Removes trailing slashes for directory index consistency
    """
    try:
        parsed = urlparse(url.strip())
        
        # Lowercase scheme and netloc (host)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        
        # Remove trailing slash in path if it's not the root path
        path = parsed.path
        if len(path) > 1 and path.endswith('/'):
            path = path.rstrip('/')
            
        # Parse query params and filter tracking/analytics tokens
        ignored_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 
            'utm_content', 'utm_term', 'fbclid', 'gclid', 'msclkid'
        }
        
        query_params = parse_qsl(parsed.query)
        filtered_params = [
            (k, v) for k, v in query_params if k.lower() not in ignored_params
        ]
        
        # Re-encode query, sorting parameters alphabetically for consistency
        filtered_params.sort(key=lambda x: x[0])
        query = urlencode(filtered_params) if filtered_params else ''
        
        # Re-assemble URL without fragment
        normalized = urlunparse((scheme, netloc, path, parsed.params, query, ''))
        return normalized
    except Exception as e:
        print(f"URL normalization failed for {url}: {e}")
        return url
