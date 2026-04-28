"""测试 generate_report.py 中的函数"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_report import format_market_cap


def test_format_market_cap_trillion():
    """测试万亿格式化"""
    assert format_market_cap(1_000_000_000_000) == "$1.0T"
    assert format_market_cap(2_500_000_000_000) == "$2.5T"


def test_format_market_cap_billion():
    """测试十亿格式化"""
    assert format_market_cap(1_000_000_000) == "$1B"
    assert format_market_cap(50_000_000_000) == "$50B"


def test_format_market_cap_million():
    """测试百万格式化"""
    assert format_market_cap(1_000_000) == "$1M"
    assert format_market_cap(500_000_000) == "$500M"


def test_format_market_cap_zero():
    """测试零值"""
    assert format_market_cap(0) == "-"
    assert format_market_cap(None) == "-"
