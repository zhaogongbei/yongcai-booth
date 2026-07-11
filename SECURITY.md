# Security Policy

## 安全公告

咏彩Booth 团队非常重视安全问题。本文档说明如何报告安全漏洞以及我们的处理流程。

## 支持的版本

| 版本 | 支持状态 | 安全更新 |
|------|---------|----------|
| 1.0.x | ✅ 支持 | 是 |
| < 1.0 | ❌ 不支持 | 否 |

## 报告安全漏洞

**请勿在公共 Issue 中报告安全漏洞。**

### 报告渠道

请通过以下方式之一报告安全问题：

1. **电子邮件**: security@dbooth.ai
2. **加密通信**: 使用我们的 PGP 公钥（附后）
3. **企业微信**: [内部安全响应群]

### 报告内容

请在报告中包含以下信息：

- 漏洞类型（SQL注入、XSS、CSRF等）
- 受影响的组件/模块
- 重现步骤（PoC）
- 潜在影响评估
- 建议的修复方案（可选）
- 您的联系方式

### 响应时间承诺

- **确认接收**: 24小时内
- **初步评估**: 48小时内
- **修复计划**: 7天内（高危）/ 14天内（中危）
- **补丁发布**: 根据严重程度，1-30天

## 安全最佳实践

### 部署安全

#### 1. 环境变量保护

```bash
# ❌ 错误：明文存储密钥
SECRET_KEY=my-secret-key-123

# ✅ 正确：使用环境变量管理工具
# 使用 AWS Secrets Manager / Azure Key Vault / HashiCorp Vault
```

#### 2. 数据库安全

```python
# ✅ 使用参数化查询（SQLAlchemy 自动处理）
result = await db.execute(
    select(User).where(User.email == email)
)

# ❌ 禁止：字符串拼接 SQL
query = f"SELECT * FROM users WHERE email = '{email}'"  # SQL注入风险
```

#### 3. HTTPS 强制

```nginx
# Nginx 配置
server {
    listen 443 ssl http2;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.3 TLSv1.2;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

#### 4. CORS 配置

```python
# ✅ 限制允许的源
CORS_ORIGINS = [
    "https://app.dbooth.ai",
    "https://admin.dbooth.ai"
]

# ❌ 禁止：允许所有源
CORS_ORIGINS = ["*"]  # 生产环境禁止
```

#### 5. 输入验证

```python
# ✅ 使用 Pydantic 验证
from pydantic import BaseModel, EmailStr, constr

class UserCreate(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=128)
    username: constr(pattern=r'^[a-zA-Z0-9_-]{3,20}$')
```

#### 6. 文件上传安全

```python
# ✅ 验证文件类型和大小
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_image(file: UploadFile):
    # 检查扩展名
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Invalid file type")
    
    # 检查 MIME 类型
    if not file.content_type.startswith('image/'):
        raise ValueError("Not an image file")
    
    # 检查文件大小
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_FILE_SIZE:
        raise ValueError("File too large")
    
    # 使用 Pillow 验证图像完整性
    try:
        img = Image.open(file.file)
        img.verify()
        file.file.seek(0)
    except Exception:
        raise ValueError("Invalid image file")
```

#### 7. 认证与授权

```python
# ✅ 实施多层防护
@router.get("/teams/{team_id}/sensitive-data")
async def get_sensitive_data(
    team_id: UUID,
    current_user: User = Depends(require_auth),  # 认证
    _: None = Depends(require_role("admin")),     # 角色检查
    db: AsyncSession = Depends(get_db)
):
    # 多租户隔离
    team = await team_repo.get_by_id(db, team_id)
    if team.id != current_user.team_id:
        raise HTTPException(403, "Access denied")
    
    # 审计日志
    await audit_log.record(
        user_id=current_user.id,
        action="access_sensitive_data",
        resource=f"team:{team_id}"
    )
    
    return await get_data(team_id)
```

#### 8. 密码策略

```python
import bcrypt

# ✅ 使用 bcrypt 哈希密码
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# 密码强度要求
PASSWORD_POLICY = {
    "min_length": 8,
    "require_uppercase": True,
    "require_lowercase": True,
    "require_digit": True,
    "require_special": True,
}
```

#### 9. 速率限制

```python
# ✅ API 速率限制
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/auth/login")
@limiter.limit("5/minute")  # 每分钟最多5次登录尝试
async def login(credentials: LoginRequest):
    # ...
```

#### 10. 日志安全

```python
# ✅ 脱敏敏感信息
import logging

logger = logging.getLogger(__name__)

def mask_sensitive(data: dict) -> dict:
    """脱敏敏感字段"""
    sensitive_fields = {'password', 'token', 'secret', 'api_key'}
    return {
        k: '***REDACTED***' if k in sensitive_fields else v
        for k, v in data.items()
    }

# 记录日志
logger.info(f"User login: {mask_sensitive(user_data)}")
```

### 前端安全

#### 1. XSS 防护

```typescript
// ✅ React 自动转义
<div>{userInput}</div>  // 安全

// ❌ 危险：使用 dangerouslySetInnerHTML
<div dangerouslySetInnerHTML={{ __html: userInput }} />  // 禁止

// ✅ 如必须使用，需先消毒
import DOMPurify from 'dompurify';
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(userInput) }} />
```

#### 2. CSRF 防护

```typescript
// ✅ 在所有修改请求中包含 CSRF Token
const csrfToken = await fetchCsrfToken();

await fetch('/api/v1/events', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRF-Token': csrfToken,
  },
  body: JSON.stringify(eventData),
});
```

#### 3. 敏感数据存储

```typescript
// ❌ 禁止：在 localStorage 存储敏感信息
localStorage.setItem('token', jwt);  // 易受 XSS 攻击

// ✅ 使用 HttpOnly Cookie（后端设置）
// 或使用内存存储（页面刷新需重新登录）
const tokenStore = new Map<string, string>();
```

### 依赖安全

#### 定期审计

```bash
# Python
pip install -r D-Booth/backend/requirements-dev.txt
python -m pip_audit -r D-Booth/backend/requirements.txt -r D-Booth/backend/requirements-dev.txt --strict

# Node.js
cd D-Booth/frontend
npm run audit:security

# .NET
dotnet list package --vulnerable
```

#### 依赖版本固定

```txt
# requirements.txt - 使用精确版本
fastapi==0.109.0
sqlalchemy==2.0.25

# 禁止：宽松版本
fastapi>=0.100.0  # 可能引入破坏性变更
```

## 已知安全问题

当前无公开披露的已知安全问题。发现漏洞请按上文「报告安全漏洞」流程私下上报。

## 安全审计

尚未安排第三方安全审计。安排后在此登记审计方、日期与结论。

## 漏洞赏金计划

咏彩Booth 目前提供内部漏洞赏金计划：

| 严重程度 | 奖励金额 |
|---------|---------|
| 严重 (Critical) | ¥10,000 - ¥50,000 |
| 高 (High) | ¥5,000 - ¥10,000 |
| 中 (Medium) | ¥1,000 - ¥5,000 |
| 低 (Low) | ¥500 - ¥1,000 |

### 排除范围

- 社会工程攻击
- 物理攻击
- DoS/DDoS 攻击
- 已知的第三方库漏洞（未修复时）
- 需要用户交互的漏洞（钓鱼等）

---

**安全无小事，感谢您的关注和支持！**

如有任何安全相关问题，请联系: security@dbooth.ai
