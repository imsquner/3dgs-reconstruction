"""Read-only native source/patch/license inventory for the future rerun package."""
import subprocess,json,shutil,importlib.metadata
from pathlib import Path
import torch, simple_knn._C
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;E=B.parents[1];root=E/'源码/GS-ICP-SLAM/submodules'
out=B/'来源/原生依赖';out.mkdir(parents=True,exist_ok=True)
entries={}
specs={'diff-gaussian-rasterization': ['cuda_rasterizer','diff_gaussian_rasterization','ext.cpp','rasterize_points.cu','rasterize_points.h','setup.py','CMakeLists.txt'],
       'fast_gicp':['include','src','python','setup.py','CMakeLists.txt'],
       'simple-knn':['ext.cpp','setup.py','simple_knn.cu','simple_knn.h','spatial.cu','spatial.h','simple_knn']}
for name,paths in specs.items():
 source=(E.parents[1]/'MonoGS/submodules/simple-knn') if name=='simple-knn' else root/name
 commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
 selected=subprocess.check_output(['git','-C',str(source),'ls-files','--',*paths],text=True).splitlines()
 patch=subprocess.check_output(['git','-C',str(source),'diff','--ignore-space-at-eol','--',*paths])
 # Build patch uses LF context; exact source-file hashes separately retain CRLF evidence.
 target=out/(name+'.patch');target.write_bytes(patch.replace(b'\r\n',b'\n'))
 licenses=[]
 for f in ['LICENSE','LICENSE.md','third_party/glm/copying.txt']:
  if (source/f).exists():
   dest=out/name/f;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/f,dest)
   assert sha256(dest)==sha256(source/f);licenses.append({'path':str(dest.relative_to(B)),'sha256':sha256(dest)})
 entries[name]={'commit':commit,'patch_path':str(target.relative_to(B)),'patch_sha256':sha256(target),
                'patch_bytes':target.stat().st_size,'licenses':licenses,
                'license_inventory_note':'No standalone license file present in this local submodule' if not licenses else 'Copied unchanged with hashes',
                'selected_source_exact_hashes':{f:sha256(source/f) for f in selected},
                'patch_scope':paths,'patch_context_eol':'LF; source hashes above are exact bytes, not normalized'}
knn=Path(simple_knn._C.__file__)
try:metadata=importlib.metadata.distribution('simple_knn').read_text('direct_url.json')
except importlib.metadata.PackageNotFoundError:metadata=None
atomic_json(B/'协议/native-source-audit.json',{'sources':entries,'simple_knn':{'binary':str(knn),'sha256':sha256(knn),'direct_url_metadata':metadata},
 'scope':'Current candidate build sources/patches and licenses pinned. Exact relation between historical compiled binaries and these source directories is not yet proven; server build/import/GPU smoke still required. KNN import loads Torch first.'})
print('NATIVE_SOURCE_AUDIT_COMPLETE', {n: e['patch_bytes'] for n,e in entries.items()},'KNN',sha256(knn),flush=True)
