# 相似项目调研与独立贡献边界

核查日期：2026-09-26。范围：公开论文、比赛官方页面、作者维护的 GitHub 项目、AWS/Qdrant 官方文章及上游许可文件。只阅读公开资料；未克隆、运行或复制他人模型实现。

## 判断

“用 ESCI 判断商品搜索相关性”已经是成熟的公开任务。单纯完成四分类、排序或加一个展示界面，与现有项目会高度重合。把自己的工作如实描述为基于公开基准的独立应用研究，并注明来源，是合理的项目定位；没有必要把选题包装成首次提出。

这次核查没有发现需要放弃该选题的证据，但无法穷尽所有公开、未索引或私有项目，也不构成“完全没有相同组合”或“零法律风险”的保证。下列项目的性能数字没有被独立复现，不能直接作为本项目的比较结果。

## 已核查的相似工作

| 来源 | 已有内容与重合点 | 对本项目的影响 |
| --- | --- | --- |
| [Amazon ESCI 数据与基线](https://github.com/amazon-science/esci-data)；[数据论文](https://arxiv.org/abs/2206.06588) | 官方已定义四分类、排序、替代品识别，并提供基线实现 | 数据、标签定义和任务来自这里；必须引用，不能声称自建数据或首创任务 |
| [KDD Cup 2022 官方工作坊](https://amazonkddcup.github.io/) | 收录多支参赛队伍的论文、代码、展示 | 已有大量方法研究；本项目不是新比赛解法或历史参赛记录 |
| [ETS-Lab 方案](https://github.com/wufanyou/KDD-Cup-2022-Amazon)；[作者论文](https://arxiv.org/abs/2208.00108) | 多个 cross-encoder 与 LightGBM 融合，覆盖分类和排序；仓库展示 MIT 许可 | 作为已有方法背景；不复制模型融合、特征或报告结构来冒充独立设计 |
| [shaik2501/Amazon_ESCI](https://github.com/shaik2501/Amazon_ESCI) | FAISS、cross-encoder、ESCI 分类与 Streamlit 串联 | “分类模型加搜索页面”已有很近的个人项目；该仓库首页没有明确授予自身代码许可，不能只因公开就直接复制 |
| [217amin/amazon-esci-search](https://github.com/217amin/amazon-esci-search) | 混合检索、向量压缩、reranking 和演示界面 | 检索模型与部署不是本项目首期的独立贡献 |
| [Huzaifanasir95/Amazon-ESCI-Product-Search](https://github.com/Huzaifanasir95/Amazon-ESCI-Product-Search) | 神经排序、词汇基线、离线指标、Streamlit；作者称为课程作业 | 学生/作品集项目也已有相同大方向；其中成绩属于作者自报，未审核其划分或复现 |
| [albertobarnabo/product-search-embeddings](https://github.com/albertobarnabo/product-search-embeddings) | ESCI 上的 embedding 与 reranker，强调 CPU 推理 | 性能与模型大小权衡已有项目；不能把 CPU 部署作为首创 |
| [esterkane/elastic-product-search-lab](https://github.com/esterkane/elastic-product-search-lab) | Elasticsearch、BM25、混合搜索、离线相关性和延迟评估 | 完整搜索工程和一般离线评估同样属于已有实践 |
| [Qdrant 官方 SPLADE 教程](https://qdrant.tech/articles/sparse-embeddings-ecommerce-part-2/) | 使用 ESCI 微调稀疏检索模型并提供代码 | 不能把跟随教程执行说成原创模型；首期不沿用该训练路径 |
| [AWS 官方 Deequ 教程](https://aws.amazon.com/blogs/big-data/test-data-quality-at-scale-with-deequ/) | 文中使用 ESCI/Shopping Queries 文件演示 Spark 数据质量检查 | “ESCI + Spark + 数据检查”本身也不能作为新颖性主张；仍可独立实现以展示技能 |

## 本项目准备独立完成的工作

在同一份公开数据上，明确提出并验证一个产品质量问题：当人工只复核固定比例的 predicted-Exact 配对时，什么选择规则更容易发现错误？

- 独立实现 PySpark 数据处理，并保存数据来源、关联质量、划分与执行证据。
- 比较简单且可解释的文本模型，审查 Exact 与其他类别之间的混淆。
- 在同一个模型的 predicted-Exact 候选池内，比较等预算随机抽查和基于模型信号的复核排序。
- 预先定义指标、分母、切片和最终测试规则；报告不确定性与无改进结果。
- 手动分析开发集案例，区分模型错误、上下文不足和对发布标签的疑义。
- 写出产品质量建议及未来实验设计，并明确哪些结论只适用于公开数据。

这些是计划中的独立实现与分析，不是对方法学首创性的承诺。置信度排序、人工复核、校准和误差切片都是通用方法；如具体采用某篇论文的方法，继续补充引用。

## 抄袭、版权和引用

美国版权局区分思想/方法与具体表达：一般概念相近不等于复制了受保护的代码、文字或图表。[官方解释](https://www.copyright.gov/what-is-copyright/)

项目诚信还要求如实说明来自他人的数据、方法和实质性启发。即使许可证允许复用，也不能把他人的实现或实验结果说成自己的独立成果。修改文件名或改写句子本身不构成独立贡献。

上游 ESCI 仓库提供 [Apache-2.0 LICENSE](https://github.com/amazon-science/esci-data/blob/main/LICENSE) 和 [NOTICE](https://github.com/amazon-science/esci-data/blob/main/NOTICE)。若分发其受许可覆盖的材料或衍生代码，需要按许可保留相应文件、声明和修改说明。当前初始化只创建本项目说明与结构，尚未引入该数据或模型实现。

具体登记方式见 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。引用链接不等于获得其他仓库代码的复用许可；每次实际引入时核查对应版本。

## 检索记录与局限

使用的主要检索式包括：`ESCI PySpark github`、`Amazon ESCI portfolio`、`Shopping Queries Dataset classification github project`、`Amazon KDD Cup 2022 winning solution github`、`Amazon ESCI error analysis`、`ESCI confidence calibration`、`ESCI Streamlit`。对相关命中进一步打开作者/维护者页面及官方许可文件。

精确措辞检索有漏检，项目 README 不等于经过验证的实现；未读取所有源文件，未做代码相似度审计，也没有把“未看到某功能”当作证明其不存在。开始撰写公开成果时应再核查新增的实质性参考来源。
