from urllib.parse import urlparse
import socket
import ipaddress

def is_safe_url(url: str) -> bool:
    """
    Validates a URL to prevent Server-Side Request Forgery (SSRF) and scheme exploits.
    - Scheme must be http or https
    - Hostname must resolve to a valid IP address
    - IP address must NOT be in loopback, private, link-local, multicast, or unspecified ranges
    """
    try:
        parsed = urlparse(url)
        
        # Enforce scheme
        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https"):
            return False
            
        host = parsed.hostname
        if not host:
            return False
            
        # Down-score obvious internal docker names or non-fqdn names without dot (except localhost which is blocked below)
        if '.' not in host and host != 'localhost':
            # Block internal Docker services (e.g. 'db', 'redis', 'searxng', 'qdrant')
            return False
            
        # Resolve hostname to all associated IPs
        try:
            addr_info = socket.getaddrinfo(host, None)
        except socket.gaierror:
            # DNS lookup failed
            return False
            
        for family, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                continue
                
            # Check for SSRF-vulnerable IP scopes
            if (
                ip.is_loopback        # e.g., 127.0.0.1, ::1
                or ip.is_private      # e.g., 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, fc00::/7
                or ip.is_link_local   # e.g., 169.254.0.0/16, fe80::/10
                or ip.is_multicast    # e.g., 224.0.0.0/4, ff00::/8
                or ip.is_unspecified  # e.g., 0.0.0.0, ::
            ):
                return False
                
        return True
    except Exception as e:
        print(f"SSRF URL safety verification failed for {url}: {e}")
        return False
