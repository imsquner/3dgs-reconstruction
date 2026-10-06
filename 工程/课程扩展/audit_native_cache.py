import cv2,time,hashlib,json
from pathlib import Path
S=Path('/mnt/d/桌面/image/MonoGS/datasets/tum/rgbd_dataset_freiburg3_long_office_household');D=Path('/root/.local/share/monogs/gpt-6/data/tum-office')
files=sorted((S/'rgb').glob('*.png'))[:40];times={}
for p in files:assert hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256((D/'rgb'/p.name).read_bytes()).digest()
for root in [S,D]:
 t=time.perf_counter()
 for p in files:cv2.imread(str(root/'rgb'/p.name))
 times[str(root)]=(time.perf_counter()-t)/len(files)
r=dict(verified_rgb_files=40,cache_counts={'rgb':len(list((D/'rgb').glob('*.png'))),'depth':len(list((D/'depth').glob('*.png')))},cached_image_hashes_match=True,average_rgb_read_seconds=times)
(Path(__file__).resolve().parents[1]/'数据'/'TUM'/'native-cache-audit.json').write_text(json.dumps(r,indent=2));print(r)
