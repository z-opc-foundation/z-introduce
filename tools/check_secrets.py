#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""z-introduce 站点上线前凭据自查：确认 data.json 不含口令、密钥、内网地址或本地绝对路径。"""
import json
import re
import sys

BLOB = json.dumps(json.load(open("assets/data.json", encoding="utf-8")), ensure_ascii=False)

PATTERNS = {
    "明文口令": r"(?i)(?:password|passwd|pwd)\s*[:=]\s*[^,}\s]{4,}",
    "密钥赋值": r"(?i)(?:secret|token|apikey|api_key|access_key|secret_key)\s*[:=]\s*[^,}\s]{6,}",
    "私钥块": r"BEGIN [A-Z ]*PRIVATE KEY",
    "云厂商 AK": r"(?:LTAI|Sk-|AKIA)[A-Za-z0-9]{12,}",
    "内网 IP:PORT": r"\b\d{1,3}(?:\.\d{1,3}){3}:\d{2,5}\b",
    "JDBC 连接串": r"jdbc:\w+://",
    # 真凭据的 base64 特征：带 = padding，或 4 个以上大写+数字+小写混合段
    "长 base64 串": r"\b(?:[A-Za-z0-9+/]{40,}={1,2}|(?=[A-Za-z0-9+/]*[A-Z])(?=[A-Za-z0-9+/]*[a-z])(?=[A-Za-z0-9+/]*[0-9])[A-Za-z0-9+/]{40,})\b",
    "Bearer 令牌": r"(?i)bearer\s+[A-Za-z0-9._-]{20,}",
}

bad = False
for label, pat in PATTERNS.items():
    hits = re.findall(pat, BLOB)
    if hits:
        bad = True
        print("  [!] %-12s -> %s" % (label, hits[:4]))
    else:
        print("  [ok] %-12s 无" % label)

print("\n外链清单（部署后页面会指向这些地址）：")
for u in sorted(set(re.findall(r"https?://[^\"\s,}]+", BLOB))):
    print("  ", u)

paths = set(re.findall(r"/Users/[^\"\s,}]+", BLOB)) | \
        set(re.findall(r"/home/[^\"\s,}]+", BLOB))
print("\n本地绝对路径：", paths or "无")

print("\n结论：", "存在敏感信息，需清理后再上线" if bad else "未发现凭据 / 密钥 / 内网地址")
sys.exit(1 if bad else 0)
