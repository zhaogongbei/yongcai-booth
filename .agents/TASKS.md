# D-Booth Agent 任务配置

本文档定义各个优化 Agent 的具体任务、工具和执行策略。

---

## Agent 1: Backend Optimizer

**文件**: `.agents/backend-optimizer.md`

### 配置

```yaml
name: backend-optimizer
description: Backend API 优化专家
model: opus
tools: [Read, Edit, Grep, Glob, Bash]
isolation: none
```

### 任务 1: 代码规范化

**Prompt**:
```
你是 D-Booth Backend 优化专家。请执行以下任务：

1. 扫描 D-Booth/backend/app 目录下的所有 Python 文件
2. 运行代码格式化工具：
   - black . --check（检查需要格式化的文件）
   - isort . --check（检查导入顺序）
   - ruff check app/（检查 Linter 问题）
3. 如果发现问题，运行修复命令：
   - black .
   - isort .
   - ruff check app/ --fix
4. 运行类型检查：mypy app/
5. 修复发现的类型错误
6. 验证所有检查通过
7. 生成优化报告

工作目录：D-Booth/backend
工具：Bash, Read, Edit, Grep
输出：优化报告（Markdown 格式）
```

### 任务 2: API 端点审查

**Prompt**:
```
审查并优化 D-Booth/backend/app/api/v1/ 目录下的所有 API 端点。

对于每个文件：
1. 检查是否有统一的错误处理
2. 检查是否有 Pydantic 请求验证模型
3. 检查是否有 response_model 定义
4. 检查是否有 OpenAPI 文档注释
5. 检查数据库查询是否优化（避免 N+1）
6. 优化代码结构和命名

优化标准：
- 所有端点必须有类型注解
- 所有端点必须有文档字符串
- 错误处理统一使用 HTTPException
- 数据库查询使用 Service 层
- 添加日志记录关键操作

工具：Read, Edit, Grep, Glob
输出：修改文件列表 + 优化说明
```

### 任务 3: Service 层重构

**Prompt**:
```
重构 D-Booth/backend/app/services/ 目录。

目标：
1. 提取所有业务逻辑到 Service 层
2. 统一事务管理模式
3. 添加缓存策略
4. 实施错误处理
5. 添加完整类型注解

模式参考：
- Service 类使用依赖注入
- 所有方法都是 async
- 使用 AsyncSession 管理事务
- 关键操作添加日志
- 复杂逻辑添加注释

工具：Read, Edit, Grep, Glob
输出：重构后的 Service 层代码
```

---

## Agent 2: Frontend Optimizer

**文件**: `.agents/frontend-optimizer.md`

### 配置

```yaml
name: frontend-optimizer
description: Frontend 应用优化专家
model: opus
tools: [Read, Edit, Grep, Glob, Bash]
isolation: none
```

### 任务 1: 代码规范化

**Prompt**:
```
你是 D-Booth Frontend 优化专家。执行以下任务：

1. 扫描 D-Booth/frontend/src 目录
2. 运行 Lint 检查：pnpm lint
3. 运行类型检查：pnpm typecheck
4. 修复所有 Lint 错误：pnpm lint --fix
5. 手动修复类型错误
6. 验证所有检查通过
7. 生成优化报告

工作目录：D-Booth/frontend
工具：Bash, Read, Edit, Grep
标准：
- 所有组件必须有 TypeScript 类型
- 避免使用 any 类型
- Props 接口必须明确定义
- Hooks 依赖数组正确
```

### 任务 2: 组件优化

**Prompt**:
```
优化 D-Booth/frontend/src/app/components/ 和 screens/ 目录下的组件。

优化项：
1. 提取重复逻辑到自定义 Hooks
2. 使用 React.memo 优化不必要的重渲染
3. 统一 Loading 和 Error 状态处理
4. 优化大列表渲染（虚拟滚动）
5. 添加 ErrorBoundary
6. 优化表单处理

检查清单：
- [ ] 组件职责单一
- [ ] Props 类型明确
- [ ] 状态管理合理
- [ ] 副作用正确处理
- [ ] 性能优化到位

工具：Read, Edit, Grep, Glob
输出：优化后的组件代码
```

### 任务 3: 性能优化

**Prompt**:
```
实施 Frontend 性能优化。

优化策略：
1. 代码分割（React.lazy + Suspense）
2. 图片懒加载
3. 虚拟滚动（大列表）
4. Bundle 分析和优化
5. 添加 Service Worker

目标：
- 首屏加载 < 2s
- 交互响应 < 100ms
- Bundle 大小 < 500KB (gzip)

工具：Read, Edit, Bash
输出：性能优化报告
```

---

## Agent 3: Runtime Optimizer

**文件**: `.agents/runtime-optimizer.md`

### 配置

```yaml
name: runtime-optimizer
description: .NET Runtime 优化专家
model: opus
tools: [Read, Edit, Grep, Glob, Bash]
isolation: none
```

### 任务 1: 代码规范化

**Prompt**:
```
你是 D-Booth Runtime 优化专家。执行以下任务：

1. 扫描 D-Booth/runtime-dotnet/src 目录
2. 运行格式化：dotnet format
3. 运行构建检查：dotnet build
4. 检查命名约定
5. 添加 XML 文档注释
6. 验证编译无警告
7. 生成优化报告

工作目录：D-Booth/runtime-dotnet
工具：Bash, Read, Edit, Grep
标准：
- 遵循 C# 命名约定
- 公共 API 必须有 XML 注释
- 异步方法以 Async 结尾
- 使用 nullable 引用类型
```

### 任务 2: 领域模型优化

**Prompt**:
```
优化 D-Booth/runtime-dotnet/src/Booth.Domain.Session/ 领域模型。

优化项：
1. 完善聚合根设计
2. 添加领域事件
3. 优化值对象
4. 添加业务规则验证
5. 实施不变性原则

DDD 原则：
- 聚合根控制边界
- 值对象不可变
- 领域事件记录变化
- 业务规则在领域层

工具：Read, Edit, Grep
输出：优化后的领域模型
```

---

## Agent 4: Database Optimizer

**文件**: `.agents/database-optimizer.md`

### 配置

```yaml
name: database-optimizer
description: 数据库优化专家
model: opus
tools: [Read, Edit, Bash]
isolation: none
```

### 任务 1: 索引优化

**Prompt**:
```
优化 D-Booth Backend 数据库索引。

步骤：
1. 审查 alembic/versions/ 中的所有迁移文件
2. 识别需要索引的列：
   - 外键列
   - 频繁查询的列
   - WHERE 子句中的列
   - ORDER BY 的列
3. 生成索引添加脚本
4. 创建新的迁移文件

索引原则：
- 高选择性列优先
- 避免过度索引
- 考虑复合索引
- 监控索引使用情况

工具：Read, Edit, Bash
输出：索引优化迁移脚本
```

---

## Agent 5: Test Coverage Agent

**文件**: `.agents/test-coverage.md`

### 配置

```yaml
name: test-coverage-agent
description: 测试覆盖率提升专家
model: opus
tools: [Read, Edit, Bash, Grep, Glob]
isolation: none
```

### 任务 1: Backend 测试

**Prompt**:
```
提升 D-Booth Backend 测试覆盖率至 80%。

步骤：
1. 运行覆盖率检查：pytest --cov=app --cov-report=html
2. 识别未覆盖的关键代码
3. 为每个未覆盖的模块编写测试
4. 优先覆盖：
   - 业务逻辑（Service 层）
   - API 端点
   - Repository 层
5. 运行测试验证
6. 生成覆盖率报告

测试原则：
- 测试行为而非实现
- 使用 Fixtures 复用代码
- Mock 外部依赖
- 测试边界情况

工具：Read, Edit, Bash
目标：≥ 80% 覆盖率
```

### 任务 2: Frontend 测试

**Prompt**:
```
提升 D-Booth Frontend 测试覆盖率至 70%。

步骤：
1. 运行覆盖率检查：pnpm test --coverage
2. 为关键组件添加测试
3. 为 Hooks 添加测试
4. 为工具函数添加测试
5. 运行测试验证

测试策略：
- 使用 React Testing Library
- 测试用户交互
- Mock API 调用
- 快照测试（谨慎使用）

工具：Read, Edit, Bash
目标：≥ 70% 覆盖率
```

---

## Agent 6: Documentation Agent

**文件**: `.agents/documentation.md`

### 配置

```yaml
name: documentation-agent
description: 文档完善专家
model: opus
tools: [Read, Edit, Grep, Glob]
isolation: none
```

### 任务 1: API 文档审查

**Prompt**:
```
审查并完善 D-Booth Backend API 文档。

步骤：
1. 审查所有 API 端点的文档注释
2. 确保每个端点有：
   - summary（简短描述）
   - description（详细说明）
   - 参数说明
   - 响应示例
   - 错误码说明
3. 更新 OpenAPI 规范
4. 生成文档预览

文档标准：
- 清晰简洁
- 包含示例
- 说明边界情况
- 标注弃用 API

工具：Read, Edit
输出：完善的 API 文档
```

### 任务 2: README 更新

**Prompt**:
```
更新项目 README 文档。

更新内容：
1. 项目简介
2. 快速开始指南
3. 安装说明
4. 配置说明
5. 开发指南
6. 部署指南
7. 常见问题
8. 贡献指南

确保：
- 命令可执行
- 链接有效
- 截图最新
- 版本号正确

工具：Read, Edit
输出：更新后的 README
```

---

## 执行顺序

### 第 1 天
1. Backend Optimizer - Task 1 (代码规范化)
2. Frontend Optimizer - Task 1 (代码规范化)
3. Runtime Optimizer - Task 1 (代码规范化)

### 第 2 天
4. Backend Optimizer - Task 2 (API 端点审查)
5. Backend Optimizer - Task 3 (Service 层重构)

### 第 3 天
6. Frontend Optimizer - Task 2 (组件优化)
7. Frontend Optimizer - Task 3 (性能优化)

### 第 4 天
8. Runtime Optimizer - Task 2 (领域模型优化)
9. Database Optimizer - Task 1 (索引优化)

### 第 5 天
10. Test Coverage Agent - Task 1 (Backend 测试)
11. Test Coverage Agent - Task 2 (Frontend 测试)

### 第 6-7 天
12. Documentation Agent - Task 1 (API 文档)
13. Documentation Agent - Task 2 (README 更新)
14. 最终验证和发布

---

## 使用方法

### 启动单个 Agent

```bash
# 启动 Backend 优化
claude-agent run backend-optimizer --task "代码规范化"

# 启动 Frontend 优化
claude-agent run frontend-optimizer --task "代码规范化"
```

### 批量启动

```bash
# 启动所有优化 Agent
./scripts/run-all-optimizers.sh
```

### 监控进度

```bash
# 查看任务状态
claude-agent status

# 查看日志
tail -f .agents/logs/backend-optimizer.log
```

---

**创建日期**: 2026-07-02  
**维护**: AI Team  
**反馈**: 更新任务配置请编辑本文件
