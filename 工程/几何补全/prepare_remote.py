"""Verify task-scoped transport packages before extracting immutable RGB-D copies."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
import time
import numpy as np
from geometry_contract import validate_pose, validate_split
from run_tsdf import sha, atomic, resolve


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--package',required=True)
    a=ap.parse_args();b=Path(a.root);inp=b/'input'
    package=inp/(a.package+'.tgz'); files=json.loads((inp/(a.package+'-files.json')).read_text())
    name='rgbd_dataset_freiburg3_long_office_household'
    with tarfile.open(package) as archive:
        members=archive.getmembers()
        for member in members:
            p=PurePosixPath(member.name)
            if p.is_absolute() or '..' in p.parts or not p.parts or p.parts[0]!=name or not member.isfile():
                raise ValueError('Unsafe or unexpected archive member')
            rel=str(PurePosixPath(*p.parts[1:]))
            if rel not in files: raise ValueError('Unlisted archive member')
            data=archive.extractfile(member).read()
            if hashlib.sha256(data).hexdigest()!=files[rel]: raise ValueError('Transport hash mismatch')
            dst=inp/member.name;dst.parent.mkdir(parents=True,exist_ok=True)
            if dst.exists():
                if sha(dst)!=files[rel]: raise ValueError('Existing data differs; not overwritten')
            else: dst.write_bytes(data)
        if len(members)!=len(files): raise ValueError('Incomplete archive')
    proto=json.loads((inp/'protocol.json').read_text());m=json.loads((inp/'manifest.json').read_text())
    poses=np.array(json.loads((inp/'final-poses.json').read_text()))
    train=m['frames'];validate_split(train,proto['upstream_original_validation'])
    assert not {r['rgb_path'] for r in train} & {r['rgb_path'] for r in proto['upstream_original_validation']}, 'RGB holdout overlap'
    assert len(poses)==len(train)==2253
    assert [r['source_frame'] for r in train]==[r['source_frame'] for r in proto['upstream_original_train']]
    for p in poses:validate_pose(p)
    data=inp/name
    for f,digest in proto['file_hashes'].items():
        assert sha(data/f)==digest, 'Original metadata hash mismatch'
    audit=dict(package=a.package,package_sha256=sha(package),files=len(files),verified=True,
        total_training_frames=len(train),unique_training_depths=len({r['depth_id'] for r in train}),
        repeated_training_depths=len(train)-len({r['depth_id'] for r in train}),
        protocol_sha256=sha(inp/'protocol.json'),manifest_sha256=sha(inp/'manifest.json'),
        timestamp=time.time(),host_path_mapping='prefix relocation only; frozen rows unchanged')
    atomic(b/'verification'/('data-'+a.package+'.json'),audit)
    print('DATA_AUDIT_PASS',json.dumps(audit),flush=True)


if __name__=='__main__':main()
