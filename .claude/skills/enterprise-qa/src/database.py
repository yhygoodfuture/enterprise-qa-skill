"""
数据库查询模块

提供结构化数据查询功能，包括：
- 员工信息查询
- 项目信息查询
- 考勤记录查询
- 绩效考核查询
- 跨表关联查询
"""

import sqlite3
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from .config import get_config
from .cache import get_cache


class QueryType(Enum):
    """查询类型枚举"""
    EMPLOYEE_INFO = "employee_info"          # 员工基本信息
    EMPLOYEE_PROJECTS = "employee_projects"  # 员工项目
    EMPLOYEE_ATTENDANCE = "employee_attendance"  # 员工考勤
    EMPLOYEE_PERFORMANCE = "employee_performance"  # 员工绩效
    DEPARTMENT_STATS = "department_stats"    # 部门统计
    PROJECT_INFO = "project_info"            # 项目信息
    PROMOTION_CHECK = "promotion_check"      # 晋升条件检查
    UNKNOWN = "unknown"                       # 未知类型


@dataclass
class QueryResult:
    """查询结果"""
    success: bool
    data: Any = None
    message: str = ""
    source: str = ""
    query_type: QueryType = QueryType.UNKNOWN


class DatabaseQuery:
    """数据库查询类"""

    # SQL注入风险模式检测
    SQL_INJECTION_PATTERNS = [
        r"(\bUNION\b|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bDROP\b|\bEXEC\b|\bEXECUTE\b)",
        r"(--|#|/\*|\*/)",
        r"(\bOR\b\s+\d+\s*=\s*\d+|\bAND\b\s+\d+\s*=\s*\d+)",
        r"('.+'='.+'|\bOR\b.+'='|\bAND\b.+'=')",  # 常见 OR '1'='1' 模式
    ]

    # 缓存 TTL 设置（秒）
    CACHE_TTL = {
        "employee": 300,    # 员工信息 5 分钟
        "projects": 180,    # 项目信息 3 分钟
        "attendance": 60,    # 考勤信息 1 分钟
        "performance": 300, # 绩效信息 5 分钟
        "department": 300,   # 部门信息 5 分钟
    }

    def __init__(self, db_path: Optional[str] = None, enable_cache: bool = True):
        self.db_path = db_path or get_config().get_db_path()
        self._conn: Optional[sqlite3.Connection] = None
        self.enable_cache = enable_cache
        self._cache = get_cache() if enable_cache else None

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _get_cache(self, namespace: str):
        """获取缓存（如果启用）"""
        if self._cache:
            return self._cache.get(namespace)
        return None

    def _set_cache(self, namespace: str, key: str, value):
        """设置缓存（如果启用）"""
        if self._cache:
            ttl = self.CACHE_TTL.get(namespace, 300)
            self._cache.set(namespace, value, ttl, key)

    def _validate_input(self, value: str) -> bool:
        """
        验证输入是否安全（防止SQL注入）

        Args:
            value: 用户输入的值

        Returns:
            True if safe, False otherwise
        """
        if not value:
            return True

        # 检查是否包含SQL注入模式
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return False

        return True

    def _is_sql_injection(self, query: str) -> bool:
        """
        检查查询是否可能是SQL注入

        Args:
            query: SQL查询字符串

        Returns:
            True if potential injection detected, False otherwise
        """
        query_upper = query.upper()

      # Allow common read operations that don't modify data
      # But block if it looks like injection
        dangerous_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE', 'EXEC', 'EXECUTE']
        for keyword in dangerous_keywords:
            if re.search(r'\b' + keyword + r'\b', query_upper):
                return True

        return False

    def get_employee_by_name(self, name: str) -> QueryResult:
        """
        根据姓名查询员工信息

        Args:
            name: 员工姓名

        Returns:
            QueryResult with employee data
        """
        if not self._validate_input(name):
            return QueryResult(
                success=False,
                message="输入包含无效字符，请重新描述您的问题。",
                source="input_validation"
            )

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT employee_id, name, department, level, hire_date, email, status
                FROM employees
                WHERE name = ? AND status = 'active'
                """,
                (name,)
            )
            row = cursor.fetchone()

            if row is None:
                return QueryResult(
                    success=False,
                    message=f"未找到员工 '{name}'，或该员工已离职。",
                    source="employees 表"
                )

            data = dict(row)
            return QueryResult(
                success=True,
                data=data,
                message=f"员工 {name} 的信息如下：",
                source="employees 表"
            )

        except sqlite3.Error as e:
            return QueryResult(
                success=False,
                message=f"查询出错：{str(e)}",
                source="employees 表"
            )

    def get_employee_by_id(self, employee_id: str) -> QueryResult:
        """
        根据工号查询员工信息

        Args:
            employee_id: 工号 (如 EMP-001)

        Returns:
            QueryResult with employee data
        """
        if not self._validate_input(employee_id):
            return QueryResult(
                success=False,
                message="输入包含无效字符，请重新描述您的问题。",
                source="input_validation"
            )

        # 验证工号格式
        if not re.match(r'^EMP-\d{3}$', employee_id):
            return QueryResult(
                success=False,
                message=f"工号 '{employee_id}' 格式不正确，请使用 EMP-XXX 格式。",
                source="input_validation"
            )

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT employee_id, name, department, level, hire_date, email, status
                FROM employees
                WHERE employee_id = ?
                """,
                (employee_id,)
            )
            row = cursor.fetchone()

            if row is None:
                return QueryResult(
                    success=False,
                    message=f"未找到工号 '{employee_id}' 的员工。",
                    source="employees 表"
                )

            data = dict(row)
            return QueryResult(
                success=True,
                data=data,
                message=f"员工 {data['name']}（{employee_id}）的信息如下：",
                source="employees 表"
            )

        except sqlite3.Error as e:
            return QueryResult(
                success=False,
                message=f"查询出错：{str(e)}",
                source="employees 表"
            )

    def get_employee_manager(self, name: str) -> QueryResult:
        """
        查询员工的上级

        Args:
            name: 员工姓名

        Returns:
            QueryResult with manager info
        """
        if not self._validate_input(name):
            return QueryResult(
                success=False,
                message="输入包含无效字符。",
                source="input_validation"
            )

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT e.employee_id, e.name, e.department, e.level
                FROM employees e
                JOIN employees emp ON e.employee_id = emp.manager_id
                WHERE emp.name = ? AND emp.status = 'active'
                """,
                (name,)
            )
            row = cursor.fetchone()

            if row is None:
                return QueryResult(
                    success=False,
                    message=f"未找到员工 '{name}' 的上级信息。",
                    source="employees 表"
                )

            data = dict(row)
            return QueryResult(
                success=True,
                data=data,
                message=f"{name} 的上级是 {data['name']}（{data['employee_id']}，{data['department']}）。",
                source="employees 表"
            )

        except sqlite3.Error as e:
            return QueryResult(
                success=False,
                message=f"查询出错：{str(e)}",
                source="employees 表"
            )

    def get_employee_projects(self, name: str) -> QueryResult:
        """
        查询员工参与的项目

        Args:
            name: 员工姓名

        Returns:
            QueryResult with projects info
        """
        if not self._validate_input(name):
            return QueryResult(
                success=False,
                message="输入包含无效字符。",
                source="input_validation"
            )

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT p.project_id, p.name, p.status, pm.role, p.start_date, p.end_date
                FROM projects p
                JOIN project_members pm ON p.project_id = pm.project_id
                JOIN employees e ON pm.employee_id = e.employee_id
                WHERE e.name = ? AND e.status = 'active'
                ORDER BY p.start_date DESC
                """,
                (name,)
            )
            rows = cursor.fetchall()

            if not rows:
                return QueryResult(
                    success=False,
                    message=f"未找到员工 '{name}' 参与的项目。",
                    source="projects + project_members 表"
                )

            data = [dict(row) for row in rows]
            return QueryResult(
                success=True,
                data=data,
                message=f"{name} 参与的项目如下：",
                source="projects + project_members 表",
                query_type=QueryType.EMPLOYEE_PROJECTS
            )

        except sqlite3.Error as e:
            return QueryResult(
                success=False,
                message=f"查询出错：{str(e)}",
                source="projects + project_members 表"
            )

    def get_department_count(self, department: str) -> QueryResult:
        """
        查询部门人数

        Args:
            department: 部门名称

        Returns:
            QueryResult with count
        """
        if not self._validate_input(department):
            return QueryResult(
                success=False,
                message="输入包含无效字符。",
                source="input_validation"
            )

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT COUNT(*) as count
                FROM employees
                WHERE department = ? AND status = 'active'
                """,
                (department,)
            )
            row = cursor.fetchone()

            if row is None or row['count'] == 0:
                return QueryResult(
                    success=False,
                    message=f"未找到部门 '{department}' 或该部门没有在职员工。",
                    source="employees 表"
                )

            count = row['count']

            # 获取员工名单
            cursor.execute(
                """
                SELECT name FROM employees
                WHERE department = ? AND status = 'active'
                ORDER BY name
                """,
                (department,)
            )
            names = [r['name'] for r in cursor.fetchall()]

            data = {"count": count, "employees": names, "department": department}
            return QueryResult(
                success=True,
                data=data,
                message=f"{department}有 {count} 人：{', '.join(names)}。",
                source="employees 表",
                query_type=QueryType.DEPARTMENT_STATS
            )

        except sqlite3.Error as e:
            return QueryResult(
                success=False,
                message=f"查询出错：{str(e)}",
                source="employees 表"
            )

    def get_employee_attendance(self, name: str, year: int, month: int) -> QueryResult:
        """
        查询员工某月考勤情况

        Args:
            name: 员工姓名
            year: 年份
            month: 月份

        Returns:
            QueryResult with attendance info
        """
        if not self._validate_input(name):
            return QueryResult(
                success=False,
                message="输入包含无效字符。",
                source="input_validation"
            )

        conn = self._get_connection()
        cursor = conn.cursor()

        # 构建月份筛选
        month_str = f"{year:04d}-{month:02d}-%"

        try:
            # 获取该月迟到次数
            cursor.execute(
                """
                SELECT COUNT(*) as late_count
                FROM attendance a
                JOIN employees e ON a.employee_id = e.employee_id
                WHERE e.name = ? AND e.status = 'active'
                AND a.status = 'late' AND a.date LIKE ?
                """,
                (name, month_str)
            )
            late_row = cursor.fetchone()
            late_count = late_row['late_count'] if late_row else 0

            # 获取该月总记录数
            cursor.execute(
                """
                SELECT COUNT(*) as total
                FROM attendance a
                JOIN employees e ON a.employee_id = e.employee_id
                WHERE e.name = ? AND e.status = 'active'
                AND a.date LIKE ?
                """,
                (name, month_str)
            )
            total_row = cursor.fetchone()
            total = total_row['total'] if total_row else 0

            # 获取具体迟到日期
            cursor.execute(
                """
                SELECT a.date
                FROM attendance a
                JOIN employees e ON a.employee_id = e.employee_id
                WHERE e.name = ? AND e.status = 'active'
                AND a.status = 'late' AND a.date LIKE ?
                ORDER BY a.date
                """,
                (name, month_str)
            )
            late_dates = [r['date'] for r in cursor.fetchall()]

            data = {
                "name": name,
                "year": year,
                "month": month,
                "late_count": late_count,
                "total_records": total,
                "late_dates": late_dates
            }

            if late_count == 0:
                message = f"{name} {year}年{month}月没有迟到记录（共 {total} 条考勤记录）。"
            else:
                dates_str = "、".join([d.split('-')[2] + "日" for d in late_dates])
                message = f"{name} {year}年{month}月迟到 {late_count} 次（{dates_str}）。"

            return QueryResult(
                success=True,
                data=data,
                message=message,
                source="attendance 表",
                query_type=QueryType.EMPLOYEE_ATTENDANCE
            )

        except sqlite3.Error as e:
            return QueryResult(
                success=False,
                message=f"查询出错：{str(e)}",
                source="attendance 表"
            )

    def get_employee_performance(self, name: str, year: int) -> QueryResult:
        """
        查询员工某年绩效

        Args:
            name: 员工姓名
            year: 年份

        Returns:
            QueryResult with performance info
        """
        if not self._validate_input(name):
            return QueryResult(
                success=False,
                message="输入包含无效字符。",
                source="input_validation"
            )

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT pr.year, pr.quarter, pr.kpi_score, pr.grade
                FROM performance_reviews pr
                JOIN employees e ON pr.employee_id = e.employee_id
                WHERE e.name = ? AND pr.year = ?
                ORDER BY pr.quarter
                """,
                (name, year)
            )
            rows = cursor.fetchall()

            if not rows:
                return QueryResult(
                    success=False,
                    message=f"未找到 {name} {year} 年的绩效考核记录。",
                    source="performance_reviews 表"
                )

            data = [dict(row) for row in rows]

            # 计算平均分
            scores = [r['kpi_score'] for r in data]
            avg_score = sum(scores) / len(scores) if scores else 0

            result_data = {
                "name": name,
                "year": year,
                "reviews": data,
                "average_score": round(avg_score, 2)
            }

            return QueryResult(
                success=True,
                data=result_data,
                message=f"{name} {year}年绩效：平均分 {avg_score:.2f}。",
                source="performance_reviews 表",
                query_type=QueryType.EMPLOYEE_PERFORMANCE
            )

        except sqlite3.Error as e:
            return QueryResult(
                success=False,
                message=f"查询出错：{str(e)}",
                source="performance_reviews 表"
            )

    def check_promotion_eligibility(self, name: str, from_level: str, to_level: str) -> QueryResult:
        """
        检查员工晋升条件

        Args:
            name: 员工姓名
            from_level: 当前职级 (如 P5)
            to_level: 目标职级 (如 P6)

        Returns:
            QueryResult with eligibility info
        """
        if not self._validate_input(name):
            return QueryResult(
                success=False,
                message="输入包含无效字符。",
                source="input_validation"
            )

        # 验证职级格式
        if not re.match(r'^P[4-9]$', from_level) or not re.match(r'^P[4-9]$', to_level):
            return QueryResult(
                success=False,
                message=f"职级格式不正确，应为 P4-P9 之间的值。",
                source="input_validation"
            )

        # 检查是否是连续的晋升（如P5->P6）
        from_num = int(from_level[1])
        to_num = int(to_level[1])
        if to_num - from_num != 1:
            return QueryResult(
                success=False,
                message="系统目前只支持连续职级晋升检查（如P5->P6）。",
                source="promotion_rules"
            )

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 获取员工基本信息
            cursor.execute(
                """
                SELECT employee_id, name, level, hire_date, status
                FROM employees
                WHERE name = ? AND status = 'active'
                """,
                (name,)
            )
            emp_row = cursor.fetchone()

            if emp_row is None:
                return QueryResult(
                    success=False,
                    message=f"未找到员工 '{name}'。",
                    source="employees 表"
                )

            emp_data = dict(emp_row)
            employee_id = emp_data['employee_id']

            # 获取最近4个季度的绩效
            cursor.execute(
                """
                SELECT quarter, year, kpi_score, grade
                FROM performance_reviews
                WHERE employee_id = ?
                ORDER BY year DESC, quarter DESC
                LIMIT 4
                """,
                (employee_id,)
            )
            perf_rows = cursor.fetchall()

            # 获取参与的项目数
            cursor.execute(
                """
                SELECT COUNT(*) as project_count
                FROM project_members
                WHERE employee_id = ? AND role IN ('lead', 'core')
                """,
                (employee_id,)
            )
            proj_row = cursor.fetchone()
            project_count = proj_row['project_count'] if proj_row else 0

            # 计算入职年限
            hire_date = emp_data['hire_date']
            from datetime import datetime
            hire_dt = datetime.strptime(hire_date, '%Y-%m-%d')
            now = datetime(2026, 3, 27)  # 题目设定的当前日期
            years_employed = (now - hire_dt).days / 365.0

            data = {
                "name": name,
                "current_level": emp_data['level'],
                "target_level": to_level,
                "hire_date": hire_date,
                "years_employed": round(years_employed, 2),
                "performance": [dict(r) for r in perf_rows] if perf_rows else [],
                "project_count": project_count
            }

            return QueryResult(
                success=True,
                data=data,
                message="",
                source="employees + performance_reviews + project_members 表",
                query_type=QueryType.PROMOTION_CHECK
            )

        except sqlite3.Error as e:
            return QueryResult(
                success=False,
                message=f"查询出错：{str(e)}",
                source="employees + performance_reviews + project_members 表"
            )

    def get_active_projects(self) -> QueryResult:
        """
        查询在研项目

        Returns:
            QueryResult with active projects
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT p.project_id, p.name, p.status, p.start_date, p.end_date, e.name as lead_name
                FROM projects p
                LEFT JOIN employees e ON p.lead_id = e.employee_id
                WHERE p.status IN ('active', 'planning')
                ORDER BY p.start_date DESC
                """
            )
            rows = cursor.fetchall()

            if not rows:
                return QueryResult(
                    success=False,
                    message="目前没有在研或计划中的项目。",
                    source="projects 表"
                )

            data = [dict(row) for row in rows]
            return QueryResult(
                success=True,
                data=data,
                message=f"目前在研/计划中的项目共 {len(data)} 个：",
                source="projects 表"
            )

        except sqlite3.Error as e:
            return QueryResult(
                success=False,
                message=f"查询出错：{str(e)}",
                source="projects 表"
            )

    def get_projects_by_status(self, status: str) -> QueryResult:
        """
        按状态查询项目

        Args:
            status: 项目状态 (active/planning/completed/on_hold)

        Returns:
            QueryResult with filtered projects
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 状态中文映射
        status_map = {
            "进行中": "active",
            "计划中": "planning",
            "已完成": "completed",
            "已暂停": "on_hold"
        }

        db_status = status_map.get(status, status)

        try:
            cursor.execute(
                """
                SELECT p.project_id, p.name, p.status, p.start_date, p.end_date, e.name as lead_name
                FROM projects p
                LEFT JOIN employees e ON p.lead_id = e.employee_id
                WHERE p.status = ?
                ORDER BY p.start_date DESC
                """,
                (db_status,)
            )
            rows = cursor.fetchall()

            if not rows:
                return QueryResult(
                    success=False,
                    message=f"目前没有{status}的项目。",
                    source="projects 表"
                )

            data = [dict(row) for row in rows]
            return QueryResult(
                success=True,
                data=data,
                message=f"{status}的项目共 {len(data)} 个：",
                source="projects 表"
            )

        except sqlite3.Error as e:
            return QueryResult(
                success=False,
                message=f"查询出错：{str(e)}",
                source="projects 表"
            )
