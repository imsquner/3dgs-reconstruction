# 团队协作

1. 克隆仓库，准备依赖与私下共享的资产。
2. 更新主分支：`git switch main`，`git pull --ff-only`。
3. 新建分支：`git switch -c feature/your-task`。
4. 按任务边界修改，保留配置、种子和失败记录。实验产物不提交 Git。
5. 检查差异，运行相关测试，再 commit 和 push。
6. 创建 Pull Request，说明改变、验证结果、失败与限制，审阅后合并。

不要提交 token、私钥、服务器账号或未获再分发许可的数据；不要根据测试集修改模型或选优。不要改动冻结协议来掩盖输入、分割或预算变化。

网站测试：`node --test 工程/交互演示/test_*.mjs`（Windows PowerShell 使用 Get-ChildItem 展开文件）。算法测试在算法目录按文件运行，不直接运行批训练脚本。
