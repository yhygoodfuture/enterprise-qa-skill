"""
可视化模块

提供 ASCII 图表和文本可视化功能
"""

from typing import Dict, List, Any, Optional


class ASCIIGraph:
    """ASCII 图表生成器"""

    @staticmethod
    def bar_chart(
        data: Dict[str, float],
        title: str = "",
        max_width: int = 30,
        unit: str = "",
        show_values: bool = True,
        decimal_places: int = 0
    ) -> str:
        """
        生成水平条形图（对齐版）

        Args:
            data: Dict of label -> value
            title: 图表标题
            max_width: 最大条形宽度（不含标签和数值）
            unit: 单位
            show_values: 是否显示数值
            decimal_places: 数值小数位数

        Returns:
            ASCII 条形图字符串
        """
        if not data:
            return "无数据"

        lines = []

        # 计算最大标签长度
        max_label_len = max(len(str(k)) for k in data.keys())
        max_value = max(data.values()) if data else 1

        # 计算数值的最大显示宽度
        max_valueWidth = max(
            len(f"{v:.{decimal_places}f}{unit}") for v in data.values()
        ) if show_values else 0

        # 总宽度 = 标签 + 空格 + 条形 + 空格 + 数值
        bar_area_width = max_width
        total_width = max_label_len + 1 + bar_area_width + 1 + max_valueWidth

        if title:
            lines.append(f"【{title}】")

        # 绘制 Y 轴标签和条形
        for label, value in data.items():
            label_str = str(label)
            bar_len = int((value / max_value) * bar_area_width) if max_value > 0 else 0
            bar = "█" * bar_len

            if show_values:
                value_str = f"{value:.{decimal_places}f}{unit}".rjust(max_valueWidth)
                line = f"{label_str:<{max_label_len}} │{bar} {value_str}"
            else:
                line = f"{label_str:<{max_label_len}} │{bar}"

            lines.append(line)

        # 添加底部刻度（简化版：只显示0和最大值）
        scale_line = " " * max_label_len + " └" + "─" * bar_area_width
        if show_values:
            scale_line += " " + str(int(max_value)).rjust(max_valueWidth)
        lines.append(scale_line)

        return "\n".join(lines)

    @staticmethod
    def stacked_bar_chart(
        categories: List[str],
        series: Dict[str, List[float]],
        title: str = "",
        max_width: int = 40
    ) -> str:
        """
        生成堆叠条形图

        Args:
            categories: 类别列表
            series: Dict of series_name -> [values per category]
            title: 图表标题

        Returns:
            ASCII 堆叠条形图字符串
        """
        if not categories or not series:
            return "无数据"

        # 简化实现：显示分类统计
        lines = []
        if title:
            lines.append(f"【{title}】")
            lines.append("")

        symbols = ["▓", "▒", "░", "█", "▄", "▀"]

        for i, category in enumerate(categories):
            category_str = str(category)[:10].ljust(10)
            parts = []
            for j, (series_name, values) in enumerate(series.items()):
                if i < len(values) and values[i] > 0:
                    symbol = symbols[j % len(symbols)]
                    parts.append(f"{symbol}{values[i]:.0f}")

            lines.append(f"  {category_str} │ {' '.join(parts)}")

        return "\n".join(lines)

    @staticmethod
    def _display_width(s: str) -> int:
        """计算字符串的显示宽度（中文字符计为2）"""
        import re
        width = 0
        for char in s:
            if re.match(r'[\u4e00-\u9fa5]', char):  # 中文
                width += 2
            else:
                width += 1
        return width

    @staticmethod
    def _pad_to_width(s: str, width: int) -> str:
        """将字符串填充到指定显示宽度"""
        import re
        current_width = ASCIIGraph._display_width(s)
        padding = width - current_width
        return s + " " * padding

    @staticmethod
    def table(
        headers: List[str],
        rows: List[List[str]],
        title: str = "",
        max_col_width: int = 20
    ) -> str:
        """
        生成 ASCII 表格

        Args:
            headers: 表头
            rows: 数据行
            title: 表格标题
            max_col_width: 最大列宽（按英文字符计）

        Returns:
            ASCII 表格字符串
        """
        if not headers:
            return "无数据"

        lines = []

        # 计算每列显示宽度
        col_widths = [ASCIIGraph._display_width(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    cell_width = ASCIIGraph._display_width(str(cell))
                    col_widths[i] = min(max(col_widths[i], cell_width), max_col_width * 2)  # 中英文混合时放大

        # 表头
        if title:
            lines.append(f"【{title}】")
            lines.append("")

        header_cells = []
        for i, h in enumerate(headers):
            if i < len(col_widths):
                header_cells.append(ASCIIGraph._pad_to_width(h, col_widths[i]))
            else:
                header_cells.append(h)
        header_line = "  " + " │ ".join(header_cells)
        lines.append(header_line)

        # 分隔线
        sep_line = "  " + "─┼─".join("─" * w for w in col_widths)
        lines.append(sep_line)

        # 数据行
        for row in rows:
            row_cells = []
            for i, cell in enumerate(row):
                cell_str = str(cell)
                if i < len(col_widths):
                    # 截断处理（按显示宽度）
                    display_w = ASCIIGraph._display_width(cell_str)
                    if display_w > col_widths[i]:
                        # 截断到最大宽度
                        new_str = ""
                        w = 0
                        for c in cell_str:
                            cw = 2 if re.match(r'[\u4e00-\u9fa5]', c) else 1
                            if w + cw > col_widths[i]:
                                break
                            new_str += c
                            w += cw
                        cell_str = new_str
                    row_cells.append(ASCIIGraph._pad_to_width(cell_str, col_widths[i]))
                else:
                    row_cells.append(cell_str)
            lines.append("  " + " │ ".join(row_cells))

        return "\n".join(lines)

    @staticmethod
    def pie_chart(
        data: Dict[str, float],
        title: str = "",
        max_width: int = 50
    ) -> str:
        """
        生成 ASCII 饼图（简化版）

        Args:
            data: Dict of label -> value
            title: 图表标题
            max_width: 最大宽度

        Returns:
            ASCII 饼图字符串
        """
        if not data:
            return "无数据"

        lines = []
        if title:
            lines.append(f"【{title}】")
            lines.append("")

        total = sum(data.values())
        if total == 0:
            return "无数据"

        symbols = ["●", "○", "◐", "◑", "◕", "◔", "◖", "◗"]
        colors = []  # ASCII 没法真正支持颜色，用符号区分

        for i, (label, value) in enumerate(data.items()):
            percentage = (value / total) * 100
            symbol = symbols[i % len(symbols)]
            lines.append(f"  {symbol} {label}: {percentage:.1f}% ({value:.0f})")

        return "\n".join(lines)


class StatusBadge:
    """状态徽章生成器"""

    # 状态颜色映射（使用 ANSI 颜色代码）
    COLORS = {
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "blue": "\033[94m",
        "gray": "\033[90m",
        "reset": "\033[0m"
    }

    @staticmethod
    def status(status: str, status_type: str = "default") -> str:
        """
        生成状态徽章

        Args:
            status: 状态文本
            status_type: 状态类型 (success/warning/error/info/default)

        Returns:
            带颜色的状态徽章字符串
        """
        color_map = {
            "success": "green",
            "warning": "yellow",
            "error": "red",
            "info": "blue",
            "default": "gray"
        }
        color = StatusBadge.COLORS.get(color_map.get(status_type, "default"), "")
        reset = StatusBadge.COLORS["reset"]

        return f"[{color}{status}{reset}]"

    @staticmethod
    def checkmark(passed: bool) -> str:
        """生成勾选标记"""
        green = StatusBadge.COLORS["green"]
        red = StatusBadge.COLORS["red"]
        reset = StatusBadge.COLORS["reset"]

        if passed:
            return f"{green}✓{reset}"
        else:
            return f"{red}✗{reset}"

    @staticmethod
    def progress_bar(
        current: float,
        total: float,
        width: int = 20,
        show_percentage: bool = True
    ) -> str:
        """
        生成进度条

        Args:
            current: 当前值
            total: 总值
            width: 进度条宽度
            show_percentage: 是否显示百分比

        Returns:
            进度条字符串
        """
        if total <= 0:
            percentage = 0
            filled = 0
        else:
            percentage = min(100, (current / total) * 100)
            filled = int((current / total) * width)

        bar = "█" * filled + "░" * (width - filled)
        result = f"[{bar}]"

        if show_percentage:
            result += f" {percentage:.0f}%"

        return result


def visualize_department_stats(data: Dict[str, Any]) -> str:
    """可视化部门统计（使用 matplotlib 生成图片）"""
    if "employees" in data and isinstance(data["employees"], list):
        names = data["employees"]
        dept = data.get("department", "未知")

        # 使用 matplotlib 生成图片
        output_path = f"./charts/{dept}_members.png"
        chart_path = MatplotlibChart.bar_chart(
            data={name: 1 for name in names},
            title=f"{dept} 成员分布",
            output_path=output_path,
            show_values=False,
            horizontal=True
        )

        return f"![{dept}成员分布]({chart_path})\n\n共 {len(names)} 人"
    return "无数据"


def visualize_performance(scores: List[Dict[str, Any]], name: str = "") -> str:
    """可视化绩效数据"""
    if not scores:
        return "无绩效数据"

    headers = ["季度", "KPI分数", "评级"]
    rows = []

    for s in scores:
        rows.append([
            f"{s.get('year', '')} Q{s.get('quarter', '')}",
            str(s.get('kpi_score', '-')),
            s.get('grade', '-')
        ])

    title = f"{name} 绩效考核" if name else "绩效考核"

    graph = ASCIIGraph()
    return graph.table(headers, rows, title=title)


def visualize_project_status(projects: List[Dict[str, Any]]) -> str:
    """可视化项目状态"""
    if not projects:
        return "无项目数据"

    # 统计各状态项目数
    status_counts = {}
    for p in projects:
        status = p.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    # 状态中文映射
    status_map = {
        "active": "进行中",
        "planning": "计划中",
        "completed": "已完成",
        "on_hold": "已暂停"
    }

    display_counts = {status_map.get(k, k): v for k, v in status_counts.items()}

    graph = ASCIIGraph()
    chart = graph.pie_chart(display_counts, title="项目状态分布")

    # 详细列表
    headers = ["项目名", "状态"]
    rows = []
    for p in projects[:10]:  # 最多显示 10 个
        status = status_map.get(p.get("status", ""), p.get("status", ""))
        rows.append([p.get("name", "")[:15], status])

    table = graph.table(headers, rows, title="项目列表")

    return f"{chart}\n\n{table}"


# 快捷函数
def format_table(headers: List[str], rows: List[List[str]], title: str = "") -> str:
    """快捷表格格式化"""
    return ASCIIGraph.table(headers, rows, title)


def format_bar_chart(data: Dict[str, float], title: str = "") -> str:
    """快捷条形图格式化"""
    return ASCIIGraph.bar_chart(data, title)


def format_status(status: str, status_type: str = "default") -> str:
    """快捷状态格式化"""
    return StatusBadge.status(status, status_type)


def format_progress(current: float, total: float) -> str:
    """快捷进度条格式化"""
    return StatusBadge.progress_bar(current, total)


# ============================================================
# Matplotlib 图表生成器（真实图片）
# ============================================================

import os
from pathlib import Path


class MatplotlibChart:
    """Matplotlib 图表生成器"""

    # 默认中文字体（支持中文显示）
    FONT_SCNAME = "SimHei"  # Windows 黑体
    FONT_NAME = "DejaVu Sans"  # Linux/Mac 备用

    @classmethod
    def _get_font(cls) -> str:
        """获取可用字体"""
        import matplotlib
        matplotlib.use('Agg')  # 非交互式后端
        import matplotlib.pyplot as plt

        # 尝试设置中文字体
        try:
            plt.rcParams['font.sans-serif'] = [cls.FONT_SCNAME, cls.FONT_NAME, 'Arial']
            plt.rcParams['axes.unicode_minus'] = False  # 负号显示
        except Exception:
            pass
        return cls.FONT_SCNAME

    @classmethod
    def _ensure_output_dir(cls, output_dir: str = "./charts") -> str:
        """确保输出目录存在"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        return output_dir

    @classmethod
    def bar_chart(
        cls,
        data: Dict[str, float],
        title: str = "",
        output_path: str = "./charts/bar_chart.png",
        color: str = "#4A90D9",
        show_values: bool = True,
        horizontal: bool = True
    ) -> str:
        """
        生成条形图（matplotlib）

        Args:
            data: Dict of label -> value
            title: 图表标题
            output_path: 输出图片路径
            color: 条形颜色
            show_values: 是否显示数值标签
            horizontal: 是否水平条形图

        Returns:
            输出图片路径
        """
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        cls._get_font()

        output_dir = os.path.dirname(output_path) or "./charts"
        cls._ensure_output_dir(output_dir)

        fig, ax = plt.subplots(figsize=(10, max(4, len(data) * 0.6)))

        labels = list(data.keys())
        values = list(data.values())

        if horizontal:
            bars = ax.barh(labels, values, color=color, height=0.6)
            ax.set_xlabel('数量')
            ax.invert_yaxis()  # 最大值在顶部
        else:
            bars = ax.bar(labels, values, color=color, width=0.6)
            ax.set_ylabel('数量')
            plt.xticks(rotation=15)

        if title:
            ax.set_title(title, fontsize=14, fontweight='bold', pad=15)

        # 添加数值标签
        if show_values:
            for bar in bars:
                width = bar.get_width() if horizontal else bar.get_height()
                label_x = width + max(values) * 0.01
                label_y = bar.get_y() + bar.get_height() / 2 if horizontal else bar.get_x() + bar.get_width() / 2
                ha = 'left' if horizontal else 'center'
                va = 'center' if horizontal else 'top'

                if horizontal:
                    ax.text(label_x, label_y, f'{int(width)}', va=va, ha=ha, fontsize=10)
                else:
                    ax.text(label_y, label_x, f'{int(width)}', va=va, ha=ha, fontsize=10)

        # 设置网格
        ax.grid(axis='x' if horizontal else 'y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)

        # 设置边距
        plt.tight_layout()

        # 保存
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()

        return output_path

    @classmethod
    def pie_chart(
        cls,
        data: Dict[str, float],
        title: str = "",
        output_path: str = "./charts/pie_chart.png",
        colors: list = None
    ) -> str:
        """
        生成饼图（matplotlib）

        Args:
            data: Dict of label -> value
            title: 图表标题
            output_path: 输出图片路径
            colors: 颜色列表

        Returns:
            输出图片路径
        """
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        cls._get_font()

        output_dir = os.path.dirname(output_path) or "./charts"
        cls._ensure_output_dir(output_dir)

        fig, ax = plt.subplots(figsize=(8, 8))

        labels = list(data.keys())
        values = list(data.values())

        # 默认颜色
        if colors is None:
            default_colors = ['#4A90D9', '#50C878', '#FF6B6B', '#FFD93D', '#9B59B6', '#95A5A6']
            colors = [default_colors[i % len(default_colors)] for i in range(len(data))]

        # 分离小扇区
        explode = [0.02] * len(values)

        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            autopct=lambda pct: f'{pct:.1f}%' if pct > 3 else '',
            colors=colors,
            explode=explode,
            startangle=90,
            pctdistance=0.75
        )

        # 设置标签字体
        for text in texts:
            text.set_fontsize(11)
        for autotext in autotexts:
            autotext.set_fontsize(9)
            autotext.set_color('white')

        if title:
            ax.set_title(title, fontsize=14, fontweight='bold', pad=15)

        # 添加图例
        legend_labels = [f'{l} ({v})' for l, v in zip(labels, values)]
        ax.legend(wedges, legend_labels, title="类别", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize=9)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()

        return output_path

    @classmethod
    def grouped_bar_chart(
        cls,
        categories: List[str],
        series: Dict[str, List[float]],
        title: str = "",
        output_path: str = "./charts/grouped_bar.png",
        colors: list = None
    ) -> str:
        """
        生成分组条形图

        Args:
            categories: 类别列表
            series: Dict of series_name -> [values per category]
            title: 图表标题
            output_path: 输出图片路径
            colors: 颜色列表

        Returns:
            输出图片路径
        """
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np

        cls._get_font()

        output_dir = os.path.dirname(output_path) or "./charts"
        cls._ensure_output_dir(output_dir)

        fig, ax = plt.subplots(figsize=(12, 6))

        n_categories = len(categories)
        n_series = len(series)
        bar_width = 0.8 / n_series

        # 默认颜色
        if colors is None:
            default_colors = ['#4A90D9', '#50C878', '#FF6B6B', '#FFD93D', '#9B59B6']
            colors = [default_colors[i % len(default_colors)] for i in range(n_series)]

        x = np.arange(n_categories)

        for i, (series_name, values) in enumerate(series.items()):
            offset = (i - n_series / 2 + 0.5) * bar_width
            bars = ax.bar(x + offset, values, bar_width, label=series_name, color=colors[i])

        ax.set_xlabel('类别')
        ax.set_ylabel('数值')
        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.legend()
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()

        return output_path


def generate_bar_chart_image(data: Dict[str, float], title: str = "图表", output_path: str = "./charts/bar_chart.png") -> str:
    """生成条形图图片（快捷函数）"""
    return MatplotlibChart.bar_chart(data, title=title, output_path=output_path)


def generate_pie_chart_image(data: Dict[str, float], title: str = "分布", output_path: str = "./charts/pie_chart.png") -> str:
    """生成饼图图片（快捷函数）"""
    return MatplotlibChart.pie_chart(data, title=title, output_path=output_path)