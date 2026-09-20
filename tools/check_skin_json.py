# -*- coding: utf-8 -*-
"""检查 pip 模式导出的 skin JSON 是否自包含、调色板是否正确。"""
import json
import os

p = r"C:\Users\admin\.genshen-cp8\deepking\genshen-cp8.skin.json"
d = json.load(open(p, encoding="utf-8"))
lum = lambda c: (0.299 * int(c[1:3], 16) + 0.587 * int(c[3:5], 16)
                 + 0.114 * int(c[5:7], 16)) / 255.0  # noqa: E731

print("文件大小      : %.1f KB" % (os.path.getsize(p) / 1024.0))
print("id            :", d["id"])
print("name          :", d["name"])
print("source        :", d.get("source"))
print("槽位数        : light=%d dark=%d" % (len(d["palettes"]["light"]), len(d["palettes"]["dark"])))
print("light.bg      :", d["palettes"]["light"]["bg"], " 亮度 %.2f" % lum(d["palettes"]["light"]["bg"]))
print("dark.bg       :", d["palettes"]["dark"]["bg"], " 亮度 %.2f" % lum(d["palettes"]["dark"]["bg"]))
print("accent        : light=%s dark=%s" % (d["palettes"]["light"]["accent"], d["palettes"]["dark"]["accent"]))
print()
m = d.get("mascot", {})
for k in ("light", "dark"):
    v = m.get(k) or ""
    kind = "data URI (自包含)" if v.startswith("data:image") else \
           ("raw URL (需联网)" if v.startswith("http") else "无")
    print("mascot.%-6s: %-22s %s" % (k, kind, v[:48]))
print()
ok = (len(d["palettes"]["light"]) == 32 and len(d["palettes"]["dark"]) == 32
      and lum(d["palettes"]["light"]["bg"]) > 0.6
      and lum(d["palettes"]["dark"]["bg"]) < 0.4
      and (m.get("light") or "").startswith("data:image"))
print("自检:", "PASS —— 亮/暗分离、32 槽位齐、图片自包含" if ok else "FAIL")
