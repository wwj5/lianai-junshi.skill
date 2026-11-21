# -*- coding: utf-8 -*-
"""包内路径：脚本在 scripts\，数据在 data\，全部相对于 skill 根目录。

整个 skill 目录拷到哪都能跑，不需要改这里，也不依赖外部项目。
"""
import os

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPTS_DIR)
JSONL = os.path.join(SKILL_DIR, "data", "新增素材.jsonl")
