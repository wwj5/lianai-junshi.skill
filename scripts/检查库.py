# -*- coding: utf-8 -*-
"""库体检：字段完整性、标注来源、置信度、标签覆盖。"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import JSONL


def main():
    rows = [json.loads(l) for l in open(JSONL, encoding="utf-8") if l.strip()]
    print("段数 %d，轮数 %d" % (len(rows), sum(r["turn_count"] for r in rows)))

    print("\n[标注来源]")
    print("  stage_method:", dict(collections.Counter(r.get("stage_method") for r in rows)))
    sc = [r.get("stage_score", 0) for r in rows]
    print("  stage_score: 最低 %s / 最高 %s" % (min(sc), max(sc)))
    low = [r for r in rows if r.get("stage_score", 99) <= 1]
    print("  置信度<=1 的段: %d" % len(low))
    manual = sum(1 for r in rows if "阶段为人工标注" in r.get("note", ""))
    rule = sum(1 for r in rows if "关键词规则判定" in r.get("note", ""))
    print("  note 口径: 阶段人工标注 %d 段 / 阶段规则判定 %d 段" % (manual, rule))

    print("\n[标签覆盖]")
    for k in ("女性格", "男性格", "相识", "年龄层", "结果"):
        n = sum(1 for r in rows if any(t.startswith(k + ":") for t in r["tags"]))
        print("  %-4s %3d 段 (%.0f%%)" % (k, n, n * 100.0 / len(rows)))

    print("\n[低置信样本抽查]")
    for r in low[:3]:
        print("  %s  判为 %s  score=%s" % (r["id"], r["stage"], r.get("stage_score")))
        for w, t in r["turns"][:3]:
            print("     %s：%s" % (w, t[:36]))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
