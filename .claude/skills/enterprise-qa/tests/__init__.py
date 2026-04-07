"""
测试模块
"""

import pytest
import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import Config
from src.database import DatabaseQuery, QueryType
from src.knowledge import KnowledgeBase
from src.intention import IntentRecognizer, QueryIntent
from src.answer import AnswerGenerator


# 测试配置
TEST_DB_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "..",
    "..",
    "enterprise-qa-data",
    "enterprise.db"
)

TEST_KB_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "..",
    "..",
    "enterprise-qa-data",
    "knowledge"
)


@pytest.fixture
def config():
    """测试配置fixture"""
    cfg = Config()
    cfg.db_path = TEST_DB_PATH
    cfg.kb_path = TEST_KB_PATH
    return cfg


@pytest.fixture
def db():
    """数据库fixture"""
    database = DatabaseQuery(TEST_DB_PATH)
    yield database
    database.close()


@pytest.fixture
def kb():
    """知识库fixture"""
    return KnowledgeBase(TEST_KB_PATH)


@pytest.fixture
def intent_recognizer(db, kb):
    """意图识别器fixture"""
    return IntentRecognizer(db, kb)


@pytest.fixture
def answer_generator(db, kb):
    """答案生成器fixture"""
    return AnswerGenerator(db, kb)
