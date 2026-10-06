"""Fetch pinned upstream code; does not install dependencies or train."""
from pathlib import Path
import subprocess,json,hashlib
R=Path(__file__).resolve().parents[1];E=R/'工程';B=E/'课程扩展/TUM跨场景迭代'
def run(*args):subprocess.run(args,check=True)
def fetch(path,url,commit):
    if path.exists():
        head=subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()
        if head!=commit:raise RuntimeError('Existing source has a different version: '+str(path))
        return
    path.parent.mkdir(parents=True,exist_ok=True)
    run('git','init',str(path));run('git','-C',str(path),'remote','add','origin',url)
    run('git','-C',str(path),'fetch','--depth','1','origin',commit)
    run('git','-C',str(path),'checkout','--detach','FETCH_HEAD')
    print('PINNED',path,commit,flush=True)
url='https://github.com/Lab-of-AI-and-Robotics/GS_ICP_SLAM.git';commit='5f996a872a979406b270fe0ee3b0a8f25c5e9ae3'
for path in [E/'源码/GS-ICP-SLAM',B/'来源/GS-ICP-SLAM']:fetch(path,url,commit)
manifest=json.loads((B/'来源/source-manifest.json').read_text())
for name,expected in manifest['files'].items():
    actual=hashlib.sha256((B/'来源/GS-ICP-SLAM'/name).read_bytes()).hexdigest()
    if actual!=expected:raise RuntimeError('Source snapshot mismatch: '+name)
for name,url,commit in [
 ('fast_gicp','https://github.com/Lab-of-AI-and-Robotics/fast_gicp.git','e2954b1aa06a563d1b2ef2ec5d1fddd1e911d8f4'),
 ('diff-gaussian-rasterization','https://github.com/Lab-of-AI-and-Robotics/diff-gaussian-rasterization.git','95dbb69d81449ae56783628803198bea2f42e2c9'),
 ('simple-knn','https://github.com/camenduru/simple-knn.git','44f764299fa305faf6ec5ebd99939e0508331503')]:
    path=E/'源码/GS-ICP-SLAM/submodules'/name
    if path.is_dir() and not any(path.iterdir()):path.rmdir()
    fetch(path,url,commit)
    patch=B/'来源/原生依赖'/(name+'.patch')
    if patch.exists() and patch.stat().st_size:
        check=subprocess.run(['git','-C',str(path),'apply','--reverse','--check',str(patch)],capture_output=True)
        if check.returncode:run('git','-C',str(path),'apply','--check',str(patch));run('git','-C',str(path),'apply',str(patch))
print('UPSTREAM_READY: compile dependencies separately; no experiments started',flush=True)
