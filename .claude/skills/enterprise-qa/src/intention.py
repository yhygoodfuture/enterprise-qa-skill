"""
意图识别模块

识别用户查询的类型和意图：
- DB_ONLY: 纯数据库查询
- KB_ONLY: 纯知识库查询
- MIXED: 混合查询（需要同时查询DB和KB）
- UNKNOWN: 无法识别
"""

import re
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .database import DatabaseQuery, QueryType
from .knowledge import KnowledgeBase


class QueryIntent(Enum):
    """查询意图枚举"""
    DB_ONLY = "db_only"      # 纯数据库查询
    KB_ONLY = "kb_only"      # 纯知识库查询
    MIXED = "mixed"          # 混合查询
    UNKNOWN = "unknown"      # 未知


@dataclass
class ParsedQuery:
    """解析后的查询"""
    intent: QueryIntent
    query_type: QueryType
    entities: Dict[str, any]
    db_query_needed: bool
    kb_query_needed: bool
    original_query: str


class IntentRecognizer:
    """意图识别器"""

    # 数据库查询关键词
    DB_KEYWORDS = {
        '员工': ['员工', '工号', 'emp-', 'email', '邮箱', '上级', '下属', '部门', '职级', '级别'],
        '项目': ['项目', 'prj-', '项目成员', '参与项目', '负责项目'],
        '考勤': ['迟到', '出勤', '考勤', '请假', '旷工', '加班'],
        '绩效': ['绩效', 'kpi', '考核', '评分', '评级', 'grade'],
        '晋升': ['晋升', '升职', '升级', 'p4', 'p5', 'p6', 'p7', 'p8'],
    }

    # 知识库查询关键词
    KB_KEYWORDS = {
        '制度': ['制度', '规定', '标准', '规范', '流程', '怎么算', '如何', '规则'],
        '政策': ['政策', '福利', '年假', '病假', '事假', '调休', '报销', '餐补'],
        '晋升规则': ['晋升条件', '晋升标准', '晋升规则', '评定标准'],
        '会议': ['会议', '大会', 'sync', 'allhands', '纪要', '说了什么', '讲了'],
        '技术': ['技术', '架构', '栈', '规范', '开发流程', 'code review'],
        'faq': ['faq', '常见问题', 'q&a', '问题解答'],
    }

    # 员工姓名列表（从数据库动态获取更准确，这里作为后备）
    COMMON_NAMES = ['张三', '李四', '王五', '赵六', '钱七', '孙八', '周九', '吴十', 'ceo']

    def __init__(self, db: Optional[DatabaseQuery] = None, kb: Optional[KnowledgeBase] = None):
        self.db = db
        self.kb = kb

    def recognize(self, query: str) -> ParsedQuery:
        """
        识别查询意图

        Args:
            query: 用户查询

        Returns:
            ParsedQuery对象
        """
        query = query.strip()
        original = query

        # 1. 检查是否是SQL注入
        if self._is_sql_injection(query):
            return ParsedQuery(
                intent=QueryIntent.UNKNOWN,
                query_type=QueryType.UNKNOWN,
                entities={"error": "sql_injection"},
                db_query_needed=False,
                kb_query_needed=False,
                original_query=original
            )

        # 2. 提取命名实体
        entities = self._extract_entities(query)

        # 3. 判断查询类型
        db_keywords_hit = self._count_keywords(query, self.DB_KEYWORDS)
        kb_keywords_hit = self._count_keywords(query, self.KB_KEYWORDS)

        # 4. 特殊情况判断

        # 晋升条件检查 - 混合查询
        if any(kw in query for kw in ['符合', '条件', '可以晋升', '能晋升']) and \
           any(lv in query for lv in ['p4', 'p5', 'p6', 'p7', 'p8', '晋升']):
            return ParsedQuery(
                intent=QueryIntent.MIXED,
                query_type=QueryType.PROMOTION_CHECK,
                entities=entities,
                db_query_needed=True,
                kb_query_needed=True,
                original_query=original
            )

        # 晋升查询（仅有"晋升"关键词，无具体职级）- 混合查询
        if any(kw in query for kw in ['晋升', '升职']) and 'names' in entities:
            return ParsedQuery(
                intent=QueryIntent.MIXED,
                query_type=QueryType.PROMOTION_CHECK,
                entities=entities,
                db_query_needed=True,
                kb_query_needed=True,
                original_query=original
            )

        # 员工信息查询 - 数据库
        if any(kw in query for kw in ['部门', '邮箱', '上级', '职级', '级别', '入职']):
            return ParsedQuery(
                intent=QueryIntent.DB_ONLY,
                query_type=QueryType.EMPLOYEE_INFO,
                entities=entities,
                db_query_needed=True,
                kb_query_needed=False,
                original_query=original
            )

        # 项目查询 - 数据库
        if any(kw in query for kw in ['项目', '参与', '负责', 'lead', 'core', 'contributor']):
            return ParsedQuery(
                intent=QueryIntent.DB_ONLY,
                query_type=QueryType.EMPLOYEE_PROJECTS,
                entities=entities,
                db_query_needed=True,
                kb_query_needed=False,
                original_query=original
            )

        # 考勤查询 - 数据库（需要有员工姓名）
        if any(kw in query for kw in ['迟到', '考勤', '出勤', '旷工']):
            # 如果没有员工姓名，可能是问政策/规则
            if 'names' not in entities and 'employee_ids' not in entities:
                # 检查是否问的是政策/规则
                if any(kw in query for kw in ['怎么', '如何', '规则', '制度', '标准', '扣钱', '扣款', '开始', '几次', '多少']):
                    return ParsedQuery(
                        intent=QueryIntent.KB_ONLY,
                        query_type=QueryType.UNKNOWN,
                        entities=entities,
                        db_query_needed=False,
                        kb_query_needed=True,
                        original_query=original
                    )
            # 有员工姓名，按数据库查询处理
            return ParsedQuery(
                intent=QueryIntent.DB_ONLY,
                query_type=QueryType.EMPLOYEE_ATTENDANCE,
                entities=entities,
                db_query_needed=True,
                kb_query_needed=False,
                original_query=original
            )

        # 绩效查询 - 数据库
        if any(kw in query for kw in ['绩效', 'kpi', '考核', '评分', '评级']):
            return ParsedQuery(
                intent=QueryIntent.DB_ONLY,
                query_type=QueryType.EMPLOYEE_PERFORMANCE,
                entities=entities,
                db_query_needed=True,
                kb_query_needed=False,
                original_query=original
            )

        # 制度/政策查询 - 知识库
        if any(kw in query for kw in ['怎么算', '如何', '规则', '制度', '规定', '报销', '标准', '迟到扣钱', '扣款']):
            return ParsedQuery(
                intent=QueryIntent.KB_ONLY,
                query_type=QueryType.UNKNOWN,
                entities=entities,
                db_query_needed=False,
                kb_query_needed=True,
                original_query=original
            )

        # 会议纪要查询 - 知识库
        if any(kw in query for kw in ['会议', '大会', '纪要', '说了什么', '讲了', '全员']):
            return ParsedQuery(
                intent=QueryIntent.KB_ONLY,
                query_type=QueryType.UNKNOWN,
                entities=entities,
                db_query_needed=False,
                kb_query_needed=True,
                original_query=original
            )

        # 模糊查询（如"有什么事"）- 知识库
        if any(kw in query for kw in ['事', '最近', '有什么', '事项']):
            return ParsedQuery(
                intent=QueryIntent.KB_ONLY,
                query_type=QueryType.UNKNOWN,
                entities=entities,
                db_query_needed=False,
                kb_query_needed=True,
                original_query=original
            )

        # 根据关键词数量判断
        if db_keywords_hit > kb_keywords_hit:
            return ParsedQuery(
                intent=QueryIntent.DB_ONLY,
                query_type=QueryType.EMPLOYEE_INFO,
                entities=entities,
                db_query_needed=True,
                kb_query_needed=False,
                original_query=original
            )
        elif kb_keywords_hit > db_keywords_hit:
            return ParsedQuery(
                intent=QueryIntent.KB_ONLY,
                query_type=QueryType.UNKNOWN,
                entities=entities,
                db_query_needed=False,
                kb_query_needed=True,
                original_query=original
            )
        else:
            # 无法判断，默认尝试数据库
            return ParsedQuery(
                intent=QueryIntent.DB_ONLY,
                query_type=QueryType.EMPLOYEE_INFO,
                entities=entities,
                db_query_needed=True,
                kb_query_needed=False,
                original_query=original
            )

    def _is_sql_injection(self, query: str) -> bool:
        """检测SQL注入"""
        dangerous = ['union', 'select', 'insert', 'update', 'delete', 'drop', 'exec', 'execute',
                     '--', '#', '/*', '*/', 'or 1=1', 'and 1=1', "or '1'='1", "and '1'='1",
                     "1' or '1'='1", "1' and '1'='1"]
        query_lower = query.lower()
        for pattern in dangerous:
            if pattern in query_lower:
                return True
        return False

    def _extract_entities(self, query: str) -> Dict[str, any]:
        """
        提取命名实体

        Args:
            query: 查询字符串

        Returns:
            Dict of extracted entities
        """
        entities = {}

        # 提取员工姓名
        names = []
        for name in self.COMMON_NAMES:
            if name in query:
                names.append(name)
        if names:
            entities['names'] = names

        # 提取工号
        emp_ids = re.findall(r'EMP-\d{3}', query.upper())
        if emp_ids:
            entities['employee_ids'] = emp_ids

        # 提取项目ID
        prj_ids = re.findall(r'PRJ-\d{3}', query.upper())
        if prj_ids:
            entities['project_ids'] = prj_ids

        # 提取职级
        levels = re.findall(r'P[4-9]', query, re.IGNORECASE)
        if levels:
            entities['levels'] = [l.upper() for l in levels]

        # 提取部门
        departments = ['研发部', '产品部', '市场部', '管理层', '财务部', '人力资源部', '行政部']
        for dept in departments:
            if dept in query:
                entities['department'] = dept
                break

        # 提取年月
        year_month = re.findall(r'(\d{4})[年|\.](\d{1,2})[月|份]?', query)
        if year_month:
            entities['year'] = int(year_month[0][0])
            entities['month'] = int(year_month[0][1])

        # 提取年份
        years = re.findall(r'\b(202[0-9]|203[0-9])\b', query)
        if years:
            entities['year'] = int(years[0])

        return entities

    def _count_keywords(self, query: str, keyword_dict: Dict[str, List[str]]) -> int:
        """统计查询中关键词命中数"""
        count = 0
        query_lower = query.lower()
        for keywords in keyword_dict.values():
            for kw in keywords:
                if kw.lower() in query_lower:
                    count += 1
        return count
