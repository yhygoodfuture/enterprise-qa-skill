"""
多轮对话模块

支持上下文感知的连续对话
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class Message:
    """对话消息"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """对话上下文"""
    session_id: str
    messages: List[Message] = field(default_factory=list)
    last_entity: Dict[str, Any] = field(default_factory=dict)  # 记住上一轮提到的实体
    last_intent: str = ""
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)

    def add_user_message(self, content: str, metadata: Dict[str, Any] = None):
        """添加用户消息"""
        self.messages.append(Message(
            role="user",
            content=content,
            timestamp=time.time(),
            metadata=metadata or {}
        ))
        self.last_active = time.time()

    def add_assistant_message(self, content: str, metadata: Dict[str, Any] = None):
        """添加助手消息"""
        self.messages.append(Message(
            role="assistant",
            content=content,
            timestamp=time.time(),
            metadata=metadata or {}
        ))
        self.last_active = time.time()

    def update_entity(self, entities: Dict[str, Any]):
        """更新上下文中的实体"""
        self.last_entity.update(entities)

    def get_recent_messages(self, count: int = 5) -> List[Message]:
        """获取最近的消息"""
        return self.messages[-count:]

    def is_expired(self, ttl: float = 1800.0) -> bool:
        """检查对话是否过期（默认 30 分钟）"""
        return time.time() - self.last_active > ttl


class ConversationManager:
    """对话管理器"""

    def __init__(self, max_sessions: int = 100, ttl: float = 1800.0):
        """
        Args:
            max_sessions: 最大会话数，超过则清理最旧的会话
            ttl: 会话过期时间（秒），默认 30 分钟
        """
        self._sessions: Dict[str, ConversationContext] = {}
        self._lock = Lock()
        self.max_sessions = max_sessions
        self.ttl = ttl

    def get_or_create_session(self, session_id: str) -> ConversationContext:
        """获取或创建会话"""
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = ConversationContext(session_id=session_id)
                self._cleanup_expired()
            else:
                # 更新 last_active
                self._sessions[session_id].last_active = time.time()

            return self._sessions[session_id]

    def get_session(self, session_id: str) -> Optional[ConversationContext]:
        """获取会话，不存在则返回 None"""
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str):
        """删除会话"""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]

    def _cleanup_expired(self):
        """清理过期的会话"""
        # 如果会话数超限，删除最旧的
        if len(self._sessions) > self.max_sessions:
            sorted_sessions = sorted(
                self._sessions.items(),
                key=lambda x: x[1].last_active
            )
            # 删除最旧的 10%
            to_delete = max(1, len(sorted_sessions) // 10)
            for session_id, _ in sorted_sessions[:to_delete]:
                del self._sessions[session_id]

        # 删除过期的会话
        expired = [
            sid for sid, ctx in self._sessions.items()
            if ctx.is_expired(self.ttl)
        ]
        for sid in expired:
            del self._sessions[sid]

    def get_active_sessions(self) -> List[str]:
        """获取活跃会话 ID 列表"""
        self._cleanup_expired()
        return list(self._sessions.keys())


# 全局会话管理器
_conversation_manager: Optional[ConversationManager] = None


def get_conversation_manager() -> ConversationManager:
    """获取全局会话管理器"""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager


def get_session(session_id: str = "default") -> ConversationContext:
    """获取会话上下文"""
    return get_conversation_manager().get_or_create_session(session_id)