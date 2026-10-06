"""Apply the approved compact layout while preserving renderer DOM IDs."""
from pathlib import Path
import re
B=Path(__file__).resolve().parent
p=B/'index.html';html=p.read_text(encoding='utf-8')
if 'id="togglePanel"' in html:
    print('UI_HTML_ALREADY_READY',flush=True)
    raise SystemExit(0)
backup=B/'验证/改版前';backup.mkdir(exist_ok=True)
for name in ['index.html','style.css','app.mjs']:
    q=backup/name
    if not q.exists():q.write_bytes((B/name).read_bytes())
html=html.replace('<body><header>','<body><header><button id="togglePanel" class="iconOnly" aria-label="收起控制面板" aria-expanded="true" aria-controls="controlPanel" title="收起控制面板"><img src="vendor/icons/panel-left.svg" alt=""></button>')
html=html.replace('<i></i>','<img src="vendor/icons/box.svg" alt="">').replace('INTERACTIVE RECONSTRUCTION','实时流式三维场景重建')
html=html.replace('<main><aside>','<main><aside id="controlPanel">')
html=re.sub(r'<h1>.*?</h1><p class="intro">.*?</p>','',html,flags=re.S)
html=html.replace('<section><div class="eyebrow">实验信息</div>','<section class="metrics"><div class="eyebrow">原实验指标</div>')
html=html.replace('实测跟踪吞吐','原实验跟踪吞吐').replace('全帧轨迹误差','轨迹误差 ATE')
html=html.replace('<div class="boundary"><b>展示边界</b>','<details class="boundary"><summary>展示边界与操作说明</summary>')
html=html.replace('</p></div>\n<div class="controlshelp">','</p>\n<div class="controlshelp">')
html=html.replace('</div></aside>','</div></details></aside>')
html=html.replace('<div class="corner"><span class="live-dot"></span>','<div class="corner">')
html=html.replace('<div id="inputPreview" hidden><img','<div id="inputPreview" hidden><button id="toggleInput" aria-expanded="true">收起输入画面</button><img')
html=html.replace('浏览帧率 / 与重建吞吐不同','浏览帧率 · 非重建吞吐')
html=html.replace('相机轨迹时间轴','轨迹回放').replace('左键旋转 / 右键平移 / 滚轮缩放','左键旋转　右键平移　滚轮缩放')
icons={'fullscreen':'maximize','clean':'video','free':'mouse-pointer-2','follow':'route','reset':'rotate-ccw','overview':'scan','save':'bookmark','restore':'camera','play':'play'}
for id,name in icons.items():
    html=re.sub(r'(<button id="'+id+r'"[^>]*>)([^<]+)(</button>)',lambda m:m[1]+f'<img src="vendor/icons/{name}.svg" alt=""><span>'+m[2]+'</span>'+m[3],html)
p.write_text(html,encoding='utf-8')
print('UI_HTML_READY',flush=True)
