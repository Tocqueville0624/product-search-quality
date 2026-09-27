# 数据约定

## 来源与版本

使用 [amazon-science/esci-data](https://github.com/amazon-science/esci-data)，原论文 [Reddy et al., 2022](https://arxiv.org/abs/2206.06588)。现已下载并验证 revision `7916cdf6ab75a462e77f20ab40428a10923998d5`；真实规模和校验见 `data/manifests/source.json`、`reports/data_audit.json`。

首次获取时固定上游 commit/revision，记录每个文件的来源 URL、获取时间、字节数、SHA-256、许可 URL、读取后的行数/schema、解析异常。下载脚本应检测 Git LFS 指针或 HTML 错误页，不能只凭文件名认定得到 Parquet。

上游 README 的大版本总行数在正文和表格有小幅出入；文档中的约 262 万/US 约 182 万仅作容量规划。处理规模、训练规模、查询数量、商品数量必须分开实测，不能从 README 数字直接生成简历成绩。

## 表和关联

| 文件 | 重要字段 | 用途 |
| --- | --- | --- |
| `shopping_queries_dataset_examples.parquet` | example_id, query, query_id, product_id, product_locale, esci_label, small_version, large_version, split | 查询—商品标签配对与官方划分 |
| `shopping_queries_dataset_products.parquet` | product_id, product_locale, product_title, product_description, product_bullet_point, product_brand, product_color | 商品文本与元数据 |
| `shopping_queries_dataset_sources.csv`（可选） | query_id, source | 来源审计；不作为模型捷径 |

首期过滤：`product_locale == "us"` 且 `large_version == 1`。关联键为 `(product_locale, product_id)`，采用保留配对的 left join。关联前断言商品键唯一；若存在冲突，先调查再指定确定性规则，不能随意丢一条。关联后计数应能解释，单独报告无匹配/缺失标题的配对及处置。

核查 example ID、query ID 和 pair key 的真实唯一性，不先假设。保留来源列供审计，但特征只能使用预测时可得的信息。

## 数据范围与标签

E/S/C/I 是发布者给出的人工相关性判断，不是点击、购买、用户满意度或线上事件。按官方定义使用；发现疑似标注错误时新增复核记录，不覆盖上游标签。

这些查询与候选商品是基准样本，既不是完整商品库，也不是平台真实流量样本。数据没有提供的成本、点击、时间和人口属性不得生成后冒充观察数据。

## 本地存储与版本控制

- 原始下载：`data/raw/`，视为只读输入。
- 清洗/特征：`data/processed/`，由脚本重建。
- 临时调试：`data/samples/`，按 query group 抽样并记录 seed 和选中 ID。
- 可跟踪的小型元数据：`data/manifests/` 中的来源与校验清单。
- 大文件、原始商品文本、模型、逐条预测和日志默认不进 Git；只跟踪配置、少量汇总与必要的合成测试样例。

不要使用雇主/客户数据，也不要额外抓取电商网站来填补字段。未来若引入其他数据集或预训练模型，独立核验许可、版本和与测试集重合的可能性。
