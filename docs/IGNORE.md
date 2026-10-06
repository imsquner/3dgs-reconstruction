# 入库与忽略规则

提交：算法模块、历史实验脚本与测试、网页代码、网页依赖及其许可证、固定版本清单、场景协议、网站 JSON 元数据、文档。

忽略：原始数据、运行结果、日志、缓存、虚拟环境、编译依赖、地图、模型权重、录像、压缩包和凭据。数据和产物目录采用目录规则；地图与权重采用扩展名规则。

不全局忽略 JSON、YAML、TXT、PNG 或 JPG：它们可能是配置、校准或网页素材。不要使用 `git add -f` 绕过规则上传产物。

网站地图、输入图片、录像及三份 TUM 原始数据通过 v0.1.0-assets Release 提供，清单为 `release-assets.json`。运行 `python tools/download_assets.py --website` 安装网站基础包；Replica 包须先接受研究许可。数据集仍不进入 Git 历史。

`.gitignore` 不会取消已经跟踪的文件；新增文件提交前仍须检查 `git diff --cached --stat` 和内容。已泄露的凭据需要撤销，不能靠新增 ignore 解决。
