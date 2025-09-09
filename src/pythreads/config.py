# SPDX-FileCopyrightText: 2024-present Marc Love <copyright@marclove.com>
#
# SPDX-License-Identifier: MIT

import os
from typing import Tuple

try:
    from dotenv import load_dotenv
except Exception:  # fallback if python-dotenv isn't available
    def load_dotenv(*args, **kwargs) -> bool:  # type: ignore[misc]
        return False


class Config:
    """Centralized configuration manager for PyThreads.
    
    Handles loading and caching of environment variables with validation.
    """
    
    def __init__(self) -> None:
        load_dotenv()
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from environment variables."""
        # OAuth/API Configuration
        self.app_id = os.getenv("THREADS_APP_ID")
        self.api_secret = os.getenv("THREADS_API_SECRET") 
        self.redirect_uri = os.getenv("THREADS_REDIRECT_URI")
        
        # API Configuration
        self.graph_api_version = os.getenv("THREADS_GRAPH_API_VERSION")
        self.graph_api_base_url = (
            f"https://graph.threads.net/{self.graph_api_version}/"
            if self.graph_api_version
            else "https://graph.threads.net/"
        )
        
        # SSL Configuration
        self.ssl_cert_filepath = os.getenv("THREADS_SSL_CERT_FILEPATH", "")
        self.ssl_key_filepath = os.getenv("THREADS_SSL_KEY_FILEPATH", "")
    
    def get_ssl_credentials(self) -> Tuple[str, str] | None:
        """Get SSL certificate and key file paths if both are configured."""
        # Read fresh from environment for testing compatibility
        cert = os.getenv("THREADS_SSL_CERT_FILEPATH", "")
        key = os.getenv("THREADS_SSL_KEY_FILEPATH", "")
        if cert and key:
            return (cert, key)
        return None
    
    def validate_oauth_config(self) -> None:
        """Validate that required OAuth configuration is present."""
        if not self.app_id:
            raise ValueError("must define an THREADS_APP_ID env variable")
        if not self.api_secret:
            raise ValueError("must define an THREADS_API_SECRET env variable")
        if not self.redirect_uri:
            raise ValueError("must define an THREADS_REDIRECT_URI env variable")


# Global config instance
config = Config()