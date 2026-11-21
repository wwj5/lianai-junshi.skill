# -*- coding: utf-8 -*-
"""按 skill 规范检查 恋爱军师-skill：frontmatter、体积、引用是否落地。"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import SKILL_DIR
MAX_LINES = 150
MAX_CHARS = 5000

ok = True


def bad(msg):
    global ok
    ok = False
    print("  [X] " + msg)


def good(msg):
    print("  [.] " + msg)


print("== SKILL.md ==")
path = os.path.join(SKILL_DIR, "SKILL.md")
if not os.path.exists(path):
    bad("SKILL.md 不存在")
    sys.exit(1)
text = open(path, encoding="utf-8").read()
lines = text.count("\n") + 1
chars = len(text)
print("  行数 %d（上限 %d）/ 字符 %d（上限 %d）" % (lines, MAX_LINES, chars, MAX_CHARS))
if lines > MAX_LINES:
    bad("行数超限，加载会挤占上下文")
else:
    good("行数合规")
if chars > MAX_CHARS:
    bad("字符超限")
else:
    good("字符合规")

m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
if not m:
    bad("frontmatter 缺失或边界不对")
else:
    keys = re.findall(r"^([A-Za-z0-9_-]+):", m.group(1), re.MULTILINE)
    print("  frontmatter 键：%s" % keys)
    if keys != ["name", "description"]:
        bad("只应有 name 和 description 两个键")
    else:
        good("frontmatter 合规")
    desc = re.search(r"^description:\s*(.+)$", m.group(1), re.MULTILINE)
    if desc:
        d = desc.group(1).strip()
        print("  description %d 字" % len(d))
        if len(d) < 20:
            bad("description 太短，触发不到")
        elif len(d) > 400:
            bad("description 过长")

print("== 引用落地 ==")
refs = re.findall(r"`?(references/[^\s`|,，。]+\.md)", text)
seen = set()
for r in refs:
    if r in seen:
        continue
    seen.add(r)
    p = os.path.join(SKILL_DIR, r.replace("/", os.sep))
    if os.path.exists(p):
        good("%s 存在（%d 字）" % (r, len(open(p, encoding="utf-8").read())))
    else:
        bad("%s 指向不存在的文件" % r)

print("== 残留问题检查 ==")
for name in os.listdir(SKILL_DIR):
    if name.lower().endswith((".txt", ".bak", ".tmp")):
        bad("目录里有杂物：%s" % name)
whole = ""
for f in os.listdir(os.path.join(SKILL_DIR, "references")):
    whole += open(os.path.join(SKILL_DIR, "references", f), encoding="utf-8").read()
if "八档" in whole or "八档" in text:
    bad("还有“八档”字样，与库里 9 个 stage 不符")
else:
    good("阶段档位表述一致")
if "40、短句 98" in whole:
    bad("口吻.md 还是 177 段的旧数字")
else:
    good("口吻数据已更新")

print()
print("结论：" + ("全部通过" if ok else "有项目未通过，见上"))
