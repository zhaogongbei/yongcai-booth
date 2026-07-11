# Developer Guide

D-Booth 项目开发者完全指南。

## 快速开始

### 环境准备

**必需工具**:
```bash
# Python 3.11+
python --version

# Node.js 20+
node --version

# .NET 8.0 SDK
dotnet --version

# Docker Desktop
docker --version

# npm
npm --version

# Git
git --version
```

### 初次设置

```bash
# 1. 克隆仓库
git clone <repo-url>
cd D-Booth

# 2. 设置 Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
# 编辑 .env，设置 SECRET_KEY
alembic upgrade head

# 3. 设置 Frontend
cd ../frontend
npm ci

# 4. 设置 Runtime
cd ../runtime-dotnet
dotnet restore

# 5. 启动基础服务（Docker）
cd ../backend
docker-compose up -d postgres redis

# 6. 启动所有服务
# 终端 1: Backend
cd backend && source venv/bin/activate
uvicorn app.main:app --reload

# 终端 2: Frontend
cd frontend && npm run dev

# 终端 3: Runtime (Windows)
cd runtime-dotnet && dotnet run --project src/Booth.Runtime.ApiHost
```

---

## 项目结构详解

### Backend (Python/FastAPI)

```
backend/
├── alembic/              # 数据库迁移
│   ├── versions/         # 迁移文件
│   └── env.py           # Alembic 配置
│
├── app/
│   ├── api/             # API 路由层
│   │   ├── deps.py      # 依赖注入
│   │   └── v1/          # API v1 端点
│   │       ├── auth.py
│   │       ├── events.py
│   │       └── ...
│   │
│   ├── core/            # 核心配置
│   │   ├── config.py    # 环境配置
│   │   ├── database.py  # 数据库连接
│   │   ├── security.py  # 认证/授权
│   │   ├── logging.py   # 日志配置
│   │   ├── exceptions.py # 异常定义
│   │   └── middleware.py # 中间件
│   │
│   ├── models/          # SQLAlchemy 模型
│   │   ├── base.py      # Base 模型
│   │   ├── user.py
│   │   ├── event.py
│   │   └── ...
│   │
│   ├── schemas/         # Pydantic 模式
│   │   ├── user.py      # DTO
│   │   ├── event.py
│   │   └── ...
│   │
│   ├── repositories/    # 数据访问层
│   │   ├── base.py      # BaseRepository
│   │   ├── user.py
│   │   └── ...
│   │
│   ├── services/        # 业务逻辑层
│   │   ├── user_service.py
│   │   ├── event_service.py
│   │   └── ...
│   │
│   ├── tasks/           # Celery 任务
│   │   ├── photo_tasks.py
│   │   └── ...
│   │
│   └── main.py          # FastAPI 应用入口
│
├── tests/               # 测试
│   ├── conftest.py      # Pytest fixtures
│   ├── unit/            # 单元测试
│   └── integration/     # 集成测试
│
├── .env.example         # 环境变量模板
├── requirements.txt     # 生产依赖
├── requirements-dev.txt # 开发依赖
└── pyproject.toml       # 项目配置
```

### Frontend (React/TypeScript)

```
frontend/
├── src/
│   ├── app/
│   │   ├── screens/      # 页面组件
│   │   │   ├── AnalyticsScreen.tsx
│   │   │   ├── EventsScreen.tsx
│   │   │   └── ...
│   │   │
│   │   ├── components/   # 可复用组件
│   │   │   ├── ui/       # 基础 UI 组件
│   │   │   │   ├── button.tsx
│   │   │   │   ├── input.tsx
│   │   │   │   └── ...
│   │   │   ├── ErrorBoundary.tsx
│   │   │   ├── TopBar.tsx
│   │   │   └── ...
│   │   │
│   │   ├── hooks/        # 自定义 Hooks
│   │   │   ├── useAuth.ts
│   │   │   ├── useApi.ts
│   │   │   └── ...
│   │   │
│   │   ├── lib/          # 工具函数
│   │   │   ├── api.ts    # API 客户端
│   │   │   ├── utils.ts  # 工具函数
│   │   │   └── ...
│   │   │
│   │   ├── constants/    # 常量
│   │   │   └── index.ts
│   │   │
│   │   └── App.tsx       # 根组件
│   │
│   └── main.tsx          # 应用入口
│
├── public/               # 静态资源
├── package.json
├── tsconfig.json         # TypeScript 配置
├── vite.config.ts        # Vite 配置
└── tailwind.config.js    # TailwindCSS 配置
```

### Runtime (.NET/C#)

```
runtime-dotnet/
├── src/
│   ├── Booth.Shared.Contracts/    # 共享契约
│   │   ├── DTOs/
│   │   ├── Enums/
│   │   └── Events/
│   │
│   ├── Booth.Domain.Session/      # 领域层
│   │   ├── SessionAggregate.cs
│   │   ├── Shot.cs
│   │   ├── ISessionRepository.cs
│   │   └── ...
│   │
│   ├── Booth.Infra.Storage.Sqlite/ # 基础设施层
│   │   ├── SqliteSessionRepository.cs
│   │   └── ...
│   │
│   ├── Booth.Runtime.ApiHost/     # API 主机
│   │   ├── Program.cs
│   │   ├── Controllers/
│   │   └── appsettings.json
│   │
│   ├── Booth.Runtime.App/         # WinUI 应用
│   │   ├── MainWindow.xaml
│   │   └── ...
│   │
│   └── Booth.Plugin.Abstractions/  # 插件 SDK
│       ├── ICameraPlugin.cs
│       └── IPrinterPlugin.cs
│
├── tests/
│   └── Booth.Tests/
│
└── Booth.Runtime.sln      # 解决方案文件
```

---

## 开发工作流

### 1. 创建新功能

```bash
# 1. 从 develop 创建分支
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name

# 2. 开发功能
# Backend: 添加 model → repository → service → API
# Frontend: 添加 component → screen → route
# Runtime: 添加 domain model → repository → service

# 3. 编写测试 / 检查
# Backend: pytest tests/
# Frontend: npm run typecheck && npm run build
# Runtime: dotnet test

# 4. 代码检查
make lint

# 5. 提交代码
git add .
git commit -m "feat(scope): description"

# 6. 推送并创建 PR
git push -u origin feature/your-feature-name
# 在 GitHub 创建 Pull Request
```

### 2. Backend 开发模式

#### 添加新 API 端点

```python
# 1. 定义 Pydantic Schema (app/schemas/user.py)
class UserCreate(BaseModel):
    email: EmailStr
    password: constr(min_length=8)

class UserResponse(BaseModel):
    id: UUID
    email: str
    created_at: datetime

# 2. 添加 Repository 方法 (app/repositories/user.py)
class UserRepository(BaseRepository[User]):
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

# 3. 添加 Service 逻辑 (app/services/user_service.py)
class UserService:
    async def create_user(
        self, 
        db: AsyncSession, 
        user_data: UserCreate
    ) -> User:
        # 业务逻辑
        hashed_password = hash_password(user_data.password)
        user = User(email=user_data.email, password=hashed_password)
        db.add(user)
        await db.commit()
        return user

# 4. 添加 API 路由 (app/api/v1/users.py)
@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    user: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    service = UserService()
    created_user = await service.create_user(db, user)
    return created_user
```

#### 数据库迁移

```bash
# 修改 model 后，生成迁移文件
alembic revision --autogenerate -m "add user table"

# 检查生成的迁移文件
cat alembic/versions/xxx_add_user_table.py

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

#### 添加后台任务

```python
# app/tasks/photo_tasks.py
from app.celery_app import celery_app

@celery_app.task(bind=True, max_retries=3)
def process_photo(self, photo_id: str):
    try:
        # 处理逻辑
        photo = download_photo(photo_id)
        processed = apply_ai_filter(photo)
        upload_result(processed)
        return {"status": "success"}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

# 调用任务
from app.tasks.photo_tasks import process_photo
process_photo.delay(photo_id)
```

### 3. Frontend 开发模式

#### 添加新页面

```tsx
// 1. 创建页面组件 (src/app/screens/UsersScreen.tsx)
import { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { User } from '../types';

export const UsersScreen: React.FC = () => {
  const { data: users, loading, error } = useApi<User[]>('/api/v1/users');

  if (loading) return <Spinner />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <div>
      <h1>Users</h1>
      {users?.map(user => (
        <UserCard key={user.id} user={user} />
      ))}
    </div>
  );
};

// 2. 添加路由 (src/app/App.tsx)
<Route path="/users" element={<UsersScreen />} />
```

#### 创建可复用组件

```tsx
// src/app/components/Button.tsx
interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  onClick,
  variant = 'primary',
  disabled = false
}) => {
  const baseClass = 'px-4 py-2 rounded-lg transition-colors';
  const variantClass = variant === 'primary' 
    ? 'bg-blue-600 text-white hover:bg-blue-700'
    : 'bg-gray-200 text-gray-800 hover:bg-gray-300';

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${baseClass} ${variantClass} disabled:opacity-50`}
    >
      {children}
    </button>
  );
};
```

### 4. Runtime 开发模式

#### 添加领域模型

```csharp
// src/Booth.Domain.Session/SessionAggregate.cs
public class SessionAggregate
{
    private readonly List<Shot> _shots = new();

    public Guid Id { get; private set; }
    public SessionStatus Status { get; private set; }
    public IReadOnlyList<Shot> Shots => _shots.AsReadOnly();

    public void Start()
    {
        if (Status != SessionStatus.Created)
            throw new InvalidOperationException("Session already started");
        
        Status = SessionStatus.Active;
        // 发布领域事件
        AddDomainEvent(new SessionStartedEvent(Id));
    }

    public void CaptureShot(string filePath, CaptureMetadata metadata)
    {
        if (Status != SessionStatus.Active)
            throw new InvalidOperationException("Session not active");

        var shot = new Shot
        {
            Id = Guid.NewGuid(),
            SessionId = Id,
            FilePath = filePath,
            Metadata = metadata,
            CapturedAt = DateTime.UtcNow
        };

        _shots.Add(shot);
        AddDomainEvent(new ShotCapturedEvent(Id, shot.Id));
    }
}
```

---

## 调试技巧

### Backend 调试

```python
# 使用 pdb 断点调试
import pdb; pdb.set_trace()

# 使用日志
from app.core.logging import logger
logger.debug(f"User data: {user}")
logger.info(f"Request from {request.client.host}")
logger.error(f"Failed to process: {exc}")

# 查看 SQL 查询
# 在 .env 设置
SQL_ECHO=True
```

### Frontend 调试

```typescript
// 使用 console.log
console.log('User data:', user);

// 使用 React DevTools
// Chrome 扩展：React Developer Tools

// 使用 debugger
function handleClick() {
  debugger;  // 执行到此处会暂停
  // ...
}

// 查看网络请求
// Chrome DevTools → Network tab
```

### Runtime 调试

```csharp
// 使用断点
// Visual Studio: F9 设置断点，F5 开始调试

// 使用日志
using Microsoft.Extensions.Logging;

private readonly ILogger<MyClass> _logger;

_logger.LogInformation("Session {SessionId} started", sessionId);
_logger.LogError(ex, "Failed to capture shot");

// 使用 Debug.WriteLine
System.Diagnostics.Debug.WriteLine($"Value: {value}");
```

---

## 测试指南

### Backend 测试

```python
# tests/unit/test_user_service.py
import pytest
from app.services.user_service import UserService
from app.schemas.user import UserCreate

@pytest.mark.asyncio
async def test_create_user_success(db_session):
    # Arrange
    service = UserService()
    user_data = UserCreate(email="test@example.com", password="password123")
    
    # Act
    user = await service.create_user(db_session, user_data)
    
    # Assert
    assert user.email == "test@example.com"
    assert user.id is not None

@pytest.mark.asyncio
async def test_create_user_duplicate_email(db_session):
    # Arrange
    service = UserService()
    user_data = UserCreate(email="test@example.com", password="password123")
    await service.create_user(db_session, user_data)
    
    # Act & Assert
    with pytest.raises(ValueError, match="Email already exists"):
        await service.create_user(db_session, user_data)
```

### Frontend 测试

> 前端当前**未接入单元测试框架**（package.json 无 Jest/Vitest 依赖）。前端质量门禁为类型检查与构建：

```bash
npm run typecheck   # tsc --noEmit
npm run build       # tsc --noEmit && vite build
```

若后续引入 Vitest + testing-library，可参考以下组件测试形态（示例，尚未接入）：

```typescript
// 示例：待接入 Vitest 后可用
// tests/components/Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '../components/Button';

describe('Button', () => {
  it('renders children correctly', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Click me</Button>);
    expect(screen.getByText('Click me')).toBeDisabled();
  });
});
```

### Runtime 测试

```csharp
// tests/Booth.Tests/SessionAggregateTests.cs
using Xunit;
using Booth.Domain.Session;

public class SessionAggregateTests
{
    [Fact]
    public void Start_WhenCreated_SetsStatusToActive()
    {
        // Arrange
        var session = new SessionAggregate(Guid.NewGuid());

        // Act
        session.Start();

        // Assert
        Assert.Equal(SessionStatus.Active, session.Status);
    }

    [Fact]
    public void CaptureShot_WhenNotActive_ThrowsException()
    {
        // Arrange
        var session = new SessionAggregate(Guid.NewGuid());

        // Act & Assert
        Assert.Throws<InvalidOperationException>(() =>
            session.CaptureShot("/path/photo.jpg", new CaptureMetadata())
        );
    }
}
```

---

## 常见问题

### Backend

**Q: 数据库连接错误**
```bash
# 检查 PostgreSQL 是否运行
docker ps | grep postgres

# 检查连接字符串
echo $DATABASE_URL

# 手动连接测试
psql $DATABASE_URL
```

**Q: 模块导入错误**
```bash
# 确保虚拟环境已激活
source venv/bin/activate

# 重新安装依赖
pip install -r requirements.txt
```

### Frontend

**Q: 依赖安装失败**
```bash
# 清理缓存
rm -rf node_modules
npm ci
```

**Q: 类型错误**
```bash
# 运行类型检查
npm run typecheck
```

### Runtime

**Q: 构建失败**
```bash
# 清理并重建
dotnet clean
dotnet restore
dotnet build
```

**Q: SQLite 锁定错误**
```bash
# 关闭所有运行的实例
# 删除数据库文件
rm data/booth.db
# 重新运行
dotnet run
```

---

## 性能优化清单

- [ ] Backend: 添加数据库索引
- [ ] Backend: 使用查询缓存
- [ ] Backend: 优化 N+1 查询
- [ ] Frontend: 代码分割
- [ ] Frontend: 图片懒加载
- [ ] Frontend: 虚拟滚动
- [ ] Runtime: 内存池
- [ ] Runtime: 并行处理

---

## 安全检查清单

- [ ] 输入验证
- [ ] SQL 注入防护
- [ ] XSS 防护
- [ ] CSRF 保护
- [ ] 认证授权
- [ ] 敏感数据加密
- [ ] 审计日志
- [ ] 依赖漏洞扫描

---

**保持文档同步**：代码变更时请更新本文档。

**有问题**？查看 [CONTRIBUTING.md](./CONTRIBUTING.md) 或联系团队。
