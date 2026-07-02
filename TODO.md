# D-Booth 优化执行清单

> **面向**: 执行优化的 AI Agent  
> **更新**: 2026-07-02  
> **状态**: 待执行

---

## 📋 总体进度

- ✅ **阶段 0**: 项目扫描与分析 (100%)
- ✅ **阶段 1**: 根目录文档体系 (100%)
- ⏳ **阶段 2**: Backend 优化 (0%)
- ⏳ **阶段 3**: Frontend 优化 (0%)
- ⏳ **阶段 4**: Runtime 优化 (0%)
- ⏳ **阶段 5**: 数据库优化 (0%)
- ⏳ **阶段 6**: DevOps 优化 (0%)
- ⏳ **阶段 7**: 测试与验证 (0%)

---

## 🎯 阶段 2: Backend 优化

**负责 Agent**: `backend-optimizer-agent`  
**预计时间**: 2-3 天  
**优先级**: P0

### Task 2.1: 代码规范化

```bash
cd D-Booth/backend

# 格式化代码
black .
isort .

# 类型检查
mypy app/

# Linter 检查
ruff check app/ --fix

# 提交变更
git add -A
git commit -m "refactor(backend): code standardization and formatting"
```

**检查点**:
- [ ] Black 格式化无变更
- [ ] isort 无错误
- [ ] mypy 类型检查通过
- [ ] ruff 无警告

---

### Task 2.2: API 端点审查

**文件列表**:
```
app/api/v1/auth.py
app/api/v1/teams.py
app/api/v1/events.py
app/api/v1/photos.py
app/api/v1/templates.py
app/api/v1/print_jobs.py
app/api/v1/shares.py
app/api/v1/ai_tasks.py
```

**优化清单**:
- [ ] 统一错误处理 (`HTTPException`)
- [ ] 添加请求验证 (`Pydantic` models)
- [ ] 添加响应模型 (`response_model`)
- [ ] 优化数据库查询 (避免 N+1)
- [ ] 添加缓存策略 (`@cache` decorator)
- [ ] 添加日志记录
- [ ] 添加 OpenAPI 文档注释

**示例优化**:
```python
# Before
@router.get("/events")
async def get_events(db: AsyncSession = Depends(get_db)):
    events = await db.execute(select(Event))
    return events.scalars().all()

# After
@router.get("/events", 
            response_model=List[EventResponse],
            summary="获取事件列表",
            description="返回当前用户可访问的所有事件")
async def get_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[EventResponse]:
    """获取事件列表（分页）"""
    events = await event_service.get_events(
        db, current_user, skip=skip, limit=limit
    )
    return events
```

---

### Task 2.3: Service 层重构

**文件列表**:
```
app/services/event_service.py
app/services/photo_service.py
app/services/auth_service.py
```

**优化清单**:
- [ ] 提取业务逻辑到 Service 层
- [ ] 统一事务管理
- [ ] 添加缓存逻辑
- [ ] 添加错误处理
- [ ] 添加类型注解

---

### Task 2.4: Repository 层优化

**文件列表**:
```
app/repositories/event_repository.py
app/repositories/photo_repository.py
app/repositories/user_repository.py
```

**优化清单**:
- [ ] 统一 CRUD 基类
- [ ] 优化查询方法 (避免 N+1)
- [ ] 添加批量操作
- [ ] 添加软删除支持
- [ ] 添加分页工具

**示例**:
```python
class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model
    
    async def get_by_id(self, db: AsyncSession, id: UUID) -> Optional[T]:
        result = await db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_multi(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[T]:
        result = await db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()
```

---

### Task 2.5: 数据库迁移优化

```bash
cd D-Booth/backend

# 审查迁移文件
ls alembic/versions/

# 检查迁移历史
alembic history

# 验证迁移
alembic upgrade head --sql > migration.sql
# 审查 migration.sql
```

**检查点**:
- [ ] 所有迁移文件有清晰注释
- [ ] 索引已正确添加
- [ ] 外键约束正确
- [ ] 可回滚 (downgrade)

---

### Task 2.6: 测试覆盖

```bash
# 运行测试
pytest --cov=app --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

**目标**:
- [ ] 核心业务逻辑 ≥ 80%
- [ ] API 端点 ≥ 70%
- [ ] Repository ≥ 90%

**待补充测试**:
```
tests/test_auth.py
tests/test_events.py
tests/test_photos.py
tests/test_repositories.py
```

---

## 🎨 阶段 3: Frontend 优化

**负责 Agent**: `frontend-optimizer-agent`  
**预计时间**: 2-3 天  
**优先级**: P0

### Task 3.1: 代码规范化

```bash
cd D-Booth/frontend

# Lint 修复
pnpm lint --fix

# 类型检查
pnpm typecheck

# 格式化
pnpm format

# 提交变更
git add -A
git commit -m "refactor(frontend): code standardization"
```

---

### Task 3.2: 组件优化

**审查文件**:
```
src/app/screens/*.tsx
src/app/components/*.tsx
```

**优化清单**:
- [ ] 提取可复用逻辑到 Hooks
- [ ] 优化渲染性能 (React.memo)
- [ ] 添加 ErrorBoundary
- [ ] 统一 Loading 状态
- [ ] 优化表单处理

---

### Task 3.3: API 客户端优化

**文件**: `src/app/lib/api.ts`

**优化清单**:
- [ ] 统一错误处理
- [ ] 添加请求拦截器
- [ ] 添加响应拦截器
- [ ] 实施请求取消
- [ ] 添加重试机制
- [ ] 添加类型定义

---

### Task 3.4: 性能优化

**清单**:
- [ ] 实施代码分割 (React.lazy)
- [ ] 优化图片加载 (lazy loading)
- [ ] 实施虚拟滚动
- [ ] 添加 Service Worker
- [ ] 优化 Bundle 大小

```typescript
// 代码分割示例
const EventsScreen = React.lazy(() => import('./screens/EventsScreen'));
const PhotosScreen = React.lazy(() => import('./screens/PhotosScreen'));

<Suspense fallback={<Spinner />}>
  <Routes>
    <Route path="/events" element={<EventsScreen />} />
    <Route path="/photos" element={<PhotosScreen />} />
  </Routes>
</Suspense>
```

---

### Task 3.5: 测试覆盖

```bash
pnpm test --coverage
```

**目标**: ≥ 70%

**待补充测试**:
```
src/app/screens/__tests__/
src/app/components/__tests__/
src/app/hooks/__tests__/
```

---

## 🖥️ 阶段 4: Runtime 优化

**负责 Agent**: `runtime-optimizer-agent`  
**预计时间**: 1-2 天  
**优先级**: P0

### Task 4.1: 代码规范化

```bash
cd D-Booth/runtime-dotnet

# 格式化
dotnet format

# 构建检查
dotnet build

# 提交变更
git add -A
git commit -m "refactor(runtime): code standardization"
```

---

### Task 4.2: 领域模型优化

**文件**: `src/Booth.Domain.Session/`

**优化清单**:
- [ ] 完善聚合根
- [ ] 添加领域事件
- [ ] 优化值对象
- [ ] 添加业务规则验证

---

### Task 4.3: 测试覆盖

```bash
dotnet test --collect:"XPlat Code Coverage"
```

**目标**: ≥ 80%

---

## 💾 阶段 5: 数据库优化

**负责 Agent**: `database-optimizer-agent`  
**预计时间**: 1 天  
**优先级**: P1

### Task 5.1: 索引优化

**审查表**:
```sql
-- 检查缺失索引
SELECT * FROM pg_stat_user_tables;

-- 检查未使用索引
SELECT * FROM pg_stat_user_indexes WHERE idx_scan = 0;
```

**添加索引**:
```sql
CREATE INDEX idx_events_team_id ON events(team_id);
CREATE INDEX idx_photos_event_id ON photos(event_id);
CREATE INDEX idx_users_email ON users(email);
```

---

### Task 5.2: 查询优化

**工具**: `EXPLAIN ANALYZE`

```sql
EXPLAIN ANALYZE
SELECT * FROM events WHERE team_id = '...';
```

---

## 🚀 阶段 6: DevOps 优化

**负责 Agent**: `devops-optimizer-agent`  
**预计时间**: 1-2 天  
**优先级**: P1

### Task 6.1: Docker 优化

**文件**: `D-Booth/backend/Dockerfile`

**优化清单**:
- [ ] 多阶段构建
- [ ] 缩小镜像体积
- [ ] 安全扫描
- [ ] 添加健康检查

---

### Task 6.2: CI/CD 优化

**文件**: `.github/workflows/ci.yml`

**优化清单**:
- [ ] 并行化测试
- [ ] 缓存优化
- [ ] 部署自动化

---

## ✅ 阶段 7: 测试与验证

**负责 Agent**: `qa-agent`  
**预计时间**: 2 天  
**优先级**: P0

### Task 7.1: 集成测试

```bash
# Backend
pytest tests/integration/

# Frontend
pnpm test:e2e

# Runtime
dotnet test --filter Category=Integration
```

---

### Task 7.2: 性能测试

```bash
# 使用 Locust
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

---

### Task 7.3: 安全测试

```bash
# 依赖扫描
pip install safety
safety check

pnpm audit

# 容器扫描
trivy image dbooth/backend:latest
```

---

## 📊 验收标准

### 代码质量

- [ ] 所有 Linter 无错误
- [ ] 所有类型检查通过
- [ ] 测试覆盖率达标
- [ ] 代码审查通过

### 性能

- [ ] API 响应时间 < 500ms (P95)
- [ ] 首屏加载 < 2s
- [ ] 并发支持 ≥ 1000 用户

### 安全

- [ ] 无高危漏洞
- [ ] 无中危漏洞
- [ ] 依赖全部最新

### 文档

- [ ] API 文档完整
- [ ] README 更新
- [ ] CHANGELOG 更新

---

## 🔄 执行流程

1. **选择任务** - 从清单中选择一个未完成的任务
2. **理解需求** - 阅读任务描述和检查点
3. **执行优化** - 按照清单逐项完成
4. **运行测试** - 验证优化结果
5. **提交代码** - 使用规范的提交消息
6. **更新状态** - 标记任务为完成 ✅
7. **继续下一个** - 重复流程

---

## 📝 注意事项

1. **批量操作** - 尽可能批量完成相关任务
2. **保持一致** - 遵循项目现有风格和模式
3. **充分测试** - 每次修改后运行相关测试
4. **清晰提交** - 使用 Conventional Commits 规范
5. **文档同步** - 修改代码同时更新文档

---

**创建日期**: 2026-07-02  
**维护**: 持续更新  
**反馈**: 发现问题请及时更新本清单
