# 索引与性能优化指南

本文档说明针对本项目（支持 Mongo 全文 + SQLite 回退）在数据库层与查询层的索引建议，以及在代码层如何利用索引提高查询性能。

## 总体原则
- 优先在查询的过滤/排序字段上建立索引（例如 `store_id`, `isbn` 等）。
- 对于全文检索，Mongo 使用 `text` 索引，SQLite 使用 FTS5 虚拟表（FTS）以获得高效全文搜索。
- 避免在高并发路径执行未索引的全表扫描；必要时使用分页（limit/offset 或基于游标的分页）。

## MongoDB（全文优先方案）

1) 常见索引

- 全文索引（用于 title/author/description 等）：
```js
// 在 mongo shell 中：
db.books.createIndex({ title: "text", author: "text", description: "text" }, { name: "book_text_idx" })
// 若需要为不同字段设置权重：
db.books.createIndex({ title: "text", description: "text" }, { weights: { title: 10, description: 2 } })
```

- 精确查询索引（用于基于 store 或 isbn 的过滤）：
```js
db.books.createIndex({ store_id: 1 })
db.books.createIndex({ isbn: 1 })
```

2) 查询建议
- 使用 `{$text: {$search: "keyword"}}` 来利用 text 索引。若要在店铺范围内搜索，加上 `store_id` 的过滤以使用复合索引。
- 分页建议：使用 sort + limit（避免大 offset），或使用基于 _id 的游标分页（efficient pagination）。

示例（按店铺分页全文检索）：
```js
db.books.find({ $text: { $search: "python" }, store_id: "store_123" })
  .sort({ score: { $meta: "textScore" } })
  .skip(0).limit(20)
```

3) 注意点
- 如果全文索引覆盖所有需要字段，以 textScore 排序会触发 text 索引；额外的 filter 字段应当也建立索引以避免回表扫描。

## SQLite（回退方案）

1) 使用 FTS5 做全文：

```sql
-- 创建基于 FTS5 的虚拟表（在初始化 DB 时执行）
CREATE VIRTUAL TABLE books_fts USING fts5(title, author, description, content='books', content_rowid='id');

-- 将现有 books 表同步到 books_fts（或使用触发器）
INSERT INTO books_fts(rowid, title, author, description) SELECT id, title, author, description FROM books;
-- 也可创建触发器保持同步（INSERT/UPDATE/DELETE）
```

2) 精确查询索引

```sql
CREATE INDEX IF NOT EXISTS idx_books_store ON books(store_id);
CREATE INDEX IF NOT EXISTS idx_books_isbn ON books(isbn);
```

3) 查询建议
- 用 FTS5 查询全文：
```sql
SELECT b.* FROM books b JOIN books_fts f ON b.id = f.rowid WHERE books_fts MATCH 'python' LIMIT 20 OFFSET 0;
```
- 若需要 store 过滤，请在 join 查询中加入 `b.store_id = ?`。确保 `idx_books_store` 存在以便加速过滤。

## 应用层（代码）优化要点

- 在代码里尽量把过滤条件放到 DB 层（不要先拉大量数据再在 Python 里过滤）。
- 分页使用 limit + offset 对小页码可行；对于深度分页建议使用基于游标/last_id 的分页。
- 对于 Mongo：尽量使用投影（只 select 所需字段）以减少网络与内存开销。
- 避免在循环中重复打开数据库连接；使用长生命周期的连接/客户端池。

## 在本项目的实践建议

- 如果你想启用 Mongo 搜索：在初始化脚本或部署步骤中创建上述 `text` 索引与 `store_id` 索引。
- 如果使用 SQLite 回退：在数据库初始化时创建 FTS5 表与必要的索引。
- 在 `be/model/search.py` 中确认：
  - 当 mongo 可用时构造 `$text` 查询并传入 `store_id` 等 filter；
  - 当 fall back 到 sqlite 时，使用 FTS5 的 MATCH 查询并且在 WHERE 中包含 store_id 的过滤条件。

示例：在部署或 CI 中运行的初始化命令
```bash
# Mongo (mongo shell)
mongo bookstore --eval "db.books.createIndex({ title: 'text', author: 'text', description: 'text' })"
mongo bookstore --eval "db.books.createIndex({ store_id: 1 })"

# SQLite (使用 sqlite3 CLI)
sqlite3 book.db "CREATE INDEX IF NOT EXISTS idx_books_store ON books(store_id);"
```

## 监控与验证
- 对于 Mongo，可以用 `explain()` 检查查询是否使用了索引：
```js
db.books.find({ $text: { $search: 'python' }, store_id: 's1' }).explain('executionStats')
```
- 对于 SQLite，使用 `EXPLAIN QUERY PLAN` 来查看是否使用索引：
```sql
EXPLAIN QUERY PLAN SELECT * FROM books WHERE store_id = 's1' AND title LIKE '%python%';
```

---

