"""Run pinned MonoGS with an explicit frame limit and observation logs.

Official tracking, mapping, saving and trajectory evaluation remain unchanged.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import hashlib
import random

ROOT = Path(os.environ["MONOGS_SOURCE"]).resolve()
sys.path.insert(0, str(ROOT))
from utils.slam_backend import BackEnd
import torch.multiprocessing as mp


class CheckedProcess(mp.Process):
    registry = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registry.append(self)

    def run(self):
        try:
            super().run()
        except BaseException:
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(1)

    def join(self, timeout=None):
        super().join(timeout)
        if timeout is None and self.exitcode != 0:
            raise RuntimeError(f"child {self.name} exited with {self.exitcode}")


class StopAwareQueue:
    def __init__(self, queue):
        self.queue = queue
        self.stopped = False

    def __getattr__(self, name):
        return getattr(self.queue, name)

    def empty(self):
        return self.stopped or self.queue.empty()


class StopCommandQueue:
    def __init__(self, queue, output):
        self.queue, self.output = queue, output

    def empty(self):
        return self.queue.empty()

    def get(self):
        command = self.queue.get()
        if command[0] == "stop":
            self.output.stopped = True
        return command


class ManagedBackEnd(BackEnd):
    """Release pending observation packets when the official stop loop exits."""
    def run(self):
        import numpy as np
        import torch
        seed = int(os.environ["MONOGS_SEED"])
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        raw_output = self.frontend_queue
        self.frontend_queue = StopAwareQueue(raw_output)
        self.backend_queue = StopCommandQueue(self.backend_queue, self.frontend_queue)
        try:
            super().run()
            print("BACKEND_LOOP_RETURNED", flush=True)
        finally:
            raw_output.cancel_join_thread()
            raw_output.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", type=int, default=40)
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--preset", choices=["official", "fast"], default="official")
    parser.add_argument("--input-fps", type=float, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.frames < 20:
        parser.error("at least 20 frames are required for the smoke run")
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ["MONOGS_RUN_OUTPUT"] = str(args.output)
    os.environ["WANDB_MODE"] = "disabled"
    os.environ["MPLBACKEND"] = "Agg"
    os.environ["MONOGS_SEED"] = str(args.seed)
    os.chdir(ROOT)

    import torch
    import numpy as np
    import cv2
    import torch.multiprocessing as mp
    import yaml
    import wandb
    from evo.tools.settings import SETTINGS
    SETTINGS.plot_backend = "Agg"
    import slam
    slam.BackEnd = ManagedBackEnd
    from utils.config_utils import load_config

    mp.set_start_method("spawn", force=True)
    mp.Process = CheckedProcess
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    config = load_config(os.environ.get("MONOGS_CONFIG", "configs/mono/tum/fr3_office.yaml"))
    config["Dataset"]["dataset_path"] = os.environ["MONOGS_DATA"]
    if args.preset == "fast":
        config["Training"].update(tracking_itr_num=20, mapping_itr_num=30,
                                  init_itr_num=200, window_size=4, pose_window=3)
    config["Results"].update(use_gui=False, use_wandb=False,
                             eval_rendering=False, save_results=True,
                             save_dir=str(args.output))
    with (args.output / "effective-config.yaml").open("w") as handle:
        yaml.safe_dump(config, handle)
    manifest = dict(source=str(ROOT), source_commit=os.environ.get("MONOGS_COMMIT"), config_name=os.environ.get("MONOGS_CONFIG"), seed=args.seed, requested_frames=args.frames,
                    preset=args.preset, input_fps=args.input_fps,
                    wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    config_sha256=hashlib.sha256((args.output / "effective-config.yaml").read_bytes()).hexdigest())
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2))

    original_loader = slam.load_dataset
    arrival_clock = {"origin": None, "scheduled": {}}
    def limited_loader(*pos, **kw):
        dataset = original_loader(*pos, **kw)
        available = len(dataset)
        dataset.num_imgs = min(available, args.frames)
        if args.input_fps > 0:
            original_getitem = type(dataset).__getitem__
            def paced_getitem(instance, index):
                # Fixed-rate virtual arrivals after initialization. Late inputs are
                # retained, so backlog appears as age rather than hidden drops.
                if index >= 1:
                    if arrival_clock["origin"] is None:
                        arrival_clock["origin"] = time.monotonic()
                    deadline = arrival_clock["origin"] + (index-1)/args.input_fps
                    time.sleep(max(0, deadline-time.monotonic()))
                    arrival_clock["scheduled"][index] = deadline
                return original_getitem(instance, index)
            type(dataset).__getitem__ = paced_getitem
        print(f"DATASET available={available} selected={len(dataset)}", flush=True)
        return dataset
    slam.load_dataset = limited_loader

    original_tracking = slam.FrontEnd.tracking
    started = time.monotonic()
    offset = np.zeros(3, dtype=np.float32)
    video = None
    if args.gui:
        (args.output / "gui").mkdir()
        cv2.namedWindow("MonoGS CUDA Demo - WASD/QE move, R reset", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("MonoGS CUDA Demo - WASD/QE move, R reset", 960, 480)
        video = cv2.VideoWriter(str(args.output / "demo.mp4"),
                                cv2.VideoWriter_fourcc(*"mp4v"), 30, (640, 480))
    def observed_tracking(frontend, index, viewpoint):
        for child in CheckedProcess.registry:
            if child.exitcode not in (None, 0):
                raise RuntimeError(f"child {child.name} failed with {child.exitcode}")
        begin = time.monotonic()
        result = original_tracking(frontend, index, viewpoint)
        torch.cuda.synchronize()
        tracking_seconds = time.monotonic() - begin
        if args.gui:
            image = result["render"]
            if np.any(offset):
                import copy
                from gaussian_splatting.gaussian_renderer import render
                camera = copy.copy(viewpoint)
                camera.update_RT(viewpoint.R, viewpoint.T + torch.as_tensor(offset, device=viewpoint.T.device))
                with torch.no_grad():
                    image = render(camera, frontend.gaussians, frontend.pipeline_params, frontend.background)["render"]
            rgb = (image.detach().clamp(0, 1).permute(1, 2, 0).cpu().numpy()*255).astype(np.uint8)
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            cv2.putText(bgr, f"Frame {index} | Gaussians {frontend.gaussians.get_xyz.shape[0]}",
                        (12, 26), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 255, 0), 1)
            cv2.imshow("MonoGS CUDA Demo - WASD/QE move, R reset", bgr)
            if video is not None:
                video.write(bgr)
            if index % 20 == 0 or index == 1:
                cv2.imwrite(str(args.output / "gui" / f"frame-{index:04d}.png"), bgr)
                print(f"GUI_RENDER frame={index}", flush=True)
            key = cv2.waitKey(1) & 255
            for letter, axis, delta in [('a',0,-.05),('d',0,.05),('q',1,-.05),('e',1,.05),('w',2,.05),('s',2,-.05)]:
                if key == ord(letter):
                    offset[axis] += delta
            if key == ord('r'):
                offset[:] = 0
        record = dict(frame=index, wall_seconds=time.monotonic()-started,
                      tracking_seconds=tracking_seconds,
                      gaussians=int(frontend.gaussians.get_xyz.shape[0]),
                      keyframes=len(frontend.kf_indices))
        if index in arrival_clock["scheduled"]:
            record["arrival_to_tracking_complete_seconds"] = time.monotonic()-arrival_clock["scheduled"][index]
            record["input_fps"] = args.input_fps
        with (args.output / "frames.jsonl").open("a") as handle:
            handle.write(json.dumps(record)+"\n")
        print("FRAME " + json.dumps(record), flush=True)
        return result
    slam.FrontEnd.tracking = observed_tracking
    wandb.init(project="MonoGS-local-demo", mode="disabled")
    system = slam.SLAM.__new__(slam.SLAM)
    try:
        system.__init__(config, save_dir=str(args.output))
    except BaseException as error:
        (args.output / "failure.json").write_text(json.dumps(
            dict(type=type(error).__name__, message=str(error)), indent=2))
        for child in mp.active_children():
            child.terminate()
            child.join(timeout=5)
        if hasattr(system, "frontend"):
            for name in ("frontend_queue", "backend_queue", "q_main2vis", "q_vis2main"):
                queue = getattr(system.frontend, name, None)
                if hasattr(queue, "cancel_join_thread"):
                    queue.cancel_join_thread()
        wandb.finish()
        if video is not None:
            video.release()
        cv2.destroyAllWindows()
        raise
    torch.cuda.synchronize()
    summary = dict(frames=len(system.frontend.cameras),
                   keyframes=len(system.frontend.kf_indices),
                   gaussians=int(system.frontend.gaussians.get_xyz.shape[0]),
                   wall_seconds=time.monotonic()-started,
                   peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                   gui=args.gui, torch=torch.__version__,
                   cuda=torch.version.cuda)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
    wandb.finish()
    if video is not None:
        video.release()
    cv2.destroyAllWindows()
    print("COMPLETE " + json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
