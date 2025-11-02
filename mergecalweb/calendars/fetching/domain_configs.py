"""
Encrypted configuration for calendar sources that require special handling.

This module stores encrypted domain-specific configurations for calendar sources
that need custom headers or other special handling. The configurations are encrypted
to protect user privacy in the public codebase.

Configuration is encrypted using Fernet symmetric encryption. The encryption key
must be provided via the CALENDAR_CONFIG_KEY environment variable.

Each encrypted config is a JSON object with the following structure:
{
    "domain": "example.com",
    "user_agent": "Custom User Agent",  # optional
    "accept": "text/calendar",  # optional
    "additional_headers": {"Header-Name": "value"},  # optional
    "notes": "Why this config is needed"  # optional, for documentation
}
"""

import json
import logging
import os
from typing import Any

from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken

logger = logging.getLogger(__name__)

# Encrypted domain configurations
# Each entry is an encrypted JSON object containing domain and header overrides
ENCRYPTED_CONFIGS: list[str] = [
    "gAAAAABpBtM8JKCSEohrD570Bvn-AQj8OtxDqfKtAOvKfFbnKzadSjqJLsdW0ezyIOPDYmoxdpvkR1MV3HvZSJfQgapZTPWwyMxytZai-I6k8Ma9Ul6GHmdukMvFw15W0pbO44EDXPC9h3GzwMAqk8EGX0GmosQTYquVO5ITm5NggKkAopBqKUn_DWZpGHqrawj7Ll3BuhVx7-8MAJPGk7bI8FxntKxi6P20k8kDkcf2Zv9XUOiRQzYR8C8Yrq0V4V7K29xd-RHoLif7Wti6d0yd9yVQoUP46xgXYLYaz0QYy3FACP5lzQii1DzJzUvwtdgwar6Lk5mecLAqjy93wUVrDVuuucZFue5-0VAN2VJ5U6XqmIqPoCOXc1Zzxk46lVDe6MgLQ1-MbxVzYAYblcMn0BPW8hoiOe4T_1H80-yX6sp5kFO2GVlKW8B42Jdu47hWv0xBPK0z",
]


def _get_encryption_key() -> bytes | None:
    """Get the encryption key from environment variable."""
    key = os.environ.get("CALENDAR_CONFIG_KEY")
    if not key:
        return None
    return key.encode()


def _decrypt_configs() -> dict[str, dict[str, Any]]:
    """
    Decrypt all domain configurations.

    Returns:
        Dictionary mapping domain names to their configuration overrides.
        Returns empty dict if decryption fails or no key is available.
    """
    key = _get_encryption_key()
    if not key:
        logger.warning(
            "CALENDAR_CONFIG_KEY not set, domain-specific configs unavailable",
            extra={"event": "calendar_config_key_missing"},
        )
        return {}

    if not ENCRYPTED_CONFIGS:
        logger.debug(
            "No encrypted domain configs defined",
            extra={"event": "calendar_config_empty"},
        )
        return {}

    configs = {}
    fernet = Fernet(key)

    for i, encrypted_blob in enumerate(ENCRYPTED_CONFIGS):
        try:
            decrypted_data = fernet.decrypt(encrypted_blob.encode())
            config = json.loads(decrypted_data)
            domain = config.pop("domain")
            configs[domain] = config
            logger.debug(
                "Loaded config for domain (index %d)",
                i,
                extra={"event": "calendar_config_loaded", "config_index": i},
            )
        except InvalidToken:
            logger.exception(
                "Failed to decrypt config at index %d - invalid key",
                i,
                extra={"event": "calendar_config_decrypt_error", "config_index": i},
            )
        except (json.JSONDecodeError, KeyError):
            logger.exception(
                "Failed to parse config at index %d",
                i,
                extra={
                    "event": "calendar_config_parse_error",
                    "config_index": i,
                },
            )
        except Exception:
            logger.exception(
                "Unexpected error loading config at index %d",
                i,
                extra={
                    "event": "calendar_config_error",
                    "config_index": i,
                },
            )

    logger.info(
        "Loaded %d domain-specific calendar configurations",
        len(configs),
        extra={"event": "calendar_configs_loaded", "count": len(configs)},
    )
    return configs


# Cache decrypted configs at module load time
_DOMAIN_CONFIGS = _decrypt_configs()


def get_domain_config(domain: str) -> dict[str, Any]:
    """
    Get configuration overrides for a specific domain.

    Args:
        domain: The domain name (e.g., 'example.com')

    Returns:
        Dictionary of configuration overrides, or empty dict if no config exists.
    """
    return _DOMAIN_CONFIGS.get(domain, {})
