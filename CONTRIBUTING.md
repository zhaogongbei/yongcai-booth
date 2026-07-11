# Contributing to D-Booth

> **注意**: 本项目为商业闭源软件，仅限内部开发团队访问。

感谢您对咏彩Booth项目的贡献！本文档提供内部开发规范与协作流程。

## 目录

- [开发环境设置](#开发环境设置)
- [开发工作流](#开发工作流)
- [代码规范](#代码规范)
- [提交规范](#提交规范)
- [测试要求](#测试要求)
- [文档要求](#文档要求)
- [代码审查](#代码审查)

---

## 开发环境设置

### 必需工具

- Git 2.40+
- Python 3.11+
- Node.js 20+ (使用 npm 与 package-lock.json)
- .NET 8.0 SDK
- Docker Desktop
- VS Code / JetBrains IDE

### IDE 配置

#### VS Code 推荐扩展

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-vscode.vscode-typescript-next",
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "ms-dotnettools.csharp",
    "ms-azuretools.vscode-docker"
  ]
}
```

### 本地开发设置

完整的本地环境搭建步骤（Backend / Frontend / Runtime / 基础设施）以 [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md#初次设置) 为唯一权威来源，本文不再重复，避免多处漂移。

---

## 开发工作流

### 分支策略

```
main (受保护)
  ├── develop (开发主分支)
  │     ├── feature/camera-sdk-integration
  │     ├── feature/ai-beauty-filter
  │     └── fix/print-queue-blocking
  └── hotfix/security-patch
```

#### 分支命名规范

- `feature/*` - 新功能开发
- `fix/*` - Bug 修复
- `refactor/*` - 代码重构
- `perf/*` - 性能优化
- `docs/*` - 文档更新
- `test/*` - 测试相关
- `hotfix/*` - 紧急修复

### 开发流程

1. **创建分支**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **开发与提交**
   - 遵循代码规范
   - 编写单元测试
   - 保持提交原子化
   - 使用规范的提交消息

3. **推送与 PR**
   ```bash
   git push -u origin feature/your-feature-name
   # 在 GitHub/GitLab 创建 Pull Request
   ```

4. **代码审查**
   - 至少 1 位 Reviewer 批准
   - CI 检查全部通过
   - 无未解决的评论

5. **合并**
   - 使用 Squash and Merge (功能分支)
   - 使用 Merge Commit (release 分支)

---

## 代码规范

### Python (Backend)

#### 风格指南

遵循 [PEP 8](https://pep8.org/) 和项目配置：

```python
# 好的示例
async def get_event_by_id(
    event_id: UUID,
    db: AsyncSession,
    current_user: User,
) -> Event:
    """获取事件详情。
    
    Args:
        event_id: 事件唯一标识
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        Event 对象
        
    Raises:
        HTTPException: 事件不存在或无权限
    """
    event = await event_repo.get_by_id(db, event_id)
    if not event:
        raise HTTPException(404, "Event not found")
    
    # 检查权限
    if event.team_id != current_user.team_id:
        raise HTTPException(403, "Permission denied")
    
    return event
```

#### 强制要求

- 使用 Black 格式化 (行长度 100)
- 使用 isort 排序导入
- 使用 Ruff 静态分析（CI 门禁：`ruff check app/ --select E9,F63,F7,F82`）
- 所有公共函数必须有 docstring
- 所有参数必须有类型注解
- 类型检查（mypy）按模块逐步收敛，当前不是 CI 门禁

```bash
# 运行检查（与 CI 一致）
black --check .
isort --check-only .
ruff check app/ --select E9,F63,F7,F82
```

### TypeScript (Frontend)

#### 风格指南

```typescript
// 好的示例
interface EventDetailsProps {
  eventId: string;
  onUpdate?: (event: Event) => void;
}

export const EventDetails: React.FC<EventDetailsProps> = ({ 
  eventId, 
  onUpdate 
}) => {
  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchEvent = async () => {
      try {
        const data = await api.getEvent(eventId);
        setEvent(data);
      } catch (error) {
        console.error('Failed to fetch event:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchEvent();
  }, [eventId]);

  // ...
};
```

#### 强制要求

- 使用 TypeScript 编译检查和项目约定格式
- 启用 TypeScript strict mode
- 所有组件必须有类型定义
- 优先使用函数组件与 Hooks
- 避免 `any` 类型（使用 `unknown`）

```bash
# 运行检查
npm run typecheck
npm run build
```

### C# (Runtime)

#### 风格指南

遵循 [.NET 编码约定](https://learn.microsoft.com/dotnet/csharp/fundamentals/coding-style/coding-conventions)：

```csharp
// 好的示例
public class SessionAggregate
{
    private readonly List<Shot> _shots = new();

    public Guid Id { get; private set; }
    public SessionStatus Status { get; private set; }
    public IReadOnlyList<Shot> Shots => _shots.AsReadOnly();

    public void CaptureShot(string filePath, CaptureMetadata metadata)
    {
        if (Status != SessionStatus.Active)
        {
            throw new InvalidOperationException(
                "Cannot capture shot: session is not active"
            );
        }

        var shot = new Shot
        {
            Id = Guid.NewGuid(),
            SessionId = Id,
            FilePath = filePath,
            Metadata = metadata,
            CapturedAt = DateTime.UtcNow
        };

        _shots.Add(shot);
    }
}
```

#### 强制要求

- 使用 .editorconfig
- 使用 C# 12 语法
- 优先使用 `record` 和 `init` 属性
- 异步方法必须以 `Async` 结尾
- 所有公共 API 必须有 XML 文档注释

---

## 提交规范

### Conventional Commits

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### 类型 (type)

- `feat`: 新功能
- `fix`: Bug 修复
- `refactor`: 重构（既不是新功能也不是修复）
- `perf`: 性能优化
- `style`: 代码格式（不影响代码运行）
- `test`: 测试相关
- `docs`: 文档更新
- `chore`: 构建过程或辅助工具变动
- `ci`: CI 配置文件和脚本的变动
- `revert`: 回滚提交

#### 范围 (scope)

- `backend` / `frontend` / `runtime`
- `auth` / `events` / `photos` / `templates`
- `camera` / `printer` / `ai`
- `db` / `api` / `ui`

#### 示例

```bash
# 新功能
feat(backend): add GoPro WiFi camera integration

# Bug 修复
fix(frontend): resolve photo grid infinite scroll issue

# 重构
refactor(runtime): extract camera SDK abstraction layer

# 性能优化
perf(backend): optimize photo thumbnail generation with WebP

# 文档
docs: update deployment guide with Docker Compose examples

# 破坏性变更
feat(api)!: migrate authentication to OAuth2

BREAKING CHANGE: JWT token format has changed, clients must re-authenticate
```

### 提交最佳实践

- ✅ 原子提交（一个提交解决一个问题）
- ✅ 清晰的提交信息
- ✅ 提交前本地测试通过
- ❌ 不要提交注释代码
- ❌ 不要提交调试日志
- ❌ 不要提交敏感信息（密钥、密码）

---

## 测试要求

### 测试覆盖率要求

- 核心业务逻辑: **≥ 80%**
- API 端点: **≥ 70%**
- 工具函数: **≥ 90%**

### Backend 测试

```python
# tests/test_events.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_event_success(client: AsyncClient, auth_headers):
    """测试创建事件成功"""
    payload = {
        "name": "Test Event",
        "event_type": "wedding",
        "start_time": "2026-08-01T10:00:00Z",
        "end_time": "2026-08-01T18:00:00Z",
    }
    
    response = await client.post(
        "/api/v1/events",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Event"
    assert "id" in data
```

### Frontend 测试

```typescript
// EventDetails.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { EventDetails } from './EventDetails';

describe('EventDetails', () => {
  it('renders event details correctly', async () => {
    const mockEvent = {
      id: '123',
      name: 'Test Event',
      status: 'active',
    };

    render(<EventDetails eventId="123" />);

    await waitFor(() => {
      expect(screen.getByText('Test Event')).toBeInTheDocument();
    });
  });
});
```

### Runtime 测试

```csharp
// SessionAggregateTests.cs
[Fact]
public void CaptureShot_WhenSessionActive_AddsShot()
{
    // Arrange
    var session = new SessionAggregate(Guid.NewGuid());
    session.Start();

    // Act
    session.CaptureShot("/path/to/photo.jpg", new CaptureMetadata());

    // Assert
    Assert.Single(session.Shots);
    Assert.Equal(SessionStatus.Active, session.Status);
}
```

---

## 文档要求

### 代码文档

- 所有公共 API 必须有文档注释
- 复杂逻辑必须有行内注释
- 配置文件必须有说明注释

### README 更新

新功能必须更新相应模块的 README：

- Backend: `D-Booth/backend/README.md`
- Frontend: `D-Booth/frontend/README.md`
- Runtime: `D-Booth/runtime-dotnet/README.md`

### API 文档

Backend API 使用 OpenAPI 自动生成文档，需确保：

- 所有端点有 `summary` 和 `description`
- 所有参数有类型和说明
- 所有响应有示例

```python
@router.post("/events", response_model=EventResponse, status_code=201)
async def create_event(
    event: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EventResponse:
    """创建新事件。
    
    需要团队管理员权限。
    
    Args:
        event: 事件创建数据
        db: 数据库会话
        current_user: 当前认证用户
        
    Returns:
        创建的事件详情
        
    Raises:
        HTTPException 403: 权限不足
        HTTPException 422: 验证错误
    """
    # ...
```

---

## 代码审查

### 审查清单

#### 功能性

- [ ] 代码实现符合需求
- [ ] 边界情况已处理
- [ ] 错误处理完善
- [ ] 日志记录充分

#### 代码质量

- [ ] 代码清晰易读
- [ ] 无重复代码
- [ ] 函数职责单一
- [ ] 命名语义化

#### 测试

- [ ] 单元测试覆盖核心逻辑
- [ ] 测试用例充分
- [ ] 所有测试通过

#### 安全

- [ ] 无 SQL 注入风险
- [ ] 无 XSS 风险
- [ ] 敏感数据已加密/脱敏
- [ ] 权限检查完整

#### 性能

- [ ] 无 N+1 查询
- [ ] 合理使用缓存
- [ ] 大数据量场景优化
- [ ] 异步操作适当

#### 文档

- [ ] 代码注释充分
- [ ] API 文档完整
- [ ] README 已更新

### 审查流程

1. **自查**: 开发者自行检查清单
2. **同行审查**: 至少 1 位团队成员审查
3. **架构审查**: 重大变更需架构师审查
4. **安全审查**: 涉及认证/授权/敏感数据需安全审查

### 审查意见分级

- **Must**: 必须修改（阻塞合并）
- **Should**: 应当修改（建议采纳）
- **Nice-to-have**: 可选优化

---

## 问题报告

### Bug 报告模板

```markdown
**描述**
简要描述 Bug

**复现步骤**
1. 访问 XXX 页面
2. 点击 XXX 按钮
3. 观察到 XXX 错误

**预期行为**
应该显示 XXX

**实际行为**
显示了 XXX 错误

**环境**
- OS: Windows 11
- Browser: Chrome 126
- Version: 1.0.0

**截图/日志**
[附上截图或日志]
```

---

## 发布流程

### 版本发布

1. 更新 `VERSION` 文件
2. 更新 `CHANGELOG.md`
3. 创建 Git Tag
4. 构建发布包
5. 部署到生产环境
6. 发布公告

### 版本号规则

```
MAJOR.MINOR.PATCH

例如: 1.2.3
- 1: 主版本号（破坏性变更）
- 2: 次版本号（新功能）
- 3: 修订号（Bug 修复）
```

---

## 联系方式

- 技术讨论: 企业微信开发群
- 紧急问题: 值班手机 XXX-XXXX-XXXX
- 代码审查: GitHub Pull Request
- 项目管理: JIRA / 内部看板

---

**Happy Coding! 🚀**
