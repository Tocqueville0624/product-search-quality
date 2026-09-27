# 当前状态

更新：2026-09-26。阶段：**本地 MVP 已验证；公开 GitHub 仓库已创建。**

## 已验证

- 环境：项目内 Python 3.11.15、Java 17.0.20.1、PySpark 3.5.7；`uv.lock` 固定依赖。Spark 为单机 `local[4]`、4 GB driver。
- 数据：固定官方 revision 和上游 Git LFS SHA；US 1,818,825 配对、1,215,854 商品。无重复商品键、无未关联配对，join 保持行数。
- 先运行 1,944 条真实查询抽样的特征冒烟，再全量处理。官方 train/test 有 1 个重合查询，从训练侧排除 3 条配对。
- 最终 train 1,113,987 / validation 279,073 / test 425,762 条；三组 query ID 和规范化文本无交叉。
- 17 个原生 Spark 词汇特征，Spark SQL 6 项审计，训练侧 StandardScaler + multinomial logistic regression。
- 开发集比较无权重与逆频率类别权重；按 macro-F1 选择加权模型。测试前冻结源码、模型、特征文件、划分和配置哈希。
- 测试 macro-F1 0.3334；多数类 0.1972。accuracy 降低，Complement precision 仅 4.17%，在 README 与产品备忘录保留这些弱点。
- 同一 predicted-E 池 10% 预算：19,998 条检查，6,575 个模型错误；随机期望 3,972.72。yield 32.88% vs 19.87%，差值的 query-bootstrap 95% 区间 12.11–14.01 pp。
- 23 项聚焦测试通过；独立审查核对官方 test 全部 example ID/标签、冻结顺序和全部哈希。
- `scripts/run_study.py --name verification` 已在独立输出目录完整重跑；结果保留，未覆盖原实验。
- 48 条开发错误已抽样，**人工复核完成数为 0**。生成样本与人工判断严格分开。
- 中文技术 PDF 共 19 页，逐页渲染检查通过；学习资源为官方文档/原始论文。PDF 位于本机 `reports/local/`，不进入 Git。

## 查看入口

补充核查：针对“是否有一模一样的公开分析”复查论文、网页和 GitHub 索引；未找到完整匹配，不能据此证明唯一性。README 和 prior-art 已补充 uncertainty sampling、selective classification 和 PRECISE 的来源与区别；模型、冻结记录和结果未改。

- README：对外项目概览、主要发现、完整复现命令。
- `reports/product-decision-memo.md`：复核运营建议及未来试点。
- `reports/test_metrics.json`、`reports/data_audit.json`、`reports/spark_execution.json`：真实结果和本地 Spark 执行证据。
- `experiments/frozen_study.json` / `test_exposure.json`：测试前冻结与曝光记录。
- `docs/validation-review.md`：独立复核和局限。
- `docs/technical-guide.zh.md`：教程源文档；本地 PDF 可用脚本重建。

## 下一次 Agent 的具体任务

1. 先读 AGENTS、项目目标、评估方案、当前状态和真实结果，不重复声称“尚未实现”。
2. 如用户继续，先帮助其解释模型与指标，完成开发案例的真实人工复核；不以 AI 生成内容冒充人工意见。
3. 再依据开发期证据提出一个有价值的改进，例如语义特征或不同错误成本；旧 test 已被观察，新确认性主张需要新 holdout。
4. 复现冻结设计用新的 `.reproduction/<name>/` 目录；原结果与冻结记录保留。
5. 保留负面结果、版本/数据来源和公开许可，不根据简历叙事挑选指标。

## 尚未完成或不在本期范围

- 无真实人工复核、双人一致性、线上 A/B、转化/收入/工时收益、生产部署。
- 无 AWS 账号、云集群运行或 Spark 相对 pandas 的性能比较。
- 模型不支持自动相关性判定；加权 E 分数未校准。
- 技术与分析部分已具备作品展示价值；用户的理解和面试表达仍需练习，不能保证求职结果。

## 发布与许可

用户本轮已授权在质量确认后分享到 GitHub。仓库：[Tocqueville0624/product-search-quality](https://github.com/Tocqueville0624/product-search-quality)。原始项目代码采用 MIT；ESCI 保留 Apache-2.0 和上游 NOTICE。完整冻结源码已保存于初始提交 `ee8b6ba`；后续清理仅修正包说明中的初始化占位文字，未改变可执行逻辑或指标，见 `experiments/post-freeze-documentation.json`。
