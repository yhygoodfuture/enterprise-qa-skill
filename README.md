# Enterprise QA Assistant (企业智能问答助手)

企业智能问答助手是一个 Claude Code Skill，能够回答员工关于公司内部的各种问题，包括员工信息、项目情况、考勤数据、绩效考核、晋升条件、公司制度、财务报销规范等。

## 项目结构

```
enterprise-qa-skill/
├── .claude/skills/enterprise-qa/     # Skill 核心代码
│   ├── src/
│   │   ├── main.py           # 主入口，CLI 和 Skill 接口
│   │   ├── config.py         # 配置管理
│   │   ├── database.py       # SQLite 数据库查询
│   │   ├── knowledge.py      # 知识库文档检索
│   │   ├── answer.py         # 答案生成与融合
│   │   ├── intention.py      # 意图识别
│   │   ├── cache.py          # 查询结果缓存
│   │   ├── logger.py         # 日志记录
│   │   ├── conversation.py   # 多轮对话上下文
│   │   └── visualization.py   # ASCII 数据可视化
│   ├── tests/
│   │   └── test_enterprise_qa.py
│   ├── charts/               # 可视化图表
│   ├── requirements.txt
│   ├── config.yaml
│   └── skill.md              # Skill 定义
│
├── enterprise-qa-data/       # 测试数据
│   ├── enterprise.db         # SQLite 数据库
│   ├── schema.sql            # 数据库表结构
│   ├── seed_data.sql         # 种子数据
│   ├── init_db.sh            # 数据库初始化脚本
│   ├── config.yaml.example
│   └── knowledge/            # 知识库文档
│       ├── hr_policies.md    # 人事制度
│       ├── promotion_rules.md # 晋升标准
│       ├── finance_rules.md  # 财务制度
│       ├── tech_docs.md      # 技术规范
│       ├── faq.md            # 常见问题
│       └── meeting_notes/     # 会议纪要
│
└── README.md                 # 本文件
```

## 功能特性

- **意图识别** - 自动判断问题类型（数据库查询/知识库检索/混合查询）
- **多轮对话** - 支持上下文连续对话，自动记忆员工姓名等信息
- **缓存机制** - 数据库查询和知识库搜索结果缓存，提升响应速度
- **日志记录** - 控制台+文件日志，按日期分割
- **数据可视化** - ASCII 条形图、饼图、表格展示
- **来源标注** - 清晰标注答案出处

## 快速开始

### 1. 安装依赖

```bash
cd .claude/skills/enterprise-qa
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
cd enterprise-qa-data
chmod +x init_db.sh
./init_db.sh
```

### 3. 配置环境变量

```bash
export ENTERPRISE_QA_DB_PATH="./enterprise-qa-data/enterprise.db"
export ENTERPRISE_QA_KB_PATH="./enterprise-qa-data/knowledge"
```

### 4. 命令行使用

```bash
cd .claude/skills/enterprise-qa
python -m src.main "张三的部门是什么？"
python -m src.main "年假怎么计算？"
python -m src.main "王五符合P5晋升P6条件吗？" my_session
```

### 5. API 调用

```python
from src.main import handle_question

result = handle_question("张三的部门是什么？")
print(result["answer"])
# 多轮对话
result = handle_question("他负责哪些项目？", session_id="user123")
```

## 触发词

- `/enterprise-qa` - 主要触发词
- `/qa` - 简写触发词
- `@enterprise` - 提及触发

## 数据来源

系统连接两个数据源：

1. **结构化数据库 (SQLite)** - 员工信息、项目记录、考勤数据、绩效考核
2. **知识库文档 (Markdown)** - 公司制度、技术规范、会议纪要、FAQ

## 示例输出

**数据库查询：**
```
问: 张三的邮箱是什么？
答: 张三的邮箱是 zhangsan@company.com。
    > 来源：employees 表 (employee_id: EMP-001)
```

**知识库查询：**
```
问: 年假怎么计算？
答: 根据《人事制度》，年假计算规则为：
    - 入职满 1 年享 5 天
    - 每增 1 年 +1 天
    - 上限 15 天
    > 来源：hr_policies.md §请假类型
```

**可视化输出：**
```
问: 研发部有多少人？
答: 研发部有 4 人：张三、李四、钱七、周九。

【研发部 成员分布】

  张三   │███
  李四   │███
  钱七   │███
  周九   │███

  共 4 人
```

## 运行测试

```bash
cd .claude/skills/enterprise-qa
python -m pytest tests/ -v
```

## 技术栈

- Python 3.10+
- SQLite3 (标准库)
- PyYAML
- 正则表达式 (标准库)

## License

Internal use only.