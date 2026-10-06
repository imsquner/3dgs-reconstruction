from pathlib import Path
B=Path(__file__).resolve().parent
backup=B/'验证/源铺改版前';backup.mkdir(exist_ok=True)
for name in ['index.html','style.css','app.mjs']:
    if not (backup/name).exists(): (backup/name).write_bytes((B/name).read_bytes())
p=B/'index.html';s=p.read_text(encoding='utf-8')
if 'id="modeGs"' not in s:
    s=s.replace('<select id="contentMode"','<select hidden id="contentMode"')
    anchor='<option value="points">RGB-D观测累积 · 真实TUM室内</option></select>'
    s=s.replace(anchor,anchor+'<div class="mode-switch" role="group" aria-label="展示内容切换"><button id="modeGs" aria-pressed="true"><strong>最终 3DGS</strong><small>自由观察完整观测地图</small></button><button id="modePoints" aria-pressed="false"><strong>观测累积</strong><small>真实 RGB-D 随输入增加</small></button></div><p id="modeNote" class="mode-note">时间轴回放轨迹，最终地图保持不变</p>')
    s=s.replace('<div id="status">正在准备地图…</div>','<div id="status" role="status" aria-live="polite"><div class="load-symbol" aria-hidden="true"></div><strong id="statusLabel">正在准备地图…</strong><progress id="loadProgress" max="100" aria-label="地图加载进度"></progress><small id="statusHint">数据仅在本机读取</small><button id="retry" hidden>重新加载</button></div>')
p.write_text(s,encoding='utf-8')
print('YUANPU_UI_HTML_READY',flush=True)
