    def _get_domain_and_page(self) -> tuple:
        """Extract domain and page from current URL - always fetch live from browser"""
        if not self.page:
            return None, None
        
        try:
            # Always get current URL from the live page
            current_url = self.page.url
            if not current_url:
                return None, None
            
            # Extract domain
            domain = current_url.replace('https://', '').replace('http://', '').split('/')[0].split('#')[0]
            
            # Extract page name
            import re
            match = re.search(r'/#/(\w+)', current_url)
            if match:
                page = match.group(1)
            else:
                page = "home"
            
            return domain, page
        except Exception as e:
            logger.warning(f"Error getting domain/page: {e}")
            return None, None

