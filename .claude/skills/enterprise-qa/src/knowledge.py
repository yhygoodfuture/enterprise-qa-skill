"""
知识库检索模块

提供非结构化知识检索功能，包括：
- 公司制度（hr_policies.md）
- 晋升规则（promotion_rules.md）
- 技术文档（tech_docs.md）
- 财务制度（finance_rules.md）
- FAQ（faq.md）
- 会议纪要（meeting_notes/*.md）
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .config import get_config
from .cache import get_cache


@dataclass
class KnowledgeResult:
    """知识检索结果"""
    success: bool
    content: str = ""
    source: str = ""
    file_path: str = ""
    relevance_score: float = 0.0
    message: str = ""
    section: str = ""  # 匹配的章节名称


class KnowledgeBase:
    """知识库检索类"""

    # 缓存 TTL 设置（秒）
    CACHE_TTL = 300  # 5 分钟

    def __init__(self, kb_path: Optional[str] = None, enable_cache: bool = True):
        self.kb_path = kb_path or get_config().get_kb_path()
        self._index: Dict[str, Dict[str, Any]] = {}
        self.enable_cache = enable_cache
        self._cache = get_cache() if enable_cache else None
        self._build_index()

    def _build_index(self):
        """构建知识库索引"""
        kb_root = Path(self.kb_path)

        if not kb_root.exists():
            return

        # 索引所有markdown文件
        for md_file in kb_root.rglob("*.md"):
            relative_path = str(md_file.relative_to(kb_root))
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # 提取标题和内容
                sections = self._extract_sections(content)

                self._index[relative_path] = {
                    "path": str(md_file),
                    "relative_path": relative_path,
                    "content": content,
                    "sections": sections,
                    "title": self._extract_title(content),
                    "keywords": self._extract_keywords(content)
                }
            except Exception:
                continue

    def _get_cache(self, namespace: str, key: str):
        """获取缓存（如果启用）"""
        if self._cache:
            return self._cache.get(namespace, key)
        return None

    def _set_cache(self, namespace: str, key: str, value):
        """设置缓存（如果启用）"""
        if self._cache:
            self._cache.set(namespace, value, self.CACHE_TTL, key)

    def _extract_title(self, content: str) -> str:
        """提取文档标题"""
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
        return ""

    def _extract_sections(self, content: str) -> Dict[str, str]:
        """
        提取文档章节

        Returns:
            Dict of {section_title: section_content}
        """
        sections = {}
        lines = content.split('\n')

        current_section = ""
        current_content = []

        for line in lines:
            # 检测章节标题 (# ## ###)
            match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if match:
                # 保存上一个章节
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()

                level = len(match.group(1))
                current_section = match.group(2).strip()
                current_content = []
            else:
                current_content.append(line)

        # 保存最后一个章节
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections

    def _extract_keywords(self, content: str) -> List[str]:
        """提取关键词"""
        # 移除markdown语法
        text = re.sub(r'[#*`\[\]()]', '', content)
        # 提取中文和英文词
        words = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z0-9_]+', text)
        # 过滤停用词
        stopwords = {'的', '了', '是', '在', '和', '与', '或', '及', '等', '为', '以', '及', '的', '并', '可', '能', '有'}
        keywords = [w for w in words if w not in stopwords and len(w) > 1]
        return keywords

    def _calculate_relevance(self, query: str, doc_keywords: List[str], doc_sections: Dict[str, str]) -> float:
        """
        计算查询与文档的相关性分数

        使用简单的BM25变种：
        - 查询词在文档中出现的次数
        - 查询词在标题中出现的权重更高
        """
        query_words = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z0-9_]+', query.lower())
        score = 0.0

        # 标题关键词匹配
        for word in query_words:
            for kw in doc_keywords:
                if word in kw.lower():
                    score += 2.0

        # 章节标题匹配（更高权重）
        for section_title in doc_sections.keys():
            for word in query_words:
                if word in section_title.lower():
                    score += 5.0

        return score

    def search(self, query: str, top_k: int = 3) -> List[KnowledgeResult]:
        """
        搜索知识库

        Args:
            query: 查询字符串
            top_k: 返回前k个结果

        Returns:
            List of KnowledgeResult sorted by relevance
        """
        results = []

        for file_path, doc_info in self._index.items():
            score = self._calculate_relevance(query, doc_info['keywords'], doc_info['sections'])

            if score > 0:
                # 找到最相关的章节
                best_section = ""
                best_content = ""

                for section_title, section_content in doc_info['sections'].items():
                    section_score = self._calculate_relevance(query, [section_title], {})
                    if section_score > 0 and section_score > self._calculate_relevance(query, [], {}):
                        if not best_section or section_score > self._calculate_relevance(query, [best_section], {}):
                            best_section = section_title
                            best_content = section_content[:500] + "..." if len(section_content) > 500 else section_content

                results.append(KnowledgeResult(
                    success=True,
                    content=best_content or doc_info['content'][:500],
                    source=doc_info['title'] or file_path,
                    file_path=file_path,
                    relevance_score=score,
                    message=f"在《{doc_info['title']}》中找到相关内容",
                    section=best_section
                ))

        # 按相关性排序
        results.sort(key=lambda x: x.relevance_score, reverse=True)

        return results[:top_k]

    def search_by_keyword(self, keyword: str) -> List[KnowledgeResult]:
        """
        通过关键词搜索

        Args:
            keyword: 关键词

        Returns:
            List of KnowledgeResult
        """
        results = []

        keyword_lower = keyword.lower()

        for file_path, doc_info in self._index.items():
            if keyword_lower in doc_info['content'].lower():
                # 找到关键词所在的章节
                for section_title, section_content in doc_info['sections'].items():
                    if keyword_lower in section_content.lower():
                        # 找到关键词附近的内容
                        idx = section_content.lower().find(keyword_lower)
                        start = max(0, idx - 100)
                        end = min(len(section_content), idx + 200)
                        snippet = section_content[start:end]

                        results.append(KnowledgeResult(
                            success=True,
                            content=snippet,
                            source=f"{doc_info['title']} - {section_title}" if section_title else doc_info['title'],
                            file_path=file_path,
                            relevance_score=1.0,
                            message=f"在《{doc_info['title']}》中找到相关内容"
                        ))
                        break
                else:
                    # 章节没找到，在全文中找
                    idx = doc_info['content'].lower().find(keyword_lower)
                    if idx >= 0:
                        start = max(0, idx - 100)
                        end = min(len(doc_info['content']), idx + 200)
                        snippet = doc_info['content'][start:end]

                        results.append(KnowledgeResult(
                            success=True,
                            content=snippet,
                            source=doc_info['title'],
                            file_path=file_path,
                            relevance_score=0.5,
                            message=f"在《{doc_info['title']}》中找到相关内容"
                        ))

        return results

    def get_promotion_rules(self, from_level: str, to_level: str) -> Optional[KnowledgeResult]:
        """
        获取晋升规则

        Args:
            from_level: 当前职级 (如 P5)
            to_level: 目标职级 (如 P6)

        Returns:
            KnowledgeResult with promotion rules or None
        """
        # 查找晋升规则文档
        promo_file = None
        for path, info in self._index.items():
            if 'promotion' in path.lower():
                promo_file = info
                break

        if not promo_file:
            return None

        # 查找对应的晋升条件
        search_key = f"{from_level} → {to_level}"
        sections = promo_file['sections']

        for section_title, section_content in sections.items():
            if search_key in section_title or (from_level in section_title and to_level in section_title):
                return KnowledgeResult(
                    success=True,
                    content=section_content,
                    source="晋升评定标准",
                    file_path=promo_file['relative_path'],
                    relevance_score=1.0,
                    message=f"找到 {from_level}→{to_level} 晋升条件",
                    section=section_title
                )

        # 尝试模糊匹配
        for section_title, section_content in sections.items():
            if from_level in section_title and '晋升' in section_content:
                return KnowledgeResult(
                    success=True,
                    content=section_content,
                    source="晋升评定标准",
                    file_path=promo_file['relative_path'],
                    relevance_score=0.8,
                    message=f"找到 {from_level} 相关晋升条件",
                    section=section_title
                )

        return KnowledgeResult(
            success=False,
            message=f"未找到 {from_level}→{to_level} 的晋升条件"
        )

    def get_hr_policy(self, policy_type: str) -> Optional[KnowledgeResult]:
        """
        获取人事政策

        Args:
            policy_type: 政策类型 (如 "年假", "迟到", "请假")

        Returns:
            KnowledgeResult with policy content or None
        """
        # 查找人事制度文档
        hr_file = None
        for path, info in self._index.items():
            if 'hr_policies' in path.lower() or '人事' in info.get('title', ''):
                hr_file = info
                break

        if not hr_file:
            # 尝试从faq中查找
            for path, info in self._index.items():
                if 'faq' in path.lower():
                    if policy_type in info['content']:
                        idx = info['content'].find(policy_type)
                        start = max(0, idx - 50)
                        end = min(len(info['content']), idx + 300)
                        snippet = info['content'][start:end]

                        return KnowledgeResult(
                            success=True,
                            content=snippet,
                            source=info['title'],
                            file_path=path,
                            relevance_score=1.0,
                            message=f"在FAQ中找到关于「{policy_type}」的信息",
                            section=""
                        )

            return None

        # 在hr_policies中查找
        for section_title, section_content in hr_file['sections'].items():
            if policy_type in section_title or policy_type in section_content:
                return KnowledgeResult(
                    success=True,
                    content=section_content,
                    source=hr_file['title'],
                    file_path=hr_file['relative_path'],
                    relevance_score=1.0,
                    message=f"找到「{policy_type}」相关制度",
                    section=section_title
                )

        return None

    def get_finance_policy(self, policy_type: str) -> Optional[KnowledgeResult]:
        """
        获取财务制度

        Args:
            policy_type: 制度类型 (如 "差旅费", "报销标准", "业务招待")

        Returns:
            KnowledgeResult with policy content or None
        """
        # 查找财务制度文档
        finance_file = None
        for path, info in self._index.items():
            if 'finance' in path.lower() or '财务' in info.get('title', ''):
                finance_file = info
                break

        if not finance_file:
            return None

        # 在finance_rules中查找相关章节
        for section_title, section_content in finance_file['sections'].items():
            if policy_type in section_title or policy_type in section_content:
                return KnowledgeResult(
                    success=True,
                    content=section_content,
                    source=finance_file['title'],
                    file_path=finance_file['relative_path'],
                    relevance_score=1.0,
                    message=f"找到「{policy_type}」相关制度",
                    section=section_title
                )

        return None

    def get_meeting_notes(self, keyword: str = "") -> List[KnowledgeResult]:
        """
        获取会议纪要

        Args:
            keyword: 关键词（可选）

        Returns:
            List of KnowledgeResult
        """
        results = []

        for path, info in self._index.items():
            if 'meeting_notes' in path.lower() or '会议' in info.get('title', ''):
                if not keyword or keyword in info['content'].lower():
                    results.append(KnowledgeResult(
                        success=True,
                        content=info['content'][:800],
                        source=info['title'],
                        file_path=path,
                        relevance_score=1.0 if keyword else 0.5,
                        message=f"找到会议纪要：{info['title']}"
                    ))

        return results

    def get_recent_events(self) -> List[KnowledgeResult]:
        """
        获取最近的重要事项（从会议纪要中提取）

        Returns:
            List of recent events
        """
        results = []

        # 查找会议纪要
        for path, info in self._index.items():
            if 'meeting_notes' in path.lower():
                # 提取关键决议和行动项
                content = info['content']
                key_items = []

                # 提取 Q&A 部分
                if 'Q&A' in content or 'Q:' in content:
                    qa_match = re.search(r'(Q&A[\s\S]+?(?=---|\Z))', content)
                    if qa_match:
                        key_items.append(("Q&A", qa_match.group(1)[:300]))

                # 提取决议事项
                if '决议' in content or '决议事项' in content:
                    decision_match = re.search(r'(决议[\s\S]+?(?=---|\Z))', content)
                    if decision_match:
                        key_items.append(("决议", decision_match.group(1)[:300]))

                if key_items:
                    results.append(KnowledgeResult(
                        success=True,
                        content="\n".join([f"【{k}】{v}" for k, v in key_items]),
                        source=info['title'],
                        file_path=path,
                        relevance_score=0.8,
                        message=f"从{info['title']}提取的重要事项"
                    ))

        return results
