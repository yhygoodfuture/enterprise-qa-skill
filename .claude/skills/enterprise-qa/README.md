# 企业智能问答助手 (Enterprise QA Skill)

企业智能问答助手是一个 Claude Code Skill，能够回答员工关于公司内部的各种问题。

## 功能特性

- **意图识别**：自动判断问题类型（数据库查询/知识库检索/混合查询）
- **结构化数据查询**：员工信息、项目情况、考勤记录、绩效考核
- **非结构化知识检索**：公司制度、晋升规则、技术文档、财务规范、会议纪要
- **混合查询分析**：综合数据库和知识库信息进行复杂分析（如晋升条件检查）
- **SQL注入防护**：参数化查询 + 危险模式检测
- **来源标注**：清晰标注答案出处

## 目录结构

```
enterprise-qa/
├── skill.md              # Skill 定义文件
├── config.yaml           # 配置文件
├── enterprise.db         # SQLite 数据库
├── requirements.txt      # Python 依赖
├── README.md            # 本文件
├── src/
│   ├── __init__.py
│   ├── config.py        # 配置管理
│   ├── database.py      # 数据库查询
│   ├── knowledge.py     # 知识库检索
│   ├── intention.py     # 意图识别
│   ├── answer.py        # 答案生成
│   └── main.py          # 主入口
└── tests/
    └── test_enterprise_qa.py  # 单元测试
```

## 安装

```bash
# 进入 Skill 目录
cd .claude/skills/enterprise-qa

# 安装依赖
pip install -r requirements.txt

# 初始化数据库（如果需要）
cd ../enterprise-qa-data
bash init_db.sh
```

## 使用方式

### 命令行使用

```bash
cd .claude/skills/enterprise-qa
python -m src.main "您的问题"
```

### 示例问题

```bash
# 员工信息查询
python -m src.main "张三的部门是什么？"
python -m src.main "李四的上级是谁？"
python -m src.main "张三的邮箱是什么？"

# 项目查询
python -m src.main "张三负责哪些项目？"
python -m src.main "有哪些在研项目？"

# 考勤查询
python -m src.main "张三2月迟到几次？"
python -m src.main "王五2月考勤情况？"

# 绩效查询
python -m src.main "张三2025年绩效如何？"

# 晋升条件查询
python -m src.main "王五符合P5晋升P6条件吗？"
python -m src.main "钱七符合晋升条件吗？"

# 制度查询
python -m src.main "年假怎么计算？"
python -m src.main "迟到几次开始扣钱？"
python -m src.main "差旅费报销标准是什么？"

# 会议纪要查询
python -m src.main "3月全员大会说了什么？"
python -m src.main "最近有什么事？"

# 部门统计
python -m src.main "研发部有多少人？"
python -m src.main "产品部有多少人？"
```

## 环境变量配置

```bash
# 数据库路径
export ENTERPRISE_QA_DB_PATH="./enterprise.db"

# 知识库路径
export ENTERPRISE_QA_KB_PATH="./knowledge"

# 配置文件
export ENTERPRISE_QA_CONFIG="./config.yaml"
```

## 测试

```bash
cd .claude/skills/enterprise-qa
python -m pytest tests/ -v
```

## 数据源

### 数据库表

| 表名 | 说明 |
|------|------|
| employees | 员工信息 |
| projects | 项目记录 |
| project_members | 项目成员关联 |
| attendance | 考勤记录 |
| performance_reviews | 绩效考核 |

### 知识库文档

| 文档 | 说明 |
|------|------|
| hr_policies.md | 人事制度 |
| promotion_rules.md | 晋升评定标准 |
| tech_docs.md | 技术规范 |
| finance_rules.md | 财务报销制度 |
| faq.md | 常见问题解答 |
| meeting_notes/*.md | 会议纪要 |

## 技术实现

### 意图识别流程

1. SQL注入检测
2. 命名实体提取（员工姓名、工号、部门、职级、年月等）
3. 关键词匹配判断查询类型
4. 特殊规则处理（晋升条件、考勤政策等）

### 答案生成流程

1. 根据意图选择数据源（DB/KB/混合）
2. 并行/串行执行查询
3. 综合分析结果
4. 格式化输出答案和来源

### 安全措施

- 参数化查询防止SQL注入
- 输入验证过滤危险字符
- 路径可配置防止路径遍历
- 不暴露敏感字段（如manager_id映射）

### 清单确认分析：

| 要求 | 状态 | 说明 |
|------|------|------|
| Skill 可在 Claude Code  中正常执行 | ✅ | `skill.md` 定义触发词 `/enterprise-qa`、`/qa`、`@enterprise` |
| 测试数据库文件 (enterprise.db) | ✅ | `enterprise-qa-data/enterprise.db` |
| 知识库文件 (knowledge/) | ✅ | `enterprise-qa-data/knowledge/` 包含 hr_policies.md、promotion_rules.md、finance_rules.md、tech_docs.md、faq.md、meeting_notes/ |
| Skill 使用说明（触发词、安装方式） | ✅ | `skill.md` 包含完整使用说明、API调用示例、环境变量配置 |
| 测试用例运行方式 | ✅ | `skill.md` 中说明：`python -m pytest tests/ -v` |
| 依赖清单 (requirements.txt) | ✅ | `.claude/skills/enterprise-qa/requirements.txt`（pytest、pyyaml） |
| 配置文件或环境变量说明 | ✅ | `config.yaml` + `skill.md` 中的环境变量说明 |

**结论：全部要求已满足。**
