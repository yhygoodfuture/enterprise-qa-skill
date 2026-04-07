# 企业智能问答助手 (Enterprise QA Assistant)

## 触发词

- `/enterprise-qa` - 主要触发词
- `/qa` - 简写触发词
- `@enterprise` - 提及触发

## 描述

企业智能问答助手能够回答员工关于公司内部的各种问题，包括员工信息、项目情况、考勤数据、绩效考核、晋升条件、公司制度、财务报销规范等。

系统通过自然语言理解，自动判断问题类型（数据库查询、知识库检索或混合查询），从相应数据源获取信息，生成准确且有依据的回答。

## 使用方式

```
/enterprise-qa "张三的部门是什么？"
/enterprise-qa "年假怎么计算？"
/enterprise-qa "王五符合P5晋升P6条件吗？"
/qa "研发部有多少人？"
@enterprise "张三2月迟到几次？"
```

## 新功能特性 (v1.1.0)

### 缓存机制
- 数据库查询结果缓存（按类型设置不同 TTL）
- 知识库搜索结果缓存
- 减少重复查询，提升响应速度

### 日志记录
- 控制台输出 + 文件记录
- 查询日志、错误日志、缓存命中率统计
- 日志文件按日期分割：`logs/enterprise-qa-YYYY-MM-DD.log`

### 多轮对话
- 支持会话上下文，保持对话连贯性
- 自动记忆上一轮提到的员工姓名等信息
- 连续追问时无需重复提供上下文

```
示例：
问: "张三的部门是什么？" → "研发部"
问: "他负责哪些项目？" → 自动识别"他"指张三
```

### 数据可视化
- 部门人员分布 ASCII 条形图
- 项目状态分布饼图
- 绩效考核表格展示
- 状态徽章（✓/✗）

```
示例输出：
研发部有 4 人： 张三、李四、钱七、周九

【研发部 成员分布】

  张三    │███
  李四    │███
  钱七    │███
  周九    │███

  共 4 人
```

## 数据源

系统连接两个数据源：
1. **结构化数据库 (SQLite)** - 员工信息、项目记录、考勤数据、绩效考核
2. **知识库文档 (Markdown)** - 公司制度、技术规范、会议纪要、FAQ

## 回答示例

**数据库查询：**
```
/enterprise-qa "张三的邮箱是什么？"
→ 张三的邮箱是 zhangsan@company.com。
  > 来源：employees 表 (employee_id: EMP-001)
```

**知识库查询：**
```
/enterprise-qa "年假怎么计算？"
→ 根据《人事制度》，年假计算规则为：
  - 入职满 1 年享 5 天
  - 每增 1 年 +1 天
  - 上限 15 天
  > 来源：hr_policies.md §请假类型
```

**混合查询：**
```
/enterprise-qa "王五符合P5晋升P6条件吗？"
→ 王五目前不符合 P5→P6 晋升条件。
  分析如下：
  | 条件 | 要求 | 王五情况 | 结果 |
  |------|------|---------|------|
  | 入职年限 | 满 1 年 | 2.2 年 | ✓ |
  | 连续 2 季度 KPI≥85 | 是 | 78, 82 (平均 80) | ✗ |
  | 项目数≥3 个 | 是 | 1 个 (PRJ-005 core) | ✗ |
  > 来源：promotion_rules.md + performance_reviews 表 + project_members 表
```

**可视化输出：**
```
/enterprise-qa "研发部有多少人？"
→ 研发部有 4 人：张三、李四、钱七、周九。

【研发部 成员分布】

  张三   │███
  李四   │███
  钱七   │███
  周九   │███

  共 4 人
```

## 环境变量配置

```bash
# 数据库路径
export ENTERPRISE_QA_DB_PATH="./enterprise.db"

# 知识库路径
export ENTERPRISE_QA_KB_PATH="./knowledge"

# 可选：配置文件
export ENTERPRISE_QA_CONFIG="./config.yaml"
```

## API 调用

```python
from src.main import handle_question

# 基础调用
result = handle_question("张三的部门是什么？")
print(result["answer"])

# 启用多轮对话
result = handle_question("张三的部门是什么？", session_id="user123")
print(result["answer"])
# 继续对话
result = handle_question("他负责哪些项目？", session_id="user123")
print(result["answer"])

# 查看统计信息
print(result["stats"])
# {'cache': {'hits': 5, 'misses': 2, 'hit_rate': 71.43}, 'session': {...}}
```

## 功能特性

- **意图识别**：自动判断问题类型（DB/KB/混合）
- **参数化查询**：防SQL注入
- **知识检索**：基于关键词的文档搜索
- **结果融合**：多源信息综合分析
- **来源标注**：清晰标注答案出处
- **错误处理**：友好处理空结果和异常情况
- **缓存机制**：减少重复查询，提升性能
- **日志记录**：文件日志，方便排查问题
- **多轮对话**：支持上下文连续对话
- **数据可视化**：ASCII 图表，清晰直观

## 注意事项

- 所有数据库查询使用参数化查询，防止SQL注入
- 知识库路径和数据库路径可通过环境变量配置
- 敏感信息（如manager_id映射）不会直接暴露
- 无法回答的问题会明确告知，不编造答案
- 缓存可提开关：初始化时设置 `enable_cache=False`

## 依赖

- Python 3.10+
- sqlite3 (标准库)
- pyyaml
- threading (标准库)

## 测试

```bash
cd .claude/skills/enterprise-qa
python -m pytest tests/ -v
```

## 会话管理

```python
from src.main import EnterpriseQA

qa = EnterpriseQA(session_id="my_session")

# 提问
print(qa.ask("张三"))

# 查看统计
print(qa.get_stats())

# 重置会话
qa.reset_session()

# 清空缓存
qa.clear_cache()

qa.close()
```
