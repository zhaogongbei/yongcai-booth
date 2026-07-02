# 物理打印机集成 - 迭代提示词

## 目标
将当前仅API定义层的打印系统升级为支持Windows物理打印机发现、状态监控、打印任务提交和模板渲染的专业打印系统。

## 当前状态
- `print_service.py` 有完整的打印任务状态机(PENDING→QUEUED→PRINTING→COMPLETED/FAILED/CANCELLED)
- `PrintScreen.tsx` 有完整的打印设置UI(打印机选择/纸张/数量/色彩)
- 但实际打印执行是模拟的，无物理打印机对接
- 模板渲染为可打印图像的逻辑完全缺失

## 需要实现的功能

### 2.1 后端: Windows打印系统集成
**新建文件:** `backend/app/services/printer_driver_service.py`

1. 打印机发现:
   ```
   GET /api/v1/printers/              → 列出系统所有打印机
   GET /api/v1/printers/{name}/status → 打印机状态(就绪/缺纸/墨尽/离线)
   ```
   - 使用 `win32print` (pywin32) 枚举打印机
   - 使用 `win32print.GetPrinter()` 获取状态信息

2. 打印任务提交:
   ```
   POST /api/v1/print-jobs/{id}/execute → 将打印任务发送到物理打印机
   ```
   - 使用 `win32print` 提交打印任务
   - 或者使用 `subprocess` 调用系统打印命令
   - 监控打印任务状态回调

3. 打印队列管理:
   - `GET /api/v1/printers/{name}/queue` → 当前队列中的任务
   - `DELETE /api/v1/printers/{name}/queue/{job_id}` → 取消指定打印任务

### 2.2 后端: 模板渲染引擎
**新建文件:** `backend/app/services/template_render_service.py`

这是核心功能 - 将模板JSON定义渲染为可打印的图像文件。

1. `TemplateRenderer` 类:
   - `render(template: Template, photos: List[Photo]) -> bytes` → 返回JPEG/PNG字节
   - 使用 Pillow (PIL) 进行图层合成

2. 支持的图层类型渲染:
   - **照片占位符**: 按预设坐标/尺寸放置照片，支持裁剪/缩放
   - **背景颜色/渐变/图案**: 创建底色图层
   - **文本**: 自定义字体/大小/颜色，支持变量替换
     - `{date}`, `{time}`, `{datetime}`, `{event_name}`, `{session_number}`, `{filename}`
   - **形状**: 线条/矩形/椭圆/星形，支持填充色/描边
   - **二维码**: 使用qrcode库生成
   - **调查答案**: `{survey_answer_1}`, `{survey_answer_2}` 等
   - **来宾签名**: 签名PNG叠加
   - **贴纸/道具**: 透明PNG叠加，支持缩放/旋转

3. 渲染参数:
   - 纸张尺寸: 2×6英寸, 4×6英寸, 6×8英寸
   - 分辨率: 300 DPI (打印), 150 DPI (预览)
   - 方向: 竖版/横版
   - 色彩模式: RGB/CMYK (自动转换)

4. 2x6经典照片条布局:
   - 4张照片垂直排列
   - 特定尺寸和间距
   - 品牌Logo/文字区域

### 2.3 后端: 打印配置管理
**修改文件:** `backend/app/services/print_service.py`

新增功能:
1. 打印对齐校准:
   - `POST /api/v1/printers/{name}/calibrate` → 打印测试页
   - `PUT /api/v1/printers/{name}/calibration` → 保存校准参数(缩放%/水平偏移/垂直偏移)

2. 打印限制:
   - 每事件最大打印数
   - 每会话最大打印窗口数
   - 打印间隔防重复

3. 双打印机支持:
   - 主打印机/辅助打印机配置
   - 交替打印模式(奇偶分发)
   - `POST /api/v1/print-jobs/{id}/assign-printer` → 指定打印机

4. 自动旋转适应:
   - 检测照片方向与纸张方向的匹配
   - 自动旋转以最大化利用纸张

### 2.4 后端: 打印状态回调
**新建文件:** `backend/app/tasks/print_tasks.py`

1. Celery任务 `execute_print_job`:
   - 接收 print_job_id
   - 调用 `TemplateRenderService.render()` 生成打印图像
   - 调用 `PrinterDriverService.send_to_printer()` 发送到打印机
   - 轮询打印机状态直至完成/失败
   - 更新 PrintJob 状态

2. 墨水/耗材监控:
   - 定时(每5分钟)查询打印机状态
   - 低墨/缺纸告警 → 写入日志 + 前端通知

### 2.5 前端: 打印屏幕增强
**修改文件:** `frontend/src/app/screens/PrintScreen.tsx`

1. 真实打印机列表:
   - 替换硬编码的 `PRINTERS` 常量
   - 调用 `GET /api/v1/printers/` 获取在线打印机
   - 显示打印机状态(就绪/缺纸/离线)

2. 打印对齐校准界面:
   - 缩放滑块(90%-110%)
   - 水平/垂直偏移微调(像素)
   - "打印测试页"按钮
   - 预览校准效果

3. 打印队列显示:
   - 显示当前排队任务
   - 取消排队任务
   - 重试失败任务

4. 打印限制提示:
   - 显示剩余可打印张数
   - 超出限制时禁用打印按钮

5. 打印模板预览:
   - 调用模板渲染预览API
   - 显示实际将要打印的图像(含所有图层合成后的效果)
   - 缩放查看细节

### 2.6 前端: 新增打印校准页面
**新建文件:** `frontend/src/app/screens/PrinterCalibrationScreen.tsx`

1. 校准向导UI:
   - Step 1: 选择打印机
   - Step 2: 打印测试页
   - Step 3: 测量实际输出 → 输入偏移值
   - Step 4: 保存校准参数

## 验收标准
1. 系统能自动发现并列出Windows中安装的所有打印机
2. 打印机状态(就绪/缺纸/墨水不足/离线)能实时显示在界面
3. 模板渲染引擎能正确合成照片、文字、形状、二维码等图层
4. 点击打印后，渲染后的图像真实发送到物理打印机
5. 打印任务状态(PENDING→QUEUED→PRINTING→COMPLETED/FAILED)正确流转
6. 打印失败时能重试和通知用户
7. 2x6经典照片条能正确打印(4张照片垂直排列)
8. 双打印机交替打印模式能正常工作

## 技术选型建议
- Windows打印: `pywin32` (win32print, win32ui)
- 图像处理: `Pillow` + `pillow-avif-plugin`
- CMYK转换: `Pillow` 内置 (image.convert("CMYK"))
- 二维码: `qrcode[pil]`
- 备选方案: `python-escpos` (如果使用ESC/POS热敏打印机)
