"""Vendor a small, pinned set of Lucide SVGs and archive design guidance."""
from pathlib import Path
import urllib.request,json,hashlib
B=Path(__file__).resolve().parent
repo='lucide-icons/lucide'
request=urllib.request.Request(f'https://api.github.com/repos/{repo}/commits/main',headers={'User-Agent':'course-demo'})
commit=json.load(urllib.request.urlopen(request,timeout=30))['sha']
folder=B/'vendor/icons';folder.mkdir(exist_ok=True)
manifest={'repository':repo,'commit':commit,'files':[]}
for name in ['box','panel-left','maximize','video','mouse-pointer-2','route','rotate-ccw','scan','bookmark','camera','image','info','play','pause']:
    data=urllib.request.urlopen(f'https://raw.githubusercontent.com/{repo}/{commit}/icons/{name}.svg',timeout=30).read()
    (folder/(name+'.svg')).write_bytes(data)
    manifest['files'].append({'file':name+'.svg','sha256':hashlib.sha256(data).hexdigest()})
license_data=urllib.request.urlopen(f'https://raw.githubusercontent.com/{repo}/{commit}/LICENSE',timeout=30).read()
(folder/'LICENSE').write_bytes(license_data)
(folder/'manifest.json').write_text(json.dumps(manifest,indent=2))
skill=B/'设计参考/frontend-design';skill.mkdir(parents=True,exist_ok=True)
for name in ['SKILL.md','LICENSE.txt']:
    data=urllib.request.urlopen('https://raw.githubusercontent.com/anthropics/skills/main/skills/frontend-design/'+name,timeout=30).read()
    (skill/name).write_bytes(data)
print('UI_ASSETS_READY',commit,len(manifest['files']),flush=True)
