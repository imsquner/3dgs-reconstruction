import sys,json,platform,subprocess,shutil
from pathlib import Path
import torch,numpy,pygicp,diff_gaussian_rasterization
from quality_core import atomic_json,sha256
B=Path(__file__).resolve().parent;E=B.parents[1]
native=[Path(pygicp.__file__),Path(diff_gaussian_rasterization._C.__file__)]
native+=list(Path(pygicp.__file__).parent.glob('libfast_gicp*.so'))
assert len(native)>=3,'GICP linked library not located'
manifest={'python':sys.version,'executable':sys.executable,'torch':torch.__version__,'torch_cuda':torch.version.cuda,'numpy':numpy.__version__,'platform':platform.platform(),'native_files':{str(p):{'sha256':sha256(p),'bytes':p.stat().st_size} for p in native},'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=name,driver_version,memory.total','--format=csv,noheader'],text=True).strip(),'scope':'Runtime pin, not peak-memory measurement; local cu116 binaries cannot be copied to incompatible server Python/Torch.'}
atomic_json(B/'协议/local-runtime.json',manifest)
src=E/'源码/GS-ICP-SLAM/LICENSE';dst=B/'来源/GS-ICP-SLAM/LICENSE'
if dst.exists():assert sha256(src)==sha256(dst)
else:shutil.copy2(src,dst)
print('RUNTIME_PINNED',len(native),manifest['gpu'],flush=True)
