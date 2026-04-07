"""
企业智能问答助手 - 主入口

提供命令行接口和Skill调用接口
"""

import sys
import os
import time
from typing import Optional

# 添加src目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import get_config
from src.database import DatabaseQuery
from src.knowledge import KnowledgeBase
from src.answer import AnswerGenerator
from src.cache import get_cache, clear_cache
from src.logger import get_logger, init_logger
from src.conversation import get_session, ConversationContext
from src.visualization import (
    visualize_department_stats,
    visualize_performance,
    visualize_project_status,
    format_table,
    format_bar_chart,
    ASCIIGraph,
    StatusBadge
)


class EnterpriseQA:
    """企业智能问答助手主类"""

    def __init__(
        self,
        db_path: Optional[str] = None,
        kb_path: Optional[str] = None,
        session_id: str = "default",
        enable_cache: bool = True,
        log_dir: Optional[str] = None
    ):
        """
        初始化问答助手

        Args:
            db_path: 数据库路径（可选，默认从配置读取）
            kb_path: 知识库路径（可选，默认从配置读取）
            session_id: 会话 ID，用于多轮对话
            enable_cache: 是否启用缓存
            log_dir: 日志目录，None 则只输出到控制台
        """
        self.db_path = db_path
        self.kb_path = kb_path
        self.session_id = session_id
        self.enable_cache = enable_cache
        self._db: Optional[DatabaseQuery] = None
        self._kb: Optional[KnowledgeBase] = None
        self._generator: Optional[AnswerGenerator] = None
        self._context: Optional[ConversationContext] = None

        # 初始化日志
        if log_dir:
            init_logger(log_dir)
        self.logger = get_logger()

        # 加载会话上下文
        self._load_context()

    def _load_context(self):
        """加载会话上下文"""
        self._context = get_session(self.session_id)

        # 如果上下文已过期或为空，重置
        if self._context.is_expired() or not self._context.messages:
            self._context = get_session(self.session_id)
            self.logger.info(f"New session started", session_id=self.session_id)

    @property
    def db(self) -> DatabaseQuery:
        """获取数据库实例（懒加载）"""
        if self._db is None:
            self._db = DatabaseQuery(self.db_path, enable_cache=self.enable_cache)
        return self._db

    @property
    def kb(self) -> KnowledgeBase:
        """获取知识库实例（懒加载）"""
        if self._kb is None:
            self._kb = KnowledgeBase(self.kb_path, enable_cache=self.enable_cache)
        return self._kb

    @property
    def generator(self) -> AnswerGenerator:
        """获取答案生成器实例（懒加载）"""
        if self._generator is None:
            self._generator = AnswerGenerator(self.db, self.kb, self._context)
        return self._generator

    @property
    def context(self) -> ConversationContext:
        """获取会话上下文"""
        return self._context

    def ask(self, question: str, include_history: bool = False) -> str:
        """
        提问

        Args:
            question: 用户问题
            include_history: 是否在回答中包含对话历史摘要

        Returns:
            格式化答案
        """
        start_time = time.time()

        # 记录用户消息
        if self._context:
            self._context.add_user_message(question)

        # 记录开始处理
        self.logger.info(f"Question received", question=question[:50], session_id=self.session_id)

        try:
            # 生成答案
            answer = self.generator.generate(question)

            # 记录助手消息
            if self._context:
                self._context.add_assistant_message(answer)

            # 记录查询日志
            duration_ms = (time.time() - start_time) * 1000
            self.logger.log_query(
                question=question,
                intent=self.generator.last_intent,
                duration_ms=duration_ms,
                result_count=1
            )

            # 如果启用了缓存且需要，显示缓存命中率
            if self.enable_cache:
                cache_stats = get_cache().get_stats()
                if cache_stats["total"] > 5:  # 只有查询足够多时才显示
                    cache_info = f" [缓存命中率: {cache_stats['hit_rate']}%]"
                    # 不追加到答案，只记录到日志

            # 如果请求包含历史，添加历史摘要
            if include_history and self._context and len(self._context.messages) > 2:
                history_summary = self._get_history_summary()
                answer = f"{answer}\n\n---\n{history_summary}"

            return answer

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.log_error(
                error_type=type(e).__name__,
                error_message=str(e),
                question=question
            )
            raise

    def _get_history_summary(self) -> str:
        """获取对话历史摘要"""
        if not self._context or len(self._context.messages) <= 2:
            return ""

        recent = self._context.get_recent_messages(5)
        lines = ["【最近对话】"]
        for msg in recent[-4:]:
            role = "🙋" if msg.role == "user" else "🤖"
            content = msg.content[:40] + "..." if len(msg.content) > 40 else msg.content
            lines.append(f"{role} {content}")

        return "\n".join(lines)

    def get_stats(self) -> dict:
        """获取系统统计信息"""
        stats = {
            "cache": get_cache().get_stats(),
            "session": {
                "session_id": self.session_id,
                "message_count": len(self._context.messages) if self._context else 0,
                "last_entity": self._context.last_entity if self._context else {}
            }
        }
        return stats

    def reset_session(self):
        """重置当前会话"""
        from src.conversation import get_conversation_manager
        get_conversation_manager().delete_session(self.session_id)
        self._context = get_session(self.session_id)
        self.logger.info(f"Session reset", session_id=self.session_id)

    def clear_cache(self):
        """清空缓存"""
        clear_cache()
        self.logger.info("Cache cleared")

    def close(self):
        """关闭连接"""
        if self._db:
            self._db.close()


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python -m src.main \"您的问题\" [session_id]")
        print("示例: python -m src.main \"张三的部门是什么？\"")
        print("多轮对话: python -m src.main \"张三\" my_session")
        sys.exit(1)

    question = sys.argv[1]
    session_id = sys.argv[2] if len(sys.argv) > 2 else "cli"

    # 初始化QA系统
    qa = EnterpriseQA(session_id=session_id)

    try:
        answer = qa.ask(question)
        print("\n" + "=" * 60)
        print(f"问: {question}")
        print("=" * 60)
        print("\n答:\n")
        print(answer)
        print("\n" + "=" * 60)

        # 显示统计信息
        stats = qa.get_stats()
        print(f"\n[缓存命中率: {stats['cache']['hit_rate']}%]")

    finally:
        qa.close()


# Skill调用接口
def handle_question(
    question: str,
    context: Optional[dict] = None,
    session_id: str = "skill"
) -> dict:
    """
    处理问题的接口函数

    Args:
        question: 用户问题
        context: 上下文信息（可选）
        session_id: 会话 ID，用于多轮对话

    Returns:
        dict: {
            "success": bool,
            "answer": str,
            "source": str,
            "stats": dict (包含缓存和会话信息),
            "error": str (如果有)
        }
    """
    # 从 context 获取配置
    session_id = context.get("session_id", session_id) if context else session_id
    enable_cache = context.get("enable_cache", True) if context else True
    log_dir = context.get("log_dir") if context else None

    try:
        qa = EnterpriseQA(
            session_id=session_id,
            enable_cache=enable_cache,
            log_dir=log_dir
        )

        answer = qa.ask(question)
        stats = qa.get_stats()
        qa.close()

        return {
            "success": True,
            "answer": answer,
            "stats": stats,
            "error": None
        }
    except Exception as e:
        logger = get_logger()
        logger.log_error(type(e).__name__, str(e), question)

        return {
            "success": False,
            "answer": None,
            "stats": {},
            "error": str(e)
        }


if __name__ == "__main__":
    main()
