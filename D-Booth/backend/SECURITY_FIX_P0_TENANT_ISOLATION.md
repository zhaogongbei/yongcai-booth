# P0 安全修复：租户隔离与越权漏洞

## 修复概述

修复了 D-Booth 后端的四个关键安全问题，防止跨租户数据泄露和未授权操作。

## 修复的问题

### 1. 活动创建越权 ✅

**问题**：`POST /api/v1/events` 允许用户为非所属团队创建活动

**修复**：
- 文件：`backend/app/api/v1/events.py`
- 改动：在 `create_event` 中添加 `PermissionError` 异常捕获，将服务层的权限错误转换为 HTTP 403
- 服务层 (`event_service.py`) 已有团队成员验证，API 层确保正确处理异常

**验证**：测试 `test_cannot_create_event_for_non_member_team` 通过

### 2. 打印任务列表全表泄露 ✅

**问题**：`GET /api/v1/print-jobs?status=pending` 绕过团队隔离，返回所有团队的打印任务

**修复**：
- 文件：
  - `backend/app/api/v1/print_jobs.py` - 传递 `status` 参数到服务层
  - `backend/app/services/print_service.py` - 接受 `status` 参数
  - `backend/app/repositories/print_job_repository.py` - 在 `get_visible_to_user` 中添加 `status` 过滤

**改进**：单次 SQL 查询，带状态过滤的团队成员 JOIN，无 N+1 问题

**验证**：测试 `test_print_jobs_status_filter_respects_team_isolation` 通过

### 3. 分享列表全表泄露 ✅

**问题**：`GET /api/v1/shares?channel=wechat` 绕过团队隔离，返回所有团队的分享记录

**修复**：
- 文件：
  - `backend/app/api/v1/shares.py` - 传递 `channel` 参数到服务层
  - `backend/app/services/share_service.py` - 接受 `channel` 参数
  - `backend/app/repositories/share_repository.py` - 在 `get_visible_to_user` 中添加 `channel` 过滤

**改进**：单次 SQL 查询，带渠道过滤的团队成员 JOIN，无 N+1 问题

**验证**：测试 `test_shares_channel_filter_respects_team_isolation` 通过

### 4. 订阅接口权限弱 ✅

**问题**：
- `POST /api/v1/subscriptions` 允许直接创建订阅，绕过 Stripe
- `PUT /api/v1/subscriptions/{id}` 和 `POST /api/v1/subscriptions/{id}/cancel` 仅验证成员身份，不验证 owner 权限

**修复**：
- 文件：`backend/app/api/v1/subscriptions.py`
- 改动：
  1. `create_subscription` 禁止直接创建，返回 403 并提示使用 `/checkout`
  2. `update_subscription` 要求团队 owner 权限（而非仅成员身份）
  3. `cancel_subscription` 要求团队 owner 权限（而非仅成员身份）

**验证**：
- `test_cannot_directly_create_subscription` 通过
- `test_non_owner_cannot_update_subscription` 通过
- `test_non_owner_cannot_cancel_subscription` 通过

## 测试覆盖

新增测试文件：`backend/tests/test_tenant_isolation.py`

包含 9 个测试场景：

1. ✅ `test_cannot_create_event_for_non_member_team` - 非成员不能创建活动
2. ✅ `test_print_jobs_status_filter_respects_team_isolation` - 状态筛选保持隔离
3. ✅ `test_shares_channel_filter_respects_team_isolation` - 渠道筛选保持隔离
4. ✅ `test_cannot_directly_create_subscription` - 禁止直接创建订阅
5. ✅ `test_non_owner_cannot_update_subscription` - 非 owner 不能更新订阅
6. ✅ `test_non_owner_cannot_cancel_subscription` - 非 owner 不能取消订阅
7. ✅ `test_user_can_create_event_for_own_team` - 成员可以为所属团队创建活动
8. ✅ `test_print_jobs_list_without_filters` - 无过滤器时列表正常工作
9. ✅ `test_shares_list_without_filters` - 无过滤器时列表正常工作

额外修复：`backend/tests/test_subscription_quotas.py` 中的 `_create_team` 辅助函数，添加团队成员关系创建。

## 测试结果

```bash
# 新增测试
tests/test_tenant_isolation.py::test_cannot_create_event_for_non_member_team PASSED
tests/test_tenant_isolation.py::test_print_jobs_status_filter_respects_team_isolation PASSED
tests/test_tenant_isolation.py::test_shares_channel_filter_respects_team_isolation PASSED
tests/test_tenant_isolation.py::test_cannot_directly_create_subscription PASSED
tests/test_tenant_isolation.py::test_non_owner_cannot_update_subscription PASSED
tests/test_tenant_isolation.py::test_non_owner_cannot_cancel_subscription PASSED
tests/test_tenant_isolation.py::test_user_can_create_event_for_own_team PASSED
tests/test_tenant_isolation.py::test_print_jobs_list_without_filters PASSED
tests/test_tenant_isolation.py::test_shares_list_without_filters PASSED

# 回归测试
tests/test_subscription_quotas.py - 全部通过
tests/test_auth.py - 全部通过
tests/test_teams.py - 全部通过
tests/test_ai_service.py - 全部通过
tests/test_main.py - 全部通过

总计：30 个测试全部通过
```

## 架构改进

### 查询优化

**修复前**：
```python
# 全表扫描，无团队隔离
SELECT * FROM print_jobs WHERE status = 'pending';
```

**修复后**：
```python
# 单次 JOIN，自动团队隔离
SELECT print_jobs.*
FROM print_jobs
JOIN photos ON print_jobs.photo_id = photos.id
JOIN events ON photos.event_id = events.id
JOIN team_members ON team_members.team_id = events.team_id
WHERE team_members.user_id = ?
  AND print_jobs.status = ?
ORDER BY print_jobs.created_at DESC
LIMIT ? OFFSET ?;
```

### 防御深度

- **API 层**：参数验证，HTTP 异常转换
- **服务层**：业务逻辑验证，权限检查
- **仓库层**：SQL 级别的团队隔离 JOIN

## 安全影响

### 修复前风险

- **IDOR（越权访问）**：用户可读取/操作其他团队数据
- **数据泄露**：状态/渠道筛选可全表遍历
- **订阅篡改**：任意用户可创建或修改订阅记录

### 修复后状态

- ✅ 所有业务数据查询自动按团队成员过滤
- ✅ 活动创建强制验证团队成员身份
- ✅ 订阅操作限制为团队 owner
- ✅ 单 SQL 查询，性能优化

## 运行测试

```bash
cd backend
python -m pytest tests/test_tenant_isolation.py -v
```

## 相关文件

### 修改的文件

1. `backend/app/api/v1/events.py` - 添加 PermissionError 处理
2. `backend/app/api/v1/print_jobs.py` - 传递 status 参数
3. `backend/app/api/v1/shares.py` - 传递 channel 参数
4. `backend/app/api/v1/subscriptions.py` - 禁用直接创建，owner 权限验证
5. `backend/app/services/print_service.py` - 接受 status 参数
6. `backend/app/services/share_service.py` - 接受 channel 参数
7. `backend/app/repositories/print_job_repository.py` - status 过滤
8. `backend/app/repositories/share_repository.py` - channel 过滤

### 新增的文件

1. `backend/tests/test_tenant_isolation.py` - 完整的安全测试套件

### 兼容性

- ✅ 无 API 响应模型变更
- ✅ 所有现有测试通过
- ✅ 向后兼容客户端调用

## 结论

所有 P0 租户隔离问题已修复，测试覆盖完整，无破坏性变更。
