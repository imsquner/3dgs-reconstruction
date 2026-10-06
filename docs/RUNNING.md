# 新机预检与两帧运行

所有命令从仓库根目录执行。GPU 运行使用 WSL Ubuntu 22.04 隔离环境，安装步骤见 [ENVIRONMENT.md](ENVIRONMENT.md)。CPU 仓库检查不加载 torch、不执行训练：

```bash
python tools/preflight.py
```

从本项目 Release 下载并解压完整 TUM RGB-D 序列到本机目录，例如 `data/rgbd_dataset_freiburg3_long_office_household`。原始数据按 CC BY 4.0 署名分发；来源与处理说明见 [DATA_ATTRIBUTION.md](DATA_ATTRIBUTION.md)。准备步骤使用公开冻结协议和对应 observations 校验清单，逐文件校验字节及 SHA256，保持图像、姿态、内参、帧号与 holdout 选择，只有宿主路径重映射；不得用任意同名图片替代。

```bash
python -u tools/download_assets.py --dataset tum-office
python -u tools/prepare_dataset.py --scene tum-office --dataset-root data/rgbd_dataset_freiburg3_long_office_household --output-dir host-protocols/office-local
python tools/preflight.py --gpu
python -u tools/run_reconstruction.py --protocol host-protocols/office-local/tum-office.json
```

`--output-dir` 必须为新空目录，不能写入冻结 `协议/`。其他场景使用对应 `<scene>.json` 与 `<scene>-observations.json`，数据集目录必须匹配冻结清单。

统一入口默认两帧、每帧十个优化步、seed=0、original variant、previous pose prior、original association；这会进行原生 GS-ICP 的少量映射优化，是安装后用户主动运行的烟雾测试，不是正式质量实验。每次生成唯一 run id；指定 `--run-id` 时拒绝路径穿越与已有目录。输出位于 `工程/运行/<run-id>/`，包括 manifest、state、heartbeat、summary、PLY 和估计姿态；完成后核对 state 与 worker exitcodes。中断输出保留；在线 tracking 不支持从 PLY 恢复，重新运行必须使用新 id。

底层入口支持 `--protocol /absolute/host-protocol.json`；省略时保持 `协议/<scene>.json` 的历史行为。manifest 记录实际读取的协议绝对路径与 SHA256，不能用冻结文件哈希冒充已映射协议哈希。不要直接运行未映射的 `/datasets/...` 占位路径。

两帧通过仅证明安装、数据读入和 native 入口可执行，不能证明重建质量或跨场景效果。正式批量实验不在本安装流程中。
