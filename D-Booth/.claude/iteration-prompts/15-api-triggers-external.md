# API安全、触发器与外部集成 - 迭代提示词

## 目标
实现外部触发器(URL/应用回调)系统、通信API完善、第三方应用集成(LumaShare/OrcaVue等)，增强平台的开放性和可集成性。

## 当前状态
- `main.py` 有基础的速率限制和安全头部
- 有API密码保护框架
- 无触发器系统
- 无第三方硬件集成

## 需要实现的功能

### 15.1 外部触发器系统

#### 后端: 触发器服务
**新建文件:** `backend/app/services/trigger_service.py`

1. 触发器类型:
   ```python
   class TriggerType(str, Enum):
       SESSION_START = "session_start"          # 会话开始
       COUNTDOWN_START = "countdown_start"      # 倒计时开始
       CAPTURE_START = "capture_start"          # 拍照瞬间
       FILE_DOWNLOAD = "file_download"          # 照片下载完成
       PROCESSING_START = "processing_start"    # 处理开始
       SHARING_SCREEN = "sharing_screen"        # 分享屏幕出现
       SESSION_END = "session_end"              # 会话结束
       PRINTING = "printing"                    # 打印开始
   ```

2. 触发器动作:
   - **应用触发器**: 执行本地可执行程序/脚本
     ```python
     async def execute_app_trigger(
         event_type: TriggerType,
         app_path: str,  # "C:\\scripts\\flash_light.exe"
         args: List[str]
     ):
         # 使用asyncio.create_subprocess_exec
     ```
   
   - **URL回调**: HTTP POST到指定URL
     ```python
     async def execute_url_trigger(
         event_type: TriggerType,
         url: str,  # "http://192.168.1.100:8080/hook"
         payload: dict  # {event_type, session_id, photo_count, ...}
     ):
         # 使用httpx异步POST
         # 带重试机制(3次, 间隔1/2/4秒)
     ```

3. 触发器配置:
   ```python
   class TriggerConfig(BaseModel):
       event_type: TriggerType
       enabled: bool
       type: Literal["app", "url"]
       target: str          # 可执行路径或URL
       args: List[str]      # 应用参数或URL GET参数
       timeout: int = 10    # 超时时间(秒)
       retry: int = 3       # 重试次数
   ```

#### 触发器API:
```
GET    /api/v1/triggers/{event_id}   → 获取事件触发器配置
PUT    /api/v1/triggers/{event_id}   → 更新触发器配置
POST   /api/v1/triggers/test         → 测试触发器
```

### 15.2 通信API完善

#### 修改: API文档和示例
**修改文件:** `backend/app/main.py`

1. OpenAPI文档增强:
   - 添加详细的endpoint描述
   - 添加请求/响应示例
   - 添加错误码说明

2. API密钥管理:
   ```python
   class APIKey(BaseModel):
       id: UUID
       name: str
       key_hash: str
       permissions: List[str]  # ["read:photos", "write:events"]
       created_at: datetime
       last_used: Optional[datetime]
       expires_at: Optional[datetime]
   ```

#### 通信API:
```
POST   /api/v1/api-keys                   → 创建API密钥
GET    /api/v1/api-keys                   → 列出API密钥
DELETE /api/v1/api-keys/{id}              → 撤销API密钥
POST   /api/v1/communication/{event_id}/trigger/{type} → 手动触发事件
```

### 15.3 GoPro摄像机集成
**新建文件:** `backend/app/services/gopro_service.py`

1. GoPro连接:
   ```python
   class GoProController:
       async def discover() -> List[GoProDevice]:
           """通过WiFi发现GoPro"""
       
       async def connect(device: GoProDevice) -> bool:
           """连接GoPro (WiFi/USB)"""
       
       async def start_recording() -> bool:
           """开始录制(视频模式)"""
       
       async def stop_recording() -> bytes:
           """停止录制并下载视频"""
       
       async def take_photo() -> bytes:
           """拍摄照片(WiFi远程控制)"""
       
       async def get_status() -> GoProStatus:
           """获取电池/SD卡/WiFi状态"""
       
       async def set_mode(mode: str):
           """设置拍摄模式"""
   ```

2. GoPro HTTP API:
   - GoPro通过WiFi提供REST API
   - 配对流程: 扫描AP → 连接WiFi → HTTP控制
   - 主要端点: `/gp/gpControl/command/...`

### 15.4 OrcaVue 360旋转台集成
**新建文件:** `backend/app/services/orcavue_service.py`

1. 旋转台控制:
   ```python
   class OrcaVueController:
       async def connect() -> bool:
           """通过串口/蓝牙连接旋转台"""
       
       async def rotate_speed(speed: int) -> None:
           """设置旋转速度"""
       
       async def start_rotation() -> None:
           """开始旋转(触发360拍摄)"""
       
       async def stop_rotation() -> None:
           """停止旋转"""
       
       async def home_position() -> None:
           """归零"""
   ```

2. 360拍摄流程:
   - 旋转台开始旋转
   - 同步触发相机按固定角度间隔拍摄
   - 旋转360°后停止
   - 生成360°可交互照片

### 15.5 运动检测(平板倾斜触发)
**新建文件:** `frontend/src/app/hooks/useMotionDetection.ts`

1. 基于DeviceMotion API:
   ```typescript
   function useMotionDetection(options: {
     sensitivity: number;  // 灵敏度 0-100
     onTrigger: () => void;
     enabled: boolean;
   }) {
     // 监听 devicemotion 事件
     // 当加速度超过阈值时触发
   }
   ```

2. 用于:
   - 平板倾斜→自动开始拍照(无需触摸)
   - 更自然的交互体验

### 15.6 Webhook通知系统
**新建文件:** `backend/app/services/webhook_service.py`

1. Webhook配置:
   ```python
   class Webhook(BaseModel):
       id: UUID
       team_id: UUID
       url: str
       events: List[str]  # ["photo.created", "print.completed", "event.started"]
       secret: str        # HMAC签名密钥
       enabled: bool
   ```

2. Webhook发送:
   ```python
   async def dispatch_webhook(event_type: str, payload: dict):
       # 查找匹配的webhook
       # 生成HMAC-SHA256签名
       # HTTP POST
       # 记录发送日志
   ```

#### Webhook API:
```
POST   /api/v1/webhooks                → 创建Webhook
GET    /api/v1/webhooks                → 列出Webhook
DELETE /api/v1/webhooks/{id}           → 删除Webhook
GET    /api/v1/webhooks/{id}/logs      → Webhook发送日志
```

## 验收标准
1. 拍照瞬间能触发外部脚本执行(如闪光灯控制)
2. 会话结束时能HTTP回调通知外部服务
3. API密钥可创建/管理，不同权限级别正常工作
4. GoPro通过WiFi能被发现和连接
5. GoPro状态(电池/SD卡/信号)能实时显示
6. OrcaVue旋转台能正确控制旋转速度和启停
7. Webhook签名验证正确，接收方能验签

## 技术选型建议
- 子进程: `asyncio.create_subprocess_exec`
- HTTP回调: `httpx` (已使用)
- 串口通信: `pyserial`
- 运动检测: DeviceMotion API (前端)
