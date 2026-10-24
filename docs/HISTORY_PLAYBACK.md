# 原生高斯历史回放接入

本轮只同步历史播放器源码、原始PLY预取模块及相关测试。当前本机演示目录是验收基准，Git仓库不是大模型和历史输入的分发包。

## 路线与入口

历史C保留原生Viewer的 `optimizeSplatData:true` 与 `addSplatScene`：原始PLY先校验SHA，再由原生库解析、整理、建空间树、排序、上传和高斯渲染。C只提前读取下一份原始PLY，读取和SHA串行，取消后不发布旧结果。没有启用旧预处理缓存、Worker直接缓冲、紧凑纹理或自定义上传。

验收通过后，历史入口默认C；`hybrid=0` 为原生A回退，`hybrid=1`显式C，`short=1`约12秒后暂停。不要在完整录制链接保留 `short=1`。

## 历史资产是可选项

仓库现有目录有意关闭未分发的观测累计资产。本轮不复制本机catalog中的观测累计开关，避免把其他四个模式开启成404；也不覆盖现有README、docs/ASSETS.md和下载脚本的改动。

要在另一份检出启用历史模式，需要完整安装：

1. `工程/交互演示/assets/history-publications.json`。
2. registry指向的 `assets/history-published/{dataset}/{run_id}/index.json` 与逐帧RGB/Depth预览。
3. 服务器 `HISTORY_ROOT` 指向的实际运行目录：`工程/GSICP历史快照/运行/{run_id}/snapshot-index.json` 及其全部 `snapshots/*.ply`。保留原始SHA与索引，不生成替代地图。
4. 在该检出的catalog中为已安装资产启用历史路由（本机当前演示目录已配置，勿重复追加）：

```javascript
findSequence('replica').sequence.history='/history/replica/index.json';
findSequence('tum-full-gsicp10').sequence.history='/history/tum/index.json';
```

仅安装最终模型的检出保持原目录功能；本轮源码同步不等于历史大资产已发布。历史运行也不覆盖静态“最终3DGS”模型，两入口目前来源不同。

## 校验

```powershell
cd 工程/交互演示
node test_history_raw_load.mjs
node test_history_raw_prefetch.mjs
node test_native_history_route.mjs
node test_history_playback.mjs
node test_history_map.mjs
```

这些测试验证原始字节/SHA/取消、单槽串行与回退、原生加载路线和时间线生命周期。它们不替代浏览器画质和完整播放验收。

本机2026-10-20验收证据在 `gpt-6/工程/GSICP服务器测试/验收/混合加载完整验收`：同PLY/同相机/同分辨率18组A/C与18组A/AA稳定画面完全一致，Replica1801输入/190地图、TUM2515输入/277地图全序列同步通过。性能数值与尚未解决的原生切图停顿以该目录最终报告为准，不能将浏览器加载或FPS称为SLAM算法吞吐。

未重新训练、未修改高斯参数、未将最终出生顺序伪装成历史状态；未commit/push或上传大资产。
