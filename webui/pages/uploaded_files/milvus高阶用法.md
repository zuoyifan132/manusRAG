### Milvus数据库高级用法详解

[TOC]

**一句话总结**： **Milvus中的HNSW索引策略适合高性能场景可进行快速召回；Milvus混合搜索可以支持表达式过滤后进行向量搜索加速搜索并提高搜索精度，推荐将chunk中的关键字进行存储并利用关键词进行过滤；Milvus时间旅行可以进行任意时刻的数据搜索；分片与分区提升系统扩展性和查询效率，适合大规模分布式场景。**

#### 1. 引言

Milvus 是一个高性能的开源向量数据库，专为处理大规模向量数据的存储、索引和搜索而设计，广泛应用于图像检索、推荐系统和自然语言处理等场景。本报告聚焦于 Milvus 的四种高级用法：**高级索引技术**、**混合搜索**、**时间旅行（Time Travel）**以及**分片与分区**。

---

#### 2. 高级用法详解

##### 2.1 高级索引技术

###### 解释
Milvus 提供多种索引类型，用于优化向量搜索的性能和准确性。不同的索引类型在速度、准确性和内存使用之间进行权衡，适用于不同规模和需求的数据集。以下是几种常见的高级索引类型及其特点：

- **FLAT**：直接存储原始向量，适合小数据集（数据量少于 10 万），提供 100% 的召回率，但查询速度较慢。
- **IVF_FLAT**：基于倒排文件（Inverted File）的树结构索引，将向量空间划分为多个聚类（簇），适合中大型数据集，兼顾速度和召回率。
- **IVF_SQ8**：在 IVF_FLAT 基础上使用标量量化（Scalar Quantization），将向量压缩为 8 位整数，降低内存占用，适合内存受限场景。
- **HNSW**：基于层次导航小世界图（Hierarchical Navigable Small World）的图结构索引，通过图结构实现高效最近邻搜索，适合高召回率和高性能需求。
- **IVF_PQ**：结合倒排文件和乘积量化（Product Quantization），进一步压缩向量数据，适合超大规模数据集，但可能牺牲部分准确性。

选择合适的索引类型需要根据数据规模、查询频率和硬件资源进行权衡。例如，**HNSW** 适合高性能场景，而 IVF_PQ 更适合内存受限的大规模数据集。

###### 示例
以下是一个创建 **IVF_FLAT** 索引的详细 Python 示例，用于一个包含 128 维向量的集合，模拟图像嵌入的存储和检索场景：

```python
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType

# 连接 Milvus 服务器
connections.connect(host="localhost", port="19530")

# 定义集合 schema
schema = CollectionSchema(
    fields=[
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=128)
    ],
    description="图像嵌入集合"
)

# 创建集合
collection = Collection(name="image_embeddings", schema=schema)

# 准备索引参数
index_params = {
    "index_type": "IVF_FLAT",  # 索引类型
    "metric_type": "L2",       # 距离度量：欧氏距离
    "params": {"nlist": 1024}  # 聚类数量，建议为 4 * sqrt(数据量)
}

# 创建索引
collection.create_index(field_name="embedding", index_params=index_params)
print("IVF_FLAT 索引创建成功！")

# 加载集合以进行查询
collection.load()
```

**代码说明**：

- `nlist` 参数定义了 IVF_FLAT 的聚类数量，建议值为 `4 * sqrt(数据量)`，例如数据量为 100 万时，`nlist` 约为 4000。
- `metric_type` 设置为 `L2`（欧氏距离），也可选择 `IP`（内积）或 `COSINE`（余弦相似度），根据应用场景选择。

###### 原理
索引技术的核心是通过数据结构优化最近邻搜索的效率：
- **FLAT**：直接计算查询向量与所有向量的距离，时间复杂度为 O(n)，适合小数据集。
- **IVF_FLAT**：将向量空间划分为 `nlist` 个簇，每个簇有一个中心点。查询时，先找到最近的簇中心（通过暴力搜索），然后只在这些簇内进行精确搜索，时间复杂度降低到 O(log n + k)，其中 k 为簇内向量数量。
- **IVF_SQ8**：在 IVF_FLAT 基础上，将每个向量分量量化为 8 位整数，减少内存占用（约为原始数据的 1/4），但可能引入量化误差。
- **HNSW**：构建多层图结构，每层节点连接最近邻，查询时从高层逐步导航到低层，时间复杂度接近 O(log n)，适合高性能场景。
- **IVF_PQ**：将向量分割为多个子向量，每个子向量通过乘积量化编码为固定字节，显著降低内存需求，但量化误差可能影响召回率。

###### 推荐指数
- **FLAT**：适合小型数据集（<10 万向量），追求 100% 召回率，推荐指数：⭐⭐。
- **IVF_FLAT**：适合中大型数据集（10 万至 1000 万向量），平衡速度和准确性，推荐指数：⭐⭐⭐⭐。
- **IVF_SQ8/IVF_PQ**：适合超大规模数据集或内存受限场景，推荐指数：⭐⭐⭐⭐。
- **HNSW**：适合高性能需求（如实时推荐），内存充足时优先选择，推荐指数：⭐⭐⭐⭐⭐。

---

##### 2.2 混合搜索

###### 解释
混合搜索（Hybrid Search）允许在向量相似性搜索的同时，结合标量字段的过滤条件。这在需要综合语义相似性和特定属性筛选的场景中非常有用，例如在推荐系统中查找与用户兴趣相似的商品，同时限制商品价格范围或类别。

混合搜索支持复杂的布尔表达式（如 `AND`、`OR`、`>`、`<` 等），可以基于标量字段（如年龄、价格、类别）进行精确过滤。Milvus 2.3 及以上版本支持最多 4 个向量字段的混合搜索，适用于多模态数据场景（如图像+文本嵌入）。

###### 示例
以下是一个混合搜索的详细 Python 示例，假设有一个用户画像数据集，包含用户 ID、128 维嵌入（表示兴趣）和年龄字段，目标是查找与查询向量相似的用户，且年龄大于 25 岁：

```python
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility

# 连接 Milvus 服务器
connections.connect(host="localhost", port="19530")

# 定义集合 schema
schema = CollectionSchema(
    fields=[
        FieldSchema(name="user_id", dtype=DataType.INT64, is_primary=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=128),
        FieldSchema(name="age", dtype=DataType.INT32)
    ],
    description="用户画像集合"
)

# 创建集合
collection_name = "user_profiles"
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)
collection = Collection(name=collection_name, schema=schema)

# 创建索引（假设已有数据）
index_params = {
    "index_type": "IVF_FLAT",
    "metric_type": "L2",
    "params": {"nlist": 1024}
}
collection.create_index(field_name="embedding", index_params=index_params)
collection.load()

# 准备查询向量（假设为用户兴趣嵌入）
query_vectors = [[0.1, 0.2, ... , 0.3]]  # 128 维向量

# 定义搜索参数
search_params = {
    "metric_type": "L2",
    "params": {"nprobe": 10}  # 检查 10 个簇
}

# 执行混合搜索
results = collection.search(
    data=query_vectors,
    anns_field="embedding",
    param=search_params,
    limit=10,  # 返回 Top-10 结果
    expr="age > 25",  # 标量过滤条件
    output_fields=["user_id", "age"]  # 返回字段
)

# 输出结果
for hits in results:
    for hit in hits:
        print(f"用户 ID: {hit.entity.get('user_id')}, 年龄: {hit.entity.get('age')}, 距离: {hit.distance}")
```

**代码说明**：
- `expr="age > 25"` 定义了标量过滤条件，只返回年龄大于 25 岁的用户。
- `output_fields` 指定返回的字段（如 `user_id` 和 `age`），减少数据传输量。
- `nprobe=10` 控制搜索的簇数量，平衡准确性和速度。
- 查询返回的 `hits` 包含每个结果的距离（`distance`）和字段值。

###### 原理
混合搜索的执行流程如下：
1. **标量过滤**：Milvus 首先根据 `expr` 条件（如 `age > 25`）过滤数据集，生成候选集。这一步利用标量字段的索引（如 B 树或位图）快速完成。
2. **向量搜索**：在过滤后的候选集中，执行向量相似性搜索（基于 ANN 算法，如 IVF 或 HNSW）。通过缩小搜索范围，显著提高效率。
3. **结果合并**：将向量搜索的 Top-K 结果与标量字段信息合并，返回最终结果。

混合搜索支持复杂的表达式，例如：
- `price > 100 AND price < 500`
- `category IN ['book', 'electronics']`
- `(age >= 18 AND age <= 30) OR vip == true`

###### 推荐指数
混合搜索非常适合需要综合语义和属性过滤的场景，如个性化推荐、内容搜索等，推荐指数：⭐⭐⭐⭐⭐。

---

##### 2.3 时间旅行（Time Travel）

###### 解释
时间旅行（Time Travel）是 Milvus 提供的一项独特功能，允许用户查询或搜索数据在某个历史时间点的状态。这对于需要访问历史数据快照的场景非常有用，例如：
- 审计系统：检查某时间点的数据是否被篡改。
- 实验回溯：分析模型在不同时间点的表现。
- 数据恢复：恢复到某个时间点的数据状态。

Time Travel 基于时间戳操作，用户可以指定一个时间点，Milvus 将返回该时间点之前的所有有效数据（包括插入但未删除的实体）。

###### 示例
以下是一个使用 Time Travel 的详细 Python 示例，假设有一个日志数据集，包含日志 ID 和 128 维嵌入，目标是查询 2025-01-01 之前的数据状态：

```python
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
from datetime import datetime
import time

# 连接 Milvus 服务器
connections.connect(host="localhost", port="19530")

# 定义集合 schema
schema = CollectionSchema(
    fields=[
        FieldSchema(name="log_id", dtype=DataType.INT64, is_primary=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=128)
    ],
    description="日志嵌入集合"
)

# 创建集合
collection_name = "log_embeddings"
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)
collection = Collection(name=collection_name, schema=schema)

# 创建索引
index_params = {
    "index_type": "HNSW",
    "metric_type": "L2",
    "params": {"M": 16, "efConstruction": 200}
}
collection.create_index(field_name="embedding", index_params=index_params)
collection.load()

# 插入示例数据（模拟不同时间点）
# 假设当前时间为 2025-04-11
vectors = [[0.1, 0.2, ... , 0.3]] * 100  # 100 个 128 维向量
ids = list(range(100))
collection.insert([ids, vectors])

# 模拟 1 小时后删除部分数据
time.sleep(3600)  # 等待 1 小时
collection.delete(expr="log_id in [0, 1, 2]")

# 获取目标时间戳（2025-01-01 00:00:00）
travel_time = datetime(2025, 1, 1)
travel_timestamp = int(travel_time.timestamp() * 1000)  # 转换为毫秒

# 执行 Time Travel 搜索
search_params = {
    "metric_type": "L2",
    "params": {"ef": 64}
}
results = collection.search(
    data=[[0.1, 0.2, ... , 0.3]],  # 查询向量
    anns_field="embedding",
    param=search_params,
    limit=10,
    travel_timestamp=travel_timestamp
)

# 输出结果
for hits in results:
    for hit in hits:
        print(f"日志 ID: {hit.id}, 距离: {hit.distance}")
```

**代码说明**：
- `travel_timestamp` 是毫秒级时间戳，表示目标时间点（2025-01-01）。
- 删除操作发生在当前时间（2025-04-11），但 Time Travel 查询会返回 2025-01-01 时的数据状态，包括已删除的 `log_id` 0、1、2。
- HNSW 索引用于加速搜索，`ef` 参数控制搜索时的扩展范围。

###### 原理
Time Travel 的实现基于以下机制：
1. **时间戳记录**：Milvus 为每次插入和删除操作分配一个时间戳（毫秒级），记录操作发生的时刻。
2. **数据快照**：通过时间戳，Milvus 可以重建某个时间点的数据状态。查询时，系统只返回时间戳小于或等于 `travel_timestamp` 的有效实体（插入但未删除）。
3. **位图过滤**：Milvus 使用位图（bitset）记录实体的有效性，结合时间戳快速过滤出符合条件的实体。
4. **存储管理**：历史数据默认保留 432,000 秒（120 小时），可通过配置 `common.retentionDuration` 延长或缩短。

性能注意事项：
- Time Travel 会增加存储开销，因为需要保留历史操作日志。
- 查询性能可能因数据量和时间跨度而下降，建议为频繁查询的字段创建索引。
- 定期清理过期数据以释放存储空间。

###### 推荐指数
Time Travel 适合需要历史数据审计或回溯的场景，如金融交易、日志分析等，推荐指数：⭐⭐⭐⭐。

---

##### 2.4 分片与分区

###### 解释
- **分片（Sharding）**：将数据水平分割到多个物理节点或虚拟通道上，实现并行写入和查询，适合大规模数据集的高吞吐需求。
- **分区（Partitioning）**：根据用户定义的逻辑分组（如日期、类别）将数据组织成子集，优化特定查询的性能。

分片和分区结合使用，可以显著提升 Milvus 的扩展性和查询效率。例如，在电子商务系统中，可以按商品类别分区（如“电子产品”、“服装”），并通过分片分布到多个节点。

###### 示例
以下是一个创建带分片和分区的集合的详细 Python 示例，模拟一个商品数据集，包含商品 ID、嵌入和类别字段：

```python
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility

# 连接 Milvus 服务器
connections.connect(host="localhost", port="19530")

# 定义集合 schema
schema = CollectionSchema(
    fields=[
        FieldSchema(name="product_id", dtype=DataType.INT64, is_primary=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=128),
        FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=50)
    ],
    description="商品嵌入集合",
    shards_num=4  # 设置 4 个分片
)

# 创建集合
collection_name = "product_embeddings"
if utility.has_collection(collection_name):
    utility.drop_collection(collection_name)
collection = Collection(name=collection_name, schema=schema)

# 创建分区
collection.create_partition("electronics")  # 电子产品分区
collection.create_partition("clothing")     # 服装分区

# 创建索引
index_params = {
    "index_type": "IVF_FLAT",
    "metric_type": "L2",
    "params": {"nlist": 1024}
}
collection.create_index(field_name="embedding", index_params=index_params)
collection.load()

# 插入数据到特定分区
electronics_data = {
    "product_id": [1, 2, 3],
    "embedding": [[0.1, 0.2, ... , 0.3]] * 3,
    "category": ["electronics"] * 3
}
collection.insert(electronics_data, partition_name="electronics")

clothing_data = {
    "product_id": [4, 5, 6],
    "embedding": [[0.4, 0.5, ... , 0.6]] * 3,
    "category": ["clothing"] * 3
}
collection.insert(clothing_data, partition_name="clothing")

# 查询特定分区
search_params = {
    "metric_type": "L2",
    "params": {"nprobe": 10}
}
results = collection.search(
    data=[[0.1, 0.2, ... , 0.3]],
    anns_field="embedding",
    param=search_params,
    limit=5,
    partition_names=["electronics"],  # 只搜索电子产品分区
    output_fields=["product_id", "category"]
)

# 输出结果
for hits in results:
    for hit in hits:
        print(f"商品 ID: {hit.entity.get('product_id')}, 类别: {hit.entity.get('category')}, 距离: {hit.distance}")
```

**代码说明**：
- `shards_num=4` 设置 4 个分片，数据将根据 `product_id` 的哈希值分布到不同分片。
- 创建了两个分区（`electronics` 和 `clothing`），分别存储电子产品和服装数据。
- 查询时通过 `partition_names=["electronics"]` 限制只搜索电子产品分区，减少扫描范围。
- 数据插入时通过 `partition_name` 指定目标分区。

###### 原理
- **分片（Sharding）**：
  - 数据根据主键（如 `product_id`）的哈希值分配到多个分片。
  - 每个分片对应一个虚拟通道（vchannel），映射到物理通道（pchannel）进行存储。
  - 分片实现并行写入和查询，适合高吞吐场景。分片数量（`shards_num`）建议根据节点数和数据量设置，例如 1-8 个分片。
- **分区（Partitioning）**：
  - 分区是逻辑分组，数据按用户定义的标签（如 `category`）存储到不同分区。
  - 查询时可以指定分区（如 `electronics`），只扫描相关数据，减少计算量。
  - 分区不影响物理存储，但通过元数据管理分组信息。

性能优化建议：
- **分片数量**：根据集群规模设置，过多分片可能增加协调开销，建议 2-8 个。
- **分区设计**：选择高区分度的分区键（如类别、日期），避免分区过于细碎。
- **分区查询**：尽量指定 `partition_names`，减少扫描范围。

###### 推荐指数
- **分片**：适合大规模分布式部署，优化写入和查询吞吐量，推荐指数：⭐⭐⭐⭐。
- **分区**：适合数据有自然分组（如按类别、时间）的场景，显著提升查询效率，推荐指数：⭐⭐⭐⭐⭐。

---

#### 3. 总结
Milvus 数据库的高级用法，包括高级索引技术、混合搜索、时间旅行以及分片与分区，为用户提供了强大的工具来处理海量向量数据。这些功能在不同场景下各有优势：
- **高级索引技术**通过优化数据结构，平衡查询速度和准确性。
- **混合搜索**结合向量和标量过滤，满足复杂查询需求。
- **时间旅行**支持历史数据访问，适合审计和回溯。
- **分片与分区**提升系统扩展性和查询效率，适合大规模分布式场景。

---

#### 关键引用
- [Milvus 索引文档](https://milvus.io/docs/index.md)
- [Milvus 多向量搜索文档](https://milvus.io/docs/multi-vector-search.md)
- [Milvus Time Travel 文档](https://milvus.io/docs/v2.2.x/timetravel_ref.md)
- [Milvus 数据处理文档](https://milvus.io/docs/data_processing.md)
- [Zilliz 博客：分片与分区优化](https://zilliz.com/blog/sharding-partitioning-segments-get-most-from-your-database)

