# DeepFurniture 家具风格识别与个性化设计——复现与补充材料

## 1. 版本与真实性

本包是论文方法的**可执行补充材料骨架**，包括可核查的官方元数据、标签对照与人工核验规则、图像身份索引生成程序、近重复检查、样本拆分、图像预处理、核验统计和模型参数配置。

**不包含12,500张已经筛选的家具图像或其真实身份编号。** 原始图像数据仓库总大小约43.5GB，当前未获得原始图像数据；不能在未读取该数据前生成可信的12,500行真实索引。因此，`release/`内的 CSV 是字段齐全的空清单，避免将虚构编号冒充已经执行的实验。程序从真实的DeepFurniture原始标注生成索引；没有足够的已核验样本时会报错，绝不自动虚构数据。

原始数据集：<https://huggingface.co/datasets/byliu/DeepFurniture>

官方说明：约24,000场景图，170,000家具实例，20,000独立家具身份。仓库页面标记AFL-3.0，且其内部 `dataset_info.json` 仍有未填的许可字段；使用前须核查授权与再分发条款。原图不随此包再分发。

`source_metadata/`的3个小型JSON根据Hugging Face仓库公开页内容转录，包含11个风格标签、11个家具类别和数据集元信息。**其内容来自真实公开页面，并非人为构造的论文五类别标签。**

## 2. 目录

- `source_metadata/`：公开元数据的小文件副本（注明来源）；不含图像。
- `config/study_protocol.json`：论文已公开模型与数据处理参数，以及缺失参数的明确状态。
- `config/raw_to_target_mapping_review.csv`：五种目标类别候选映射（仍需人工逐条核验）。
- `scripts/00_fetch_dataset.sh`：下载与解压官方资源。
- `scripts/01_inventory.py`：从真实场景注释生成 `sample_id`、`identityID`、原标签和图像路径。
- `scripts/02_make_review.py`：生成独立双人标注表。
- `scripts/02b_duplicate_audit.py`：提取pHash和近重复候选对。
- `scripts/03_build_splits.py`：基于真实人工审核标签划分5×5×500的数据集。
- `scripts/04_preprocess.py`：根据官方场景与实例分割生成分类/生成图、掩码和256点轮廓。
- `scripts/05_validate.py`：核对12500、8750/1875/1875、产品身份分组和跨split近重复。
- `scripts/06_label_kappa.py`：从两个独立标注记录计算风格与类别的科恩卡帕系数。
- `release/`：可公开发布的索引/切分/审核输出位置（当前仅空表和状态说明）。
- `protocols/`：人工核验、去重、样本划分、实验重建边界。
- `tests/`：自检脚本，仅使用合成测试夹具，不混入研究数据。

## 3. 使用顺序

推荐Python 3.10以上，另行安装 Git LFS（按官方资源要求）。

```bash
python -m pip install numpy Pillow opencv-python-headless pycocotools huggingface_hub
bash scripts/00_fetch_dataset.sh ./DeepFurniture

python scripts/01_inventory.py \
  --root ./DeepFurniture/uncompressed_data \
  --output ./data_index/source_instances.csv

python scripts/02_make_review.py \
  --inventory ./data_index/source_instances.csv \
  --output ./data_index/review.csv
```

根据原始图像和标签完成双人核验，填入 `review.csv` 六项标注字段并更新decision。需人工剔除其他风格、凳/架类、模糊风格、损坏图像；不允许整表无核验地改为approved。

```bash
python scripts/02b_duplicate_audit.py \
  --root ./DeepFurniture/uncompressed_data \
  --inventory ./data_index/source_instances.csv \
  --review ./data_index/review.csv \
  --out-dir ./data_index/duplicate_audit
```

检查 `near_duplicate_pairs_review.csv`，去掉确认重复的候选，再运行02b。**没有未解决的近重复候选对**后生成真实数据拆分：

```bash
python scripts/03_build_splits.py \
  --inventory ./data_index/source_instances.csv \
  --review ./data_index/review.csv \
  --near-duplicate-pairs ./data_index/duplicate_audit/near_duplicate_pairs_review.csv \
  --output ./release/master_index.csv \
  --seed 2024

python scripts/05_validate.py \
  --master ./release/master_index.csv \
  --root ./DeepFurniture/uncompressed_data \
  --phashes ./data_index/duplicate_audit/phashes.csv \
  --out ./release/validation_report.json

python scripts/04_preprocess.py \
  --root ./DeepFurniture/uncompressed_data \
  --split-file ./release/master_index.csv \
  --output-dir ./processed_images

python scripts/06_label_kappa.py \
  --review ./data_index/review.csv \
  --out ./release/annotation_agreement.json
```

正常发布条件：`validation_report.json` 中 `passed=true`，有12500个真实且已复核的样本，训练/验证/测试各为8750/1875/1875，25个类别组合各为500张。若原始数据不足或人工核验尚未完成，脚本会**拒绝生成假配额**；此时只能披露当前筛选结果，不能仍宣称数据与论文中已经报告的12,500规模一致。

## 4. 与论文审稿意见的对应

- **数据来源和全球文化覆盖**：元数据与候选标签映射清楚区分原始11类和研究使用的5类，跨文化泛化不能通过重命名得到证明。
- **近重复图像**：64位pHash与距离阈值8，保留审计对及人工审核决定，复现实验可重新计算被删除图片数量。
- **标签一致性**：保留两名独立标注者的表格，可计算κ；已发表 κ=0.87/0.92不能代替原始记录。
- **数据可得性与复现**：公开真实样本身份索引、训练/验证/测试文件、标签对应表、参数JSON与预处理脚本；原始图片通过官网单独获取。
- **模型参数**：包含ResNet-50、CSS尺度、RBF MKL-SVM及cGAN的已披露参数；未披露损失权重不猜测。

## 5. 引用来源

Liu B, Zhang J, Zhang X, Zhang W, Yu C, Zhou Y. Furnishing Your Room by What You See: An End-to-End Furniture Set Retrieval Framework with Rich Annotated Benchmark Dataset. arXiv:1911.09299 (2019).

公开页面：<https://huggingface.co/datasets/byliu/DeepFurniture>

本包的代码和审核流程属于为复现目的编写的实现；原图、原标签及原数据集标注权利由原数据提供方保留。
