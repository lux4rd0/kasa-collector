import time
import socket
import asyncio
from typing import Dict, Optional
import logging
from config import Config

type CacheEntry = tuple[str, float]  # (hostname, timestamp)
type CacheStats = dict[str, int | float]

logger = logging.getLogger(__name__)


class DNSCache:
    """
    DNS cache implementation with TTL support for hostname resolution.
    Prevents repeated DNS lookups for the same IP addresses.
    """

    def __init__(self, ttl_seconds: Optional[int] = None):  # Use config default TTL
        if ttl_seconds is None:
            ttl_seconds = Config.KASA_COLLECTOR_DNS_CACHE_TTL
        self.cache: Dict[str, CacheEntry] = {}
        self.ttl_seconds = ttl_seconds
        self._lock = asyncio.Lock()

    async def get_hostname(self, ip: str) -> str:
        """
        Get hostname for IP address with caching.
        Returns cached value if available and not expired, otherwise performs lookup.
        """
        current_time = time.time()

        async with self._lock:
            # Check cache first
            if ip in self.cache:
                hostname, timestamp = self.cache[ip]
                if current_time - timestamp < self.ttl_seconds:
                    logger.debug(f"DNS cache hit for {ip}: {hostname}")
                    return hostname
                else:
                    # Expired entry, remove it
                    del self.cache[ip]
                    logger.debug(f"DNS cache expired for {ip}")

        # Cache miss or expired, perform lookup
        try:
            loop = asyncio.get_running_loop()
            hostname = await loop.run_in_executor(None, socket.getfqdn, ip)

            async with self._lock:
                self.cache[ip] = (hostname, current_time)
                logger.debug(f"DNS cache stored for {ip}: {hostname}")

            return hostname

        except Exception as e:
            logger.warning(f"DNS lookup failed for {ip}: {e}")
            return ip  # Return IP as fallback

    async def clear_expired(self):
        """
        Remove expired entries from cache.
        """
        current_time = time.time()
        expired_keys = []

        async with self._lock:
            for ip, (hostname, timestamp) in self.cache.items():
                if current_time - timestamp >= self.ttl_seconds:
                    expired_keys.append(ip)

            for key in expired_keys:
                del self.cache[key]

        if expired_keys:
            logger.debug(f"Cleared {len(expired_keys)} expired DNS cache entries")

    def get_cache_stats(self) -> CacheStats:
        """
        Get cache statistics using modern type annotations.
        """
        current_time = time.time()
        expired_count = sum(
            1
            for _, timestamp in self.cache.values()
            if current_time - timestamp >= self.ttl_seconds
        )

        return {
            "total_entries": len(self.cache),
            "expired_entries": expired_count,
            "active_entries": len(self.cache) - expired_count,
            "ttl_seconds": self.ttl_seconds,
            "cache_hit_rate": getattr(self, "_hit_rate", 0.0),
        }


# Global DNS cache instance
_dns_cache: Optional[DNSCache] = None


def get_dns_cache() -> DNSCache:
    """
    Get the global DNS cache instance.
    """
    global _dns_cache
    if _dns_cache is None:
        _dns_cache = DNSCache()
    return _dns_cache


async def get_hostname_cached(ip: str) -> str:
    """
    Convenience function to get hostname with caching.
    """
    cache = get_dns_cache()
    return await cache.get_hostname(ip)
