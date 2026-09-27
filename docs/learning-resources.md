# Learning resources for Product Search Quality

核查日期：2026-09-26。仅列官方文档与原始论文；以下均已打开核验。概念参考固定到 Spark 3.5.7，运行环境以项目实际锁定版本为准；跨版本复制代码前检查对应 API。阅读时间是学习建议。

## 核心路线

| 资源 | 本项目阅读目标 | 建议练习 |
| --- | --- | --- |
| [PySpark DataFrame Quickstart](https://spark.apache.org/docs/3.5.7/api/python/getting_started/quickstart_df.html) | `select`、`filter`、`groupBy`、惰性执行、避免全量 collect | 手工造五个配对，再分别筛选和计数 |
| [Spark SQL and DataFrames](https://spark.apache.org/docs/3.5.7/sql-programming-guide.html) | 两种接口共享执行引擎 | 同一标签计数分别用 DataFrame 与 SQL 表达 |
| [DataFrame.join](https://spark.apache.org/docs/3.5.7/api/python/reference/pyspark.sql/api/pyspark.sql.DataFrame.join.html) | join 类型、键、缺失匹配 | 给商品表加入重复键，预测关联后的行数 |
| [Parquet Files](https://spark.apache.org/docs/3.5.7/sql-data-sources-parquet.html) | 列式存储、schema、磁盘分区布局 | 指出项目每一步实际需要哪些列 |
| [DataFrame.explain](https://spark.apache.org/docs/3.5.7/api/python/reference/pyspark.sql/api/pyspark.sql.DataFrame.explain.html) | 物理/逻辑计划入口 | 在真实计划里找 Scan、Filter、Exchange |
| [DataFrame.cache](https://spark.apache.org/docs/3.5.7/api/python/reference/pyspark.sql/api/pyspark.sql.DataFrame.cache.html) | 复用中间结果及资源代价 | 说明哪个中间结果被多次使用、为何才考虑缓存 |
| [Spark SQL Performance Tuning](https://spark.apache.org/docs/3.5.7/sql-performance-tuning.html) | 分区、广播关联、AQE | 依据计划和实际大小提出一个可测量的优化假设 |
| [RDD Guide: Shuffle](https://spark.apache.org/docs/3.5.7/rdd-programming-guide.html#shuffle-operations) | 数据为何要跨分区重排 | 用配对卡片解释 groupBy 的数据移动；无需重写为 RDD |
| [Cluster Mode Overview](https://spark.apache.org/docs/3.5.7/cluster-overview.html) | driver、executor、cluster manager | 画出本地运行与多节点运行的区别 |
| [Submitting Applications](https://spark.apache.org/docs/3.5.7/submitting-applications.html#master-urls) | `local[n]`、`local[*]` 的意义 | 解释项目实际 master 配置，并说出不能据此声称的经验 |
| [Monitoring and Instrumentation](https://spark.apache.org/docs/3.5.7/monitoring.html) | 作业、阶段、任务与事件日志 | 从一次真实运行找主要耗时阶段 |

## 机器学习与可靠评估

| 资源 | 重点 |
| --- | --- |
| [Spark ML Pipelines](https://spark.apache.org/docs/3.5.7/ml-pipeline.html) | Estimator / Transformer / Pipeline；fit 与 transform 的责任 |
| [Spark Classification and Regression](https://spark.apache.org/docs/3.5.7/ml-classification-regression.html#multinomial-logistic-regression) | 多项逻辑回归、概率输出、正则化的角色 |
| [Spark MulticlassClassificationEvaluator](https://spark.apache.org/docs/3.5.7/api/python/reference/api/pyspark.ml.evaluation.MulticlassClassificationEvaluator.html) | 准确阅读指标定义，避免将内置 f1 名称当作 macro-F1 |
| [scikit-learn Classification Metrics](https://scikit-learn.org/stable/modules/model_evaluation.html#classification-metrics) | Precision、recall、F1、macro/weighted 与混淆矩阵 |
| [scikit-learn Common Pitfalls](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage) | 预处理同样会泄漏；先确定划分，再 fit |
| [GroupShuffleSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupShuffleSplit.html) | 组比例与行比例不同；同组不能随机拆散。此处是概念资料，不代表项目实际调用这个 API |
| [Probability Calibration](https://scikit-learn.org/stable/modules/calibration.html) | 分类、排序和校准是不同问题；校准需独立验证 |

## 任务原始来源

- [Reddy et al. (2022): Shopping Queries Dataset](https://arxiv.org/abs/2206.06588)：数据、四种标签和任务背景。先读数据与任务定义，再看模型基线。
- [Amazon Science 官方 ESCI 仓库](https://github.com/amazon-science/esci-data)：文件 schema、关联键、版本标记和官方 train/test。其报告成绩不能直接当作本项目成绩或未经对齐的比较对象。

## 使用原则

把官方示例当作概念帮助，项目代码依据具体数据约定独立实现。若实际复制或改编任何实质性代码，在 `THIRD_PARTY_NOTICES.md` 记录来源、版本、许可、文件及修改。阅读某份文档不表示使用了该文档展示的全部技术。

优先学会解释本项目的真实选择：观察单位、join、划分、特征、baseline、指标、复核预算、局限。本地 MVP 不要求同时学习流处理、旧式 MapReduce 编程或付费云部署。
