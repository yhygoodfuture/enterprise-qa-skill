"""
企业智能问答助手 - 测试模块
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


class TestDatabaseQuery:
    """数据库查询测试"""

    def test_get_employee_by_name(self, db):
        """T01: 测试查询员工部门"""
        result = db.get_employee_by_name("张三")
        assert result.success is True
        assert result.data['department'] == '研发部'
        assert result.source == 'employees 表'

    def test_get_employee_manager(self, db):
        """T02: 测试查询员工上级"""
        result = db.get_employee_manager("李四")
        assert result.success is True
        assert 'CEO' in result.data['name']

    def test_get_employee_projects(self, db):
        """T05: 测试查询员工项目"""
        result = db.get_employee_projects("张三")
        assert result.success is True
        # 张三参与了4个项目
        assert len(result.data) == 4

    def test_get_department_count(self, db):
        """T06: 测试查询部门人数"""
        result = db.get_department_count("研发部")
        assert result.success is True
        assert result.data['count'] == 4

    def test_get_employee_attendance(self, db):
        """T08: 测试查询员工考勤"""
        result = db.get_employee_attendance("张三", 2026, 2)
        assert result.success is True
        assert result.data['late_count'] == 2

    def test_get_nonexistent_employee(self, db):
        """T09: 测试查询不存在的员工"""
        result = db.get_employee_by_name("不存在的员工")
        assert result.success is False
        assert "未找到" in result.message

    def test_check_promotion_eligibility(self, db):
        """T07: 测试晋升条件检查"""
        result = db.check_promotion_eligibility("王五", "P5", "P6")
        assert result.success is True
        assert result.data['name'] == '王五'
        assert result.data['current_level'] == 'P5'

    def test_sql_injection_prevention(self, db):
        """T11: 测试SQL注入防护"""
        # 测试常见SQL注入模式
        malicious_queries = [
            "1' OR '1'='1",
            "'; DROP TABLE users;--",
            "admin'--",
        ]
        for query in malicious_queries:
            result = db.get_employee_by_name(query)
            assert result.success is False
            assert "无效字符" in result.message or "SQL" in result.message


class TestKnowledgeBase:
    """知识库测试"""

    def test_kb_initialization(self, kb):
        """测试知识库初始化"""
        assert kb is not None
        assert len(kb._index) > 0

    def test_search(self, kb):
        """测试知识库搜索"""
        results = kb.search("年假")
        assert len(results) > 0

    def test_get_hr_policy(self, kb):
        """T03/T04: 测试获取HR政策"""
        result = kb.get_hr_policy("年假")
        assert result is not None
        assert result.success is True
        assert "年假" in result.content

    def test_get_promotion_rules(self, kb):
        """测试获取晋升规则"""
        result = kb.get_promotion_rules("P5", "P6")
        assert result is not None

    def test_get_meeting_notes(self, kb):
        """测试获取会议纪要"""
        results = kb.get_meeting_notes()
        assert len(results) > 0


class TestIntentRecognition:
    """意图识别测试"""

    def test_recognize_db_query(self, intent_recognizer):
        """测试识别数据库查询"""
        result = intent_recognizer.recognize("张三的部门是什么")
        assert result.db_query_needed is True
        assert result.kb_query_needed is False

    def test_recognize_kb_query(self, intent_recognizer):
        """测试识别知识库查询"""
        result = intent_recognizer.recognize("年假怎么计算")
        assert result.db_query_needed is False
        assert result.kb_query_needed is True

    def test_recognize_mixed_query(self, intent_recognizer):
        """测试识别混合查询"""
        result = intent_recognizer.recognize("王五符合晋升条件吗")
        assert result.db_query_needed is True
        assert result.kb_query_needed is True

    def test_recognize_sql_injection(self, intent_recognizer):
        """T11: 测试识别SQL注入"""
        result = intent_recognizer.recognize("1' OR '1'='1")
        assert "error" in result.entities
        assert result.entities["error"] == "sql_injection"


class TestAnswerGeneration:
    """答案生成测试"""

    def test_t01_department_query(self, answer_generator):
        """T01: 张三的部门是什么？"""
        answer = answer_generator.generate("张三的部门是什么？")
        assert "研发部" in answer
        assert "来源" in answer

    def test_t02_manager_query(self, answer_generator):
        """T02: 李四的上级是谁？"""
        answer = answer_generator.generate("李四的上级是谁？")
        assert "CEO" in answer or "EMP-000" in answer

    def test_t03_annual_leave_query(self, answer_generator):
        """T03: 年假怎么计算？"""
        answer = answer_generator.generate("年假怎么计算？")
        assert "5天" in answer or "年假" in answer
        assert "hr_policies" in answer.lower() or "来源" in answer

    def test_t04_late_penalty_query(self, answer_generator):
        """T04: 迟到几次扣钱？"""
        answer = answer_generator.generate("迟到几次开始扣钱？")
        assert "50" in answer or "扣" in answer

    def test_t05_projects_query(self, answer_generator):
        """T05: 张三负责哪些项目？"""
        answer = answer_generator.generate("张三负责哪些项目？")
        assert "项目" in answer
        # 应该包含张淑参与的项目
        assert "PRJ" in answer or "ReMe" in answer or "数据" in answer

    def test_t06_dept_count_query(self, answer_generator):
        """T06: 研发部有多少人？"""
        answer = answer_generator.generate("研发部有多少人？")
        assert "4" in answer
        assert "研发部" in answer

    def test_t07_promotion_query(self, answer_generator):
        """T07: 王五符合P5晋升P6条件吗？"""
        answer = answer_generator.generate("王五符合P5晋升P6条件吗？")
        # 王五不符合：KPI平均80<85，项目数1<3
        assert "不符合" in answer or "✗" in answer

    def test_t08_attendance_query(self, answer_generator):
        """T08: 张三2月迟到几次？"""
        answer = answer_generator.generate("张三2月迟到几次？")
        assert "2" in answer or "2次" in answer

    def test_t09_nonexistent_employee(self, answer_generator):
        """T09: 查询不存在的员工"""
        answer = answer_generator.generate("查一下 EMP-999")
        assert "未找到" in answer or "不存在" in answer

    def test_t10_recent_events_query(self, answer_generator):
        """T10: 最近有什么事？"""
        answer = answer_generator.generate("最近有什么事？")
        # 应该有会议纪要相关的内容
        assert "会议" in answer or "事项" in answer or "纪要" in answer

    def test_t11_sql_injection_blocked(self, answer_generator):
        """T11: SQL注入被拦截"""
        answer = answer_generator.generate("SELECT * FROM users WHERE '1'='1")
        assert "敏感字符" in answer or "拦截" in answer or "无法" in answer

    def test_t12_no_matching_content(self, answer_generator):
        """T12: 无匹配内容"""
        answer = answer_generator.generate("xyzabc123怎么报销")
        # 可能会返回无法理解的回复，但不应该编造答案
        assert len(answer) > 0


class TestIntegration:
    """集成测试"""

    def test_full_pipeline(self, answer_generator):
        """测试完整流程"""
        questions = [
            "张三的部门是什么？",
            "年假怎么计算？",
            "张三2月迟到几次？",
        ]
        for q in questions:
            answer = answer_generator.generate(q)
            assert answer is not None
            assert len(answer) > 0
            assert "来源" in answer or "hr_policies" in answer.lower() or "attendance" in answer.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
