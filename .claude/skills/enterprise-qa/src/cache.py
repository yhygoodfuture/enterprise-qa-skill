"""
缓存模块

提供查询结果缓存功能，减少重复数据库/知识库查询
"""

import time
import hashlib
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass
from threading import Lock


@dataclass
class CacheEntry:
    """缓存条目"""
    value: Any
    timestamp: float
    ttl: float  # 生存时间（秒）


class Cache:
    """简单的内存缓存，支持 TTL"""

    def __init__(self, default_ttl: float = 300.0):
        """
        Args:
            default_ttl: 默认缓存生存时间（秒），默认 5 分钟
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self.default_ttl = default_ttl
        self._hits = 0
        self._misses = 0

    def _generate_key(self, namespace: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = f"{namespace}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, namespace: str, *args, **kwargs) -> Optional[Any]:
        """
        获取缓存值

        Args:
            namespace: 缓存命名空间（如 'db', 'kb'）
            *args, **kwargs: 缓存键参数

        Returns:
            缓存值，如果不存在或已过期则返回 None
        """
        key = self._generate_key(namespace, *args, **kwargs)

        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]
            if time.time() - entry.timestamp > entry.ttl:
                # 缓存已过期
                del self._cache[key]
                self._misses += 1
                return None

            self._hits += 1
            return entry.value

    def set(self, namespace: str, value: Any, ttl: Optional[float] = None, *args, **kwargs):
        """
        设置缓存值

        Args:
            namespace: 缓存命名空间
            value: 缓存值
            ttl: 生存时间（秒），None 则使用默认值
            *args, **kwargs: 缓存键参数
        """
        key = self._generate_key(namespace, *args, **kwargs)
        ttl = ttl if ttl is not None else self.default_ttl

        with self._lock:
            self._cache[key] = CacheEntry(
                value=value,
                timestamp=time.time(),
                ttl=ttl
            )

    def invalidate(self, namespace: str, *args, **kwargs):
        """使缓存失效"""
        key = self._generate_key(namespace, *args, **kwargs)
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self, namespace: Optional[str] = None):
        """
        清空缓存

        Args:
            namespace: 如果指定，只清空该命名空间；否则清空所有
        """
        with self._lock:
            if namespace is None:
                self._cache.clear()
            else:
                # 清空指定命名空间的缓存
                keys_to_delete = [
                    k for k, v in self._cache.items()
                    if k.startswith(namespace + ":")
                ]
                for k in keys_to_delete:
                    del self._cache[k]

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "total": total,
            "hit_rate": round(hit_rate * 100, 2),
            "entries": len(self._cache)
        }


# 全局缓存实例
_cache: Optional[Cache] = None


def get_cache() -> Cache:
    """获取全局缓存实例"""
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache


def clear_cache():
    """清空全局缓存"""
    get_cache().clear()