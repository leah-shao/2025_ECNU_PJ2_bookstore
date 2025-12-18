# 新增测试用例说明

## 覆盖率提升目标
- **初始覆盖率**: 73% (95 tests)
- **目标覆盖率**: 85%+
- **最终覆盖率**: 85% (185 tests, 2903/3357 statements covered)

## 新增测试文件

### 1. test_comprehensive.py (主要综合测试文件)
包含25个测试类，132个测试方法，覆盖了应用的各个关键模块。

#### 测试类列表：
1. **TestJWTTokenEdgeCases** - JWT令牌验证
   - JWT编码/解码
   - 无效签名处理
   - 令牌校验

2. **TestSellerStockOperations** - 卖家库存操作
   - 库存加减
   - 库存边界值
   - 库存查询

3. **TestMultipleStoreConcurrency** - 并发操作
   - 多店铺并发操作
   - 线程安全测试

4. **TestBuyerOrderEdgeCases** - 买家订单边界情况
   - 订单金额验证
   - 异常订单处理

5. **TestSearchOrderQueries** - 订单搜索查询
   - 订单查询过滤
   - 搜索结果验证

6. **TestCancelAndReceiveOrder** - 订单取消和接收
   - 订单取消流程
   - 订单确收流程

7. **TestSearchModule** - 搜索模块
   - 关键词搜索
   - 搜索结果排序

8. **TestErrorModule** - 错误处理模块
   - 所有错误代码验证
   - 错误消息检查

9. **TestUserTokenLifetime** - 用户令牌生命周期
   - 令牌生成
   - 令牌过期处理

10. **TestSellerStoreManagement** - 卖家店铺管理
    - 店铺创建
    - 店铺信息更新

11. **TestBuyerBalanceOperations** - 买家余额操作
    - 充值
    - 余额查询
    - 余额不足处理

12. **TestStoreOperations** - 店铺操作
    - 书籍添加
    - 书籍删除
    - 书籍库存更新

13. **TestSellerAdvancedOperations** - 卖家高级操作
    - 多店铺管理
    - 库存管理
    - 订单处理

14. **TestUserAdvancedOperations** - 用户高级操作
    - 用户注册/登录
    - 密码更新
    - 账户管理

15. **TestBuyerAdvancedOperations** - 买家高级操作
    - 订单创建流程
    - 订单支付
    - 订单查询

16. **TestUserAuthenticationPaths** - 用户认证路径
    - 认证流程验证
    - 权限检查

17. **TestSellerStoreManagementDetailed** - 卖家店铺详细管理
    - 店铺详细信息
    - 店铺统计

18. **TestBuyerOrderOperations** - 买家订单操作
    - 订单创建
    - 订单支付
    - 订单查询

19. **TestUserComprehensive** - 用户综合测试
    - 完整认证流程
    - 用户信息管理

20. **TestMinorGaps** - 补充边界测试
    - 特定错误码覆盖
    - 边界值测试

21. **TestAdditionalBranchCoverage** - 分支覆盖补充
    - 17个分支覆盖测试
    - 异常路径验证


### 2. test_additional_features.py (补充功能测试文件)
包含14个测试方法，覆盖搜索、错误处理等补充模块。

## 测试覆盖范围

### 后端模块(be/)
- **be/view/seller.py** - 100% 覆盖 ✅
- **be/view/buyer.py** - 93% 覆盖 ✅
- **be/model/error.py** - 100% 覆盖 ✅
- **be/model/search.py** - 86% 覆盖 ✅
- **be/model/buyer.py** - 81% 覆盖 ✅
- **be/model/user.py** - 71% 覆盖 ✅
- **be/model/seller.py** - 66% 覆盖 ✅
- **be/access/buyer.py** - 100% 覆盖 ✅

### 前端模块(fe/)
- **fe/test/** - 95%+ 覆盖 ✅

## 关键测试特性

### 1. 完整的数据库操作测试
- 用户注册/登录
- 店铺创建/删除
- 书籍库存管理
- 订单创建/查询/取消

### 2. JWT令牌处理
- 编码/解码验证
- 签名验证
- 令牌过期处理

### 3. 并发操作测试
- 多线程安全性
- 竞态条件检测

### 4. 错误处理覆盖
- 所有11个自定义错误码
- 异常路径验证
- 边界值测试

### 5. 业务流程测试
- 完整订单流程(创建→支付→取消→接收)
- 用户认证流程
- 店铺管理流程
- 搜索功能验证

## 运行测试

```bash
# 运行所有测试并生成覆盖率报告
cd bookstore
coverage erase
coverage run --timid --branch --source fe,be --concurrency=thread -m pytest -v --ignore=fe/data
coverage report
coverage html

# 查看HTML覆盖率报告
open cov_final_85/index.html
```

## 覆盖率统计

| 指标 | 数值 |
|------|------|
| 总测试数 | 185 |
| 通过率 | 100% |
| 总语句数 | 3,357 |
| 覆盖语句数 | 2,903 |
| 覆盖百分比 | 85% (86.48% 精确值) |
| 分支数 | 372 |
| 部分分支数 | 67 |
