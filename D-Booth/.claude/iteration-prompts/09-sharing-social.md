# 分享与社交集成 - 迭代提示词

## 目标
将当前仅支持二维码/AirDrop/微信/邮件/云端的分享系统扩展为支持SMS(Twilio)、Facebook、WhatsApp、云端相册等全渠道分享，实现分享统计和分析。

## 当前状态
- `SharingScreen.tsx` 有5种分享方式(二维码/AirDrop/微信/邮件/云端)
- `share_service.py` 有分享短链生成、浏览计数、7天过期
- 但SMS/Facebook/WhatsApp等渠道未实现
- 邮件发送仅有链接生成，无实际SMTP发送
- 微信分享仅生成链接，无微信JS-SDK集成

## 需要实现的功能

### 9.1 后端: 邮件发送服务
**新建文件:** `backend/app/services/email_service.py`

1. SMTP邮件发送:
   ```python
   async def send_photo_email(
       to_email: str,
       subject: str,
       html_body: str,
       photo_urls: List[str],
       share_url: str,
       from_email: str
   ) -> bool:
   ```

2. 邮件模板:
   - HTML邮件(支持模板变量)
   - 变量: {photo_url}, {share_url}, {event_name}, {date}
   - 内嵌照片或照片链接
   - 分享图标/按钮

3. 使用 `aiosmtplib` 异步SMTP:
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=xxx
   SMTP_PASSWORD=xxx
   SMTP_FROM=photobooth@example.com
   ```

#### 邮件API:
```
POST   /api/v1/shares/email/send      → 发送照片邮件
POST   /api/v1/shares/email/test      → 发送测试邮件
```

### 9.2 后端: SMS分享(Twilio)
**新建文件:** `backend/app/services/sms_service.py`

1. Twilio集成:
   ```python
   async def send_photo_sms(
       to_phone: str,
       message: str,          # 支持变量 {share_url}
       share_url: str,
       country_code: str = "+86"
   ) -> bool:
   ```

2. SMS验证:
   - 手机号格式验证
   - 发送频率限制(防滥用)
   - 发送状态记录

#### SMS API:
```
POST   /api/v1/shares/sms/send        → 发送SMS分享
POST   /api/v1/shares/sms/test        → 测试Twilio配置
```

### 9.3 后端: Facebook Page分享
**新建文件:** `backend/app/services/facebook_service.py`

1. Facebook Graph API集成:
   ```python
   async def post_to_facebook_page(
       page_id: str,
       access_token: str,
       photo_url: str,
       message: str,
       album_id: Optional[str] = None
   ) -> str:  # 返回帖子ID
   ```

2. OAuth流程:
   - `GET /api/v1/shares/facebook/login` → 获取授权URL
   - `GET /api/v1/shares/facebook/callback` → 处理回调
   - 存储page access token

3. 功能:
   - 选择发布到的页面
   - 选择相册
   - 需要来宾批准(配置项)
   - 自定义帖子文本

### 9.4 后端: WhatsApp分享
**新建文件:** `backend/app/services/whatsapp_service.py`

1. WhatsApp Business API 或 Twilio WhatsApp:
   ```python
   async def send_whatsapp_message(
       to_phone: str,
       photo_url: str,
       caption: str
   ) -> bool:
   ```

### 9.5 后端: 云端相册(Customer Gallery)
**新建文件:** `backend/app/services/gallery_service.py`

1. 公开相册功能:
   - 为每个事件创建公开相册
   - 访客通过事件链接访问相册
   - 密码保护(可选)
   - 过期时间设置

#### 公开相册API:
```
GET    /api/v1/gallery/{event_slug}           → 公开访问相册
POST   /api/v1/gallery/{event_slug}/download  → 下载照片(需输入邮箱)
```

### 9.6 后端: 分享统计分析
**修改文件:** `backend/app/services/share_service.py`

1. 增强分享统计:
   ```python
   async def get_share_statistics(event_id: UUID) -> ShareStatistics:
       return ShareStatistics(
           total_shares=...,
           by_channel={'email': 45, 'sms': 23, 'qr': 120, 'facebook': 8},
           total_views=...,
           total_downloads=...,
           top_photos=...,
           share_timeline=[...],  # 按时间分布
       )
   ```

### 9.7 前端: 分享屏幕重构
**修改文件:** `frontend/src/app/screens/SharingScreen.tsx`

1. 分享渠道扩展:
   ```
   [二维码] [AirDrop] [微信] [邮件] [短信] [WhatsApp] [Facebook]
   ```

2. 每个渠道的实现:
   - **二维码**: 已有，保持
   - **AirDrop**: Web Share API `navigator.share()`
   - **微信**: 显示二维码供微信扫码(微信内无法直接调起)
   - **邮件**: 弹出邮箱输入 → `POST /shares/email/send`
   - **短信**: 弹出手机号输入(含国家代码选择) → `POST /shares/sms/send`
   - **WhatsApp**: `https://wa.me/?text=...` URL scheme
   - **Facebook**: `POST /shares/facebook/post` (需先登录)

3. 分享设置(管理员可配置):
   - 启用/禁用各渠道
   - 自定义邮件/短信模板文本
   - 设置发件人地址
   - 测试各渠道配置

### 9.8 前端: 分享设置页面(管理员)
**新建文件:** `frontend/src/app/screens/ShareSettingsScreen.tsx`

1. 配置项:
   - SMTP邮件配置
   - Twilio SID/Token配置
   - Facebook App ID/Secret配置
   - WhatsApp Business ID配置
   - 各渠道启用开关
   - 模板文本自定义

### 9.9 前端: Wi-Fi QR码(来宾上网)
**修改文件:** `frontend/src/app/screens/SharingScreen.tsx`

添加Wi-Fi连接引导:
- 显示Wi-Fi名/密码
- 一键生成Wi-Fi连接二维码
- Wi-Fi加密类型选择(WPA2/WPA3)

## 验收标准
1. 邮件分享: 输入邮箱 → 点击发送 → 收到含照片链接的HTML邮件
2. SMS分享: 输入手机号 → 点击发送 → 收到含短链的短信
3. Facebook: 授权登录 → 选择页面/相册 → 照片发布到Facebook
4. WhatsApp: 点击分享 → 跳转WhatsApp → 预填照片链接
5. 云端相册: 访客可通过链接浏览活动所有照片
6. 分享统计: 仪表盘显示各渠道分享次数/浏览/下载数据
7. 各渠道发送频率限制正常工作(防滥用)

## 技术选型建议
- 邮件: `aiosmtplib` (异步SMTP)
- SMS: `twilio` Python SDK
- Facebook: `facebook-business` SDK 或直接Graph API HTTP请求
- WhatsApp: Twilio WhatsApp API 或 `https://wa.me/` URL scheme
