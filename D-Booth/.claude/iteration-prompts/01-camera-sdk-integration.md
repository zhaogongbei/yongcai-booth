# 物理相机SDK集成 - 迭代提示词

## 目标
将当前仅支持Web摄像头的拍照系统升级为支持Canon/Nikon DSLR通过USB连接进行远程控制的专业拍照系统。

## 当前状态
- `CameraScreen.tsx` 使用 `navigator.mediaDevices.getUserMedia` 获取Web摄像头流
- 相机参数面板(ISO/快门/白平衡/曝光/对焦)仅为前端模拟展示，不控制真实硬件
- `useCaptureFlow.tsx` 的 `addPhoto` 通过Canvas帧捕获生成Blob
- 后端 `photo_service.py` 处理上传，但与硬件无关

## 需要实现的功能

### 2.1 后端: 相机SDK桥接层
**新建文件:** `backend/app/services/camera_service.py`

1. 创建 `CameraController` 抽象基类:
   - `connect() -> bool`
   - `disconnect()`
   - `get_live_view() -> bytes` (返回实时取景帧)
   - `capture() -> bytes` (拍摄并下载原片)
   - `set_shutter_speed(value: str)`
   - `set_aperture(value: str)`
   - `set_iso(value: int)`
   - `set_white_balance(mode: str)`
   - `get_camera_settings() -> dict`
   - `is_connected() -> bool`

2. 实现 `CanonCameraController(CameraController)`:
   - 使用 `ctypes` 或 `subprocess` 调用 Canon EDSDK
   - 或者封装 `gphoto2` (Windows可通过WSL或编译好的二进制)
   - 实现上述所有抽象方法

3. 实现 `NikonCameraController(CameraController)`:
   - 封装 Nikon SDK 或 gphoto2
   - 实现上述所有抽象方法

4. 实现 `WebcamCameraController(CameraController)`:
   - 保留当前的Web摄像头逻辑作为fallback
   - 适配为统一接口

5. 创建 `CameraManager` 单例:
   - 自动检测连接的相机型号
   - 选择对应的Controller
   - 相机连接/断开事件通知(WebSocket广播)

### 2.2 后端: 实时取景WebSocket
**新建文件:** `backend/app/api/v1/live_view.py`

1. WebSocket端点 `ws /api/v1/live-view/{camera_id}`:
   - 以30fps推送MJPEG帧
   - 支持启停控制消息
   - 协议: `{"type": "start"|"stop"|"settings", "data": {...}}`

### 2.3 后端: 相机设置API
**修改文件:** `backend/app/api/v1/photos.py` (或新建 `camera.py`)

```
GET    /api/v1/camera/status          → 相机连接状态、型号、固件
POST   /api/v1/camera/connect         → 连接相机
POST   /api/v1/camera/disconnect      → 断开相机
GET    /api/v1/camera/settings        → 当前曝参(光圈/快门/ISO/WB)
PUT    /api/v1/camera/settings        → 修改曝参
POST   /api/v1/camera/capture        → 远程触发拍摄，下载原片到本地
GET    /api/v1/camera/capabilities    → 相机能力(支持的ISO范围/WB模式等)
```

### 2.4 后端: 相机设置向导
**新建文件:** `backend/app/services/camera_wizard_service.py`

1. 引导式设置流程:
   - Step 1: 检测相机型号 → 加载对应预设
   - Step 2: "是否使用闪光灯?" → 调整参数建议
   - Step 3: 拍摄测试照片 → 分析曝光 → 建议ISO/快门/光圈调整
   - Step 4: 闪光灯功率配置
   - Step 5: 最终确认

2. 测试照片分析(使用Pillow):
   - 亮度直方图分析(过暗/过亮检测)
   - 自动提供参数修改建议

### 2.5 前端: 相机屏幕重构
**修改文件:** `frontend/src/app/screens/CameraScreen.tsx`

1. 替换 `navigator.mediaDevices` 为后端WebSocket实时取景流:
   - 使用 `<img src="blob:...">` 替代 `<video>`
   - 或者在video元素上设置srcObject为MediaStream(Web摄像头模式)

2. 添加相机连接状态指示器:
   - 已连接(绿色) / 未连接(红色) / 检测中(黄色)
   - 相机型号显示

3. 相机参数面板改为真实控制:
   - ISO滑块联动 `PUT /camera/settings`
   - 快门速度下拉联动
   - 白平衡模式选择联动

4. 拍摄流程改为后端触发:
   - `shoot()` → `POST /camera/capture` → 下载原片 → `addPhoto`

5. 添加相机设置向导入口按钮

### 2.6 前端: 新增相机向导页面
**新建文件:** `frontend/src/app/screens/CameraWizardScreen.tsx`

1. 多步骤向导UI(参考dslrBooth):
   - 步骤指示器(1/2/3/4/5)
   - 每步的配置表单
   - 测试照片展示区域
   - 上一步/下一步导航

## 验收标准
1. Canon相机通过USB连接到PC后，系统能自动识别并建立连接
2. 实时取景画面延迟<200ms
3. 能通过前端界面上修改快门/光圈/ISO/WB，设置实时生效
4. 点击拍照按钮后，相机真实拍摄并下载原片到本地
5. 断电/拔线后系统能检测到断开状态并提示用户
6. 无DSLR时自动降级为Web摄像头模式，不影响基本功能
7. 相机设置向导能正确分析测试照片并提供建议

## 技术选型建议
- 优先使用 `gphoto2` (跨平台，支持Canon/Nikon/GoPro等1000+型号)
- Windows上可将gphoto2编译为DLL通过ctypes调用
- 备选: Canon EDSDK直接集成(仅支持Canon)
- WebSocket库: FastAPI原生支持，无需额外依赖
