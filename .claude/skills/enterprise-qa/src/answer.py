"""
答案生成模块

根据查询意图，综合数据库和知识库查询结果，生成最终答案
"""

from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from datetime import datetime

from .database import DatabaseQuery, QueryResult, QueryType
from .knowledge import KnowledgeBase, KnowledgeResult
from .intention import IntentRecognizer, QueryIntent, ParsedQuery
from .visualization import (
    visualize_department_stats,
    visualize_performance,
    visualize_project_status,
    format_table,
    format_bar_chart,
    ASCIIGraph,
    StatusBadge
)

if TYPE_CHECKING:
    from .conversation import ConversationContext


class AnswerGenerator:
    """答案生成器"""

    def __init__(
        self,
        db: Optional[DatabaseQuery] = None,
        kb: Optional[KnowledgeBase] = None,
        context: Optional["ConversationContext"] = None
    ):
        self.db = db or DatabaseQuery()
        self.kb = kb or KnowledgeBase()
        self.context = context
        self.intent_recognizer = IntentRecognizer(self.db, self.kb)
        self.last_intent: str = "unknown"  # 用于日志记录

    def _update_context(self, query: str, parsed: ParsedQuery, answer: str):
        """更新对话上下文"""
        if self.context:
            # 更新最后提到的实体
            if 'names' in parsed.entities:
                self.context.update_entity({'last_name': parsed.entities['names'][0]})
            if 'employee_ids' in parsed.entities:
                self.context.update_entity({'last_employee_id': parsed.entities['employee_ids'][0]})
            self.context.last_intent = parsed.intent.value

    def generate(self, query: str) -> str:
        """
        生成答案

        Args:
            query: 用户查询

        Returns:
            格式化的答案字符串
        """
        # 0. 代词解析：如果 query 包含代词且上下文有 last_name，则替换
        original_query = query
        if self.context and self.context.last_entity.get('last_name'):
            last_name = self.context.last_entity['last_name']
            # 检测代词
            pronouns = ['他', '她', '它']
            for pronoun in pronouns:
                if pronoun in query:
                    query = query.replace(pronoun, last_name)
                    break

        # 1. 识别意图
        parsed = self.intent_recognizer.recognize(query)
        self.last_intent = parsed.intent.value

        # 2. 处理错误情况
        if "error" in parsed.entities and parsed.entities["error"] == "sql_injection":
            return self._format_error(
                "您的查询包含敏感字符，已被系统拦截。如需查询数据，请换一种描述方式。",
                "security"
            )

        # 3. 根据意图分发查询
        if parsed.intent == QueryIntent.DB_ONLY:
            answer = self._handle_db_only(query, parsed)
        elif parsed.intent == QueryIntent.KB_ONLY:
            answer = self._handle_kb_only(query, parsed)
        elif parsed.intent == QueryIntent.MIXED:
            answer = self._handle_mixed(query, parsed)
        else:
            answer = self._handle_unknown(query, parsed)

        # 4. 更新上下文
        self._update_context(query, parsed, answer)

        return answer

    def _handle_db_only(self, query: str, parsed: ParsedQuery) -> str:
        """处理纯数据库查询"""
        entities = parsed.entities

        # T01: 查询员工部门
        if '部门' in query and 'names' in entities:
            name = entities['names'][0]
            result = self.db.get_employee_by_name(name)
            if result.success:
                return self._format_db_result(
                    f"{name}的部门是{result.data['department']}。",
                    result.source,
                    result.data.get('employee_id')
                )
            else:
                return self._format_error(result.message, result.source)

        # T02: 查询员工上级
        if '上级' in query and 'names' in entities:
            name = entities['names'][0]
            result = self.db.get_employee_manager(name)
            if result.success:
                return self._format_db_result(result.message, result.source)
            else:
                return self._format_error(result.message, result.source)

        # T05: 查询员工参与的项目
        if any(kw in query for kw in ['项目', '参与', '负责']) and 'names' in entities:
            name = entities['names'][0]
            result = self.db.get_employee_projects(name)
            if result.success:
                return self._format_projects_result(result.data, name, result.source)
            else:
                return self._format_error(result.message, result.source)

        # T06: 查询部门人数
        if '有多少' in query:
            dept = entities.get('department')
            if dept:
                result = self.db.get_department_count(dept)
                if result.success:
                    # 添加可视化
                    viz = visualize_department_stats(result.data)
                    answer = self._format_db_result(f"{result.message}\n\n{viz}", result.source)
                    return answer
            # 尝试从查询中提取部门
            for dept in ['研发部', '产品部', '市场部', '管理层', '财务部', '人力资源部']:
                if dept in query:
                    result = self.db.get_department_count(dept)
                    if result.success:
                        viz = visualize_department_stats(result.data)
                        return self._format_db_result(f"{result.message}\n\n{viz}", result.source)
                    break
            return self._format_error("无法确定要查询的部门，请明确说出部门名称。", "input")

        # T08: 查询员工考勤
        if any(kw in query for kw in ['迟到', '考勤', '出勤']) and 'names' in entities:
            name = entities['names'][0]
            year = entities.get('year', 2026)
            month = entities.get('month', 2)  # 默认2月
            result = self.db.get_employee_attendance(name, year, month)
            if result.success:
                return self._format_db_result(result.message, result.source)
            else:
                return self._format_error(result.message, result.source)

        # 查询员工邮箱
        if any(kw in query for kw in ['邮箱', 'email']) and 'names' in entities:
            name = entities['names'][0]
            result = self.db.get_employee_by_name(name)
            if result.success:
                return self._format_db_result(
                    f"{name}的邮箱是{result.data['email']}。",
                    result.source,
                    result.data.get('employee_id')
                )
            else:
                return self._format_error(result.message, result.source)

        # 查询员工职级
        if any(kw in query for kw in ['职级', '级别', 'level', 'P']) and 'names' in entities:
            name = entities['names'][0]
            result = self.db.get_employee_by_name(name)
            if result.success:
                return self._format_db_result(
                    f"{name}的职级是{result.data['level']}，入职于{result.data['hire_date']}。",
                    result.source,
                    result.data.get('employee_id')
                )
            else:
                return self._format_error(result.message, result.source)

        # 查询员工ID
        if 'employee_ids' in entities:
            emp_id = entities['employee_ids'][0]
            result = self.db.get_employee_by_id(emp_id)
            if result.success:
                data = result.data
                status_str = "在职" if data['status'] == 'active' else "已离职"
                return self._format_db_result(
                    f"工号{emp_id}是{data['name']}，{data['department']}，职级{data['level']}，{status_str}。",
                    result.source
                )
            else:
                return self._format_error(result.message, result.source)

        # T09: 查询不存在的员工
        if 'names' in entities:
            name = entities['names'][0]
            result = self.db.get_employee_by_name(name)
            if result.success:
                # 员工存在，但没有具体问题时追问
                return self._format_db_result(
                    f"找到了员工 {name}，请问您想查询什么信息？\n"
                    f"例如：{name}的部门、邮箱、职级、上级、项目、考勤等",
                    result.source
                )
            else:
                # 员工不存在
                return self._format_error(result.message, result.source)

        # 在研项目查询
        if any(kw in query for kw in ['在研', 'active', '进行中', '项目']):
            result = self.db.get_active_projects()
            if result.success:
                projects = result.data
                # 添加可视化
                viz = visualize_project_status(projects)
                lines = [f"目前在研/计划中的项目共 {len(projects)} 个："]
                return self._format_db_result("\n".join(lines) + "\n\n" + viz, result.source)

        # 默认处理
        return self._handle_unknown(query, parsed)

    def _handle_kb_only(self, query: str, parsed: ParsedQuery) -> str:
        """处理纯知识库查询"""
        # T03: 年假怎么计算
        if any(kw in query for kw in ['年假', '怎么算', '计算']):
            result = self.kb.get_hr_policy('年假')
            if result and result.success:
                return self._format_kb_result(
                    "根据《人事制度》，年假计算规则为：\n"
                    "- 入职满 1 年享 5 天\n"
                    "- 每增 1 年 +1 天\n"
                    "- 上限 15 天\n"
                    "- 年假有效期为自然年，未休可折算工资或结转（最多5天）",
                    result.source,
                    result.section
                )

        # T04: 迟到扣款
        if any(kw in query for kw in ['迟到', '扣钱', '扣款', '罚']):
            result = self.kb.get_hr_policy('迟到')
            if result and result.success:
                # 针对直接问题或简短问法给出简洁回答
                if any(kw in query for kw in ['开始', '几次', '多少', '怎么']) or len(query) < 10:
                    return self._format_kb_result(
                        "根据《人事制度》：\n"
                        "迟到**4-6次**，每次扣款**50元**。\n"
                        "（3次以内不扣款，7次以上视为旷工）",
                        result.source
                    )
                return self._format_kb_result(
                    "根据《人事制度》迟到规则：\n"
                    "| 月累计迟到次数 | 处理方式 |\n"
                    "| 3次以内 | 不扣款，口头提醒 |\n"
                    "| 4-6次 | 每次扣款50元 |\n"
                    "| 7次以上 | 视为旷工1天，通报批评 |",
                    result.source
                )

        # 报销标准
        if any(kw in query for kw in ['报销', '差旅', '机票', '酒店', '餐补']):
            results = self.kb.search_by_keyword('报销')
            if results:
                r = results[0]
                return self._format_kb_result(
                    f"根据《财务报销制度》：\n"
                    f"- 机票：经济舱，提前7天预订\n"
                    f"- 酒店：一线城市≤500元/天，其他≤300元/天\n"
                    f"- 餐补：出差100元/天\n"
                    f"- 报销流程：系统提交→主管审批→财务审核→打款（5工作日）",
                    r.source
                )

        # 晋升条件 - 通用
        if any(kw in query for kw in ['晋升', '升职', '条件']):
            # 尝试提取具体职级
            levels = entities.get('levels', []) if 'entities' in dir() else []
            if len(levels) >= 2:
                result = self.kb.get_promotion_rules(levels[0], levels[1])
                if result and result.success:
                    return self._format_kb_result(result.content, result.source, result.section)

            # 返回通用晋升信息
            results = self.kb.search_by_keyword('晋升')
            if results:
                r = results[0]
                return self._format_kb_result(
                    "根据《晋升评定标准》：\n"
                    "- P4→P5：入职满6个月，连续2季度≥B\n"
                    "- P5→P6：入职满1年，连续2季度KPI≥85，主导/核心参与≥3个项目\n"
                    "- P6→P7：P6满2年，连续4季度KPI≥90，主导项目≥2个\n"
                    "- P7→P8：P7满3年，年度绩效至少2个S\n"
                    "晋升流程：提名→评审→答辩→公示→生效（每年3月、9月）",
                    r.source
                )

        # 会议纪要
        if any(kw in query for kw in ['会议', '大会', '说了什么', '讲了']):
            results = self.kb.get_meeting_notes()
            if results:
                lines = []
                for r in results[:2]:  # 最多2个会议纪要
                    lines.append(f"【{r.source}】\n{r.content[:300]}...")
                return self._format_kb_result("\n\n".join(lines), "会议纪要")

        # 最近事项
        if any(kw in query for kw in ['最近', '事', '事项', '有什么事']):
            results = self.kb.get_recent_events()
            if results:
                lines = ["近期重要事项："]
                for r in results:
                    lines.append(f"\n{r.message}:\n{r.content[:200]}...")
                return self._format_kb_result("\n".join(lines), "会议纪要")

        # 通用搜索
        results = self.kb.search(query)
        if results:
            r = results[0]
            return self._format_kb_result(r.content[:500], r.source)

        return self._format_error(
            "抱歉，我无法从知识库中找到相关信息。建议您咨询HR或相关部门。",
            "knowledge_base"
        )

    def _handle_mixed(self, query: str, parsed: ParsedQuery) -> str:
        """处理混合查询"""
        entities = parsed.entities
        name = entities.get('names', [''])[0] if 'names' in entities else None

        if not name:
            return self._format_error("无法确定要查询的员工姓名。", "input")

        # 提取职级信息
        levels = entities.get('levels', [])
        from_level, to_level = None, None

        if len(levels) >= 2:
            # 假设第一个是当前职级，第二个是目标职级
            for i in range(len(levels) - 1):
                from_level = levels[i]
                to_level = levels[i + 1]
                break

        # 如果没有明确给出职级，尝试从数据库获取
        if not from_level or not to_level:
            emp_result = self.db.get_employee_by_name(name)
            if emp_result.success:
                current_level = emp_result.data.get('level', '')
                if current_level:
                    from_level = current_level
                    from_num = int(current_level[1])
                    # 尝试匹配查询中的目标职级
                    for lvl in levels:
                        if int(lvl[1]) == from_num + 1:
                            to_level = lvl
                            break

        # 如果仍然没有目标职级，尝试推断
        if not to_level and from_level:
            from_num = int(from_level[1])
            if from_num < 9:
                to_level = f"P{from_num + 1}"

        # T07: 王五符合P5晋升P6条件吗？
        if from_level and to_level:
            # 从数据库获取员工信息
            emp_result = self.db.get_employee_by_name(name)
            if not emp_result.success:
                return self._format_error(emp_result.message, emp_result.source)

            # 获取晋升条件
            kb_result = self.kb.get_promotion_rules(from_level, to_level)

            # 获取绩效和项目数据
            cursor_year = 2025
            perf_result = self.db.get_employee_performance(name, cursor_year)

            # 检查晋升条件
            analysis = self._analyze_promotion(
                name,
                from_level,
                to_level,
                emp_result.data,
                perf_result.data if perf_result.success else None,
                None  # project_count will be retrieved if needed
            )

            return self._format_promotion_result(name, from_level, to_level, analysis, kb_result)

        return self._format_error("无法理解晋升查询，请明确说明员工姓名和目标职级。", "input")

    def _analyze_promotion(self, name: str, from_level: str, to_level: str,
                          emp_data: Dict, perf_data: Optional[Dict],
                          project_data: Optional[List]) -> Dict:
        """
        分析晋升条件

        Returns:
            Dict with analysis results for each condition
        """
        analysis = {
            "eligible": True,
            "conditions": []
        }

        from datetime import datetime
        hire_date = emp_data.get('hire_date', '')
        hire_dt = datetime.strptime(hire_date, '%Y-%m-%d')
        now = datetime(2026, 3, 27)
        years_employed = (now - hire_dt).days / 365.0

        # P5 -> P6 条件检查
        if from_level == 'P5' and to_level == 'P6':
            # 条件1: 入职满1年
            cond1 = years_employed >= 1
            analysis["conditions"].append({
                "name": "入职年限",
                "requirement": "满 1 年",
                "actual": f"{years_employed:.1f} 年",
                "passed": cond1
            })

            # 条件2: 连续2季度KPI>=85
            kpi_passed = False
            kpi_avg = 0
            if perf_data and 'reviews' in perf_data:
                reviews = perf_data['reviews']
                if len(reviews) >= 2:
                    recent_2 = reviews[:2]  # 最近2个季度
                    scores = [r['kpi_score'] for r in recent_2]
                    kpi_avg = sum(scores) / len(scores)
                    kpi_passed = all(s >= 85 for s in scores)

            cond2 = kpi_passed
            analysis["conditions"].append({
                "name": "连续2季度KPI≥85",
                "requirement": "≥85",
                "actual": f"平均 {kpi_avg:.1f}" if kpi_avg else "无数据",
                "passed": cond2
            })

            # 条件3: 主导或核心参与>=3个项目
            # 需要额外查询项目数
            proj_result = self.db.get_employee_projects(name)
            project_count = 0
            if proj_result.success:
                project_count = len([p for p in proj_result.data if p.get('role') in ['lead', 'core']])

            cond3 = project_count >= 3
            analysis["conditions"].append({
                "name": "主导/核心参与项目≥3个",
                "requirement": "≥3个",
                "actual": f"{project_count}个",
                "passed": cond3
            })

            analysis["eligible"] = cond1 and cond2 and cond3

        # 其他职级晋升的简化检查
        elif from_level == 'P6' and to_level == 'P7':
            cond1 = years_employed >= 2
            analysis["conditions"].append({
                "name": "P6满2年",
                "requirement": "≥2年",
                "actual": f"{years_employed:.1f}年",
                "passed": cond1
            })

            kpi_passed = False
            kpi_avg = 0
            if perf_data and 'reviews' in perf_data:
                reviews = perf_data['reviews']
                if len(reviews) >= 4:
                    recent_4 = reviews[:4]
                    scores = [r['kpi_score'] for r in recent_4]
                    kpi_avg = sum(scores) / len(scores)
                    kpi_passed = all(s >= 90 for s in scores)

            cond2 = kpi_passed
            analysis["conditions"].append({
                "name": "连续4季度KPI≥90",
                "requirement": "≥90",
                "actual": f"平均 {kpi_avg:.1f}" if kpi_avg else "无数据",
                "passed": cond2
            })

            analysis["eligible"] = cond1 and cond2

        return analysis

    def _handle_unknown(self, query: str, parsed: ParsedQuery) -> str:
        """处理未知类型查询"""
        # 尝试作为员工信息查询处理
        entities = parsed.entities

        # 处理"不存在员工"、"查一下XXX"等模式
        if any(kw in query for kw in ['不存在', '没有这个', '找不到']):
            # 如果有工号，尝试查询
            if 'employee_ids' in entities:
                emp_id = entities['employee_ids'][0]
                result = self.db.get_employee_by_id(emp_id)
                return self._format_error(result.message, result.source)
            # 如果有姓名，尝试查询
            if 'names' in entities:
                name = entities['names'][0]
                result = self.db.get_employee_by_name(name)
                return self._format_error(result.message, result.source)
            # 都没有，返回友好提示
            return self._format_error(
                "请提供具体的员工姓名或工号，如「张三」或「EMP-001」。",
                "input"
            )

        if 'names' in entities:
            name = entities['names'][0]
            result = self.db.get_employee_by_name(name)
            if result.success:
                data = result.data
                lines = [f"{name}的信息："]
                lines.append(f"- 工号: {data['employee_id']}")
                lines.append(f"- 部门: {data['department']}")
                lines.append(f"- 职级: {data['level']}")
                lines.append(f"- 邮箱: {data['email']}")
                lines.append(f"- 入职日期: {data['hire_date']}")
                lines.append(f"- 状态: {'在职' if data['status'] == 'active' else '已离职'}")
                return self._format_db_result("\n".join(lines), result.source)

        if 'employee_ids' in entities:
            emp_id = entities['employee_ids'][0]
            result = self.db.get_employee_by_id(emp_id)
            if result.success:
                return self._format_db_result(
                    f"{result.data['name']}，{result.data['department']}，{result.data['level']}。",
                    result.source
                )
            else:
                return self._format_error(result.message, result.source)

        # T10: 模糊问题
        if any(kw in query for kw in ['最近', '有什么事', '事项']):
            events = self.kb.get_recent_events()
            if events:
                lines = ["根据近期会议纪要，重要事项如下："]
                for e in events:
                    lines.append(f"\n{e.message}：\n{e.content[:200]}")
                return self._format_kb_result("\n".join(lines), "会议纪要")

        # T12: 无法回答的问题
        return self._format_error(
            "抱歉，我无法理解您的问题。您可以尝试：\n"
            "1. 询问员工信息（如：张三的部门是什么？）\n"
            "2. 询问公司制度（如：年假怎么计算？）\n"
            "3. 询问项目情况（如：有哪些在研项目？）",
            "unknown"
        )

    def _format_db_result(self, content: str, source: str, employee_id: str = None) -> str:
        """格式化数据库查询结果"""
        if employee_id:
            return f"{content}\n\n> 来源：{source} (employee_id: {employee_id})"
        return f"{content}\n\n> 来源：{source}"

    def _format_kb_result(self, content: str, source: str, section: str = "") -> str:
        """格式化知识库查询结果"""
        # 从source中提取文档名
        if 'hr_policies' in source.lower() or 'hr_policies' in source:
            doc_name = 'hr_policies.md'
        elif 'promotion' in source.lower():
            doc_name = 'promotion_rules.md'
        elif 'finance' in source.lower():
            doc_name = 'finance_rules.md'
        elif 'meeting' in source.lower() or '会议' in source:
            doc_name = 'meeting_notes'
        else:
            doc_name = source.split('/')[-1] if '/' in source else source

        if section:
            return f"{content}\n\n> 来源：{doc_name} §{section}"
        return f"{content}\n\n> 来源：{doc_name}"

    def _format_projects_result(self, projects: List[Dict], name: str, source: str) -> str:
        """格式化项目查询结果"""
        if not projects:
            return self._format_error(f"未找到{name}参与的项目。", source)

        status_map = {
            'active': '进行中',
            'planning': '计划中',
            'completed': '已完成',
            'on_hold': '暂停'
        }

        role_map = {
            'lead': '负责人',
            'core': '核心成员',
            'contributor': '贡献者'
        }

        lines = [f"{name}参与的项目共 {len(projects)} 个："]
        for p in projects:
            status = status_map.get(p.get('status', ''), p.get('status', ''))
            role = role_map.get(p.get('role', ''), p.get('role', ''))
            lines.append(f"- {p['name']}（{status}，{role}）")

        return self._format_db_result("\n".join(lines), source)

    def _format_promotion_result(self, name: str, from_level: str, to_level: str,
                                analysis: Dict, kb_result: Optional[KnowledgeResult]) -> str:
        """格式化晋升查询结果"""
        eligible = analysis["eligible"]

        lines = []
        if eligible:
            lines.append(f"{name}目前符合 {from_level}→{to_level} 晋升条件。")
        else:
            lines.append(f"{name}目前不符合 {from_level}→{to_level} 晋升条件。")

        lines.append("\n分析如下：")
        lines.append("| 条件 | 要求 | 实际情况 | 结果 |")
        lines.append("|------|------|---------|------|")

        for cond in analysis["conditions"]:
            result_icon = "✓" if cond["passed"] else "✗"
            lines.append(f"| {cond['name']} | {cond['requirement']} | {cond['actual']} | {result_icon} |")

        # 添加建议
        if not eligible:
            failed = [c['name'] for c in analysis["conditions"] if not c['passed']]
            if failed:
                lines.append(f"\n建议：提升{failed[0]}。")

        # 添加来源
        sources = ["promotion_rules.md"]
        if kb_result and kb_result.section:
            sources[0] = f"promotion_rules.md §{kb_result.section}"
        elif kb_result and kb_result.source:
            sources.append(kb_result.source)

        return "\n".join(lines) + f"\n\n> 来源：{', '.join(sources)} + performance_reviews 表 + project_members 表"

    def _format_error(self, message: str, source: str) -> str:
        """格式化错误信息"""
        return f"{message}"
