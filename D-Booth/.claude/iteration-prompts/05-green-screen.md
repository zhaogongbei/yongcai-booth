# 绿幕与背景替换 - 迭代提示词

## 目标
实现色度键控(chroma key)绿幕抠图和AI人像分割两种背景替换方案，支持多背景管理、自动轮换和实时预览。

## 当前状态
- 项目完全无绿幕相关功能
- 仅在 `photo_service.py` 中有基础的背景移除占位逻辑
- 无任何抠图算法实现

## 需要实现的功能

### 5.1 后端: 色度键控(传统绿幕)
**新建文件:** `backend/app/services/green_screen_service.py`

1. 色度键抠图 `chroma_key_remove`:
   ```python
   def chroma_key_remove(
       image: np.ndarray,
       color_to_remove: tuple,  # 要去除的颜色 (R,G,B)
       sensitivity: int = 50,   # 灵敏度 0-100
       smoothness: int = 30,    # 平滑度 0-100
       use_flash: bool = False  # 是否使用闪光灯
   ) -> tuple[np.ndarray, np.ndarray]:  # (前景RGBA, 遮罩)
   ```
   - HSV颜色空间转换
   - 基于目标颜色的阈值范围计算
   - 边缘平滑处理(高斯模糊 + 形态学操作)
   - 溢出抑制(despill)去除绿色反射
   - 针对闪光灯模式调整阈值

2. 背景合成 `composite_background`:
   ```python
   def composite_background(
       foreground_rgba: np.ndarray,
       background: np.ndarray,
       overlay: Optional[np.ndarray] = None,  # 可选叠加层
       output_size: tuple = (1800, 1200)       # 输出尺寸
   ) -> np.ndarray:
   ```
   - 前景缩放到输出尺寸
   - 背景裁剪/填充适应
   - 叠加层合成(在人物之后/之前)
   - 最终颜色校正

### 5.2 后端: AI人像分割
**新建文件:** `backend/app/services/background_removal_service.py`

1. AI背景移除 `remove_background_ai`:
   ```python
   def remove_background_ai(
       image: np.ndarray,
       model: Literal["mediapipe", "rembg", "u2net"] = "mediapipe"
   ) -> tuple[np.ndarray, np.ndarray]:  # (前景RGBA, 遮罩)
   ```

   实现方案:
   - **方案A: MediaPipe Selfie Segmentation (推荐)**
     - `pip install mediapipe`
     - 速度快(CPU实时)，效果可接受
     - 适用于人像场景
   
   - **方案B: rembg**
     - `pip install rembg`
     - 基于U²-Net深度学习模型
     - 效果优秀但速度较慢
   
   - **方案C: 云端API**
     - remove.bg API
     - 效果最好但需付费+网络

2. 背景评分 `score_background_complexity`:
   ```python
   def score_background_complexity(image: np.ndarray) -> float:
       # 评估背景是否为简单纯色背景
       # 返回 0(复杂) → 1(简单纯色)
       # 用于自动选择色度键控 vs AI分割
   ```

### 5.3 后端: 绿幕设置管理
**新建文件:** `backend/app/schemas/green_screen.py`

```python
class GreenScreenSettings(BaseModel):
    enabled: bool = False
    mode: Literal["chroma_key", "ai_removal", "auto"] = "auto"
    color_to_remove: str = "#00FF00"
    sensitivity: int = 50
    smoothness: int = 30
    use_flash: bool = False
    background_mode: Literal["rotate", "manual"] = "rotate"
    backgrounds: List[GreenScreenBackground] = []
    output_size: str = "template"  # "template" | "1800x1200" | "max"

class GreenScreenBackground(BaseModel):
    id: UUID
    name: str
    background_url: str       # 背景图片URL
    overlay_url: Optional[str] # 可选叠加层(透明PNG)
    order: int                 # 轮换顺序
```

### 5.4 后端: 绿幕API
**新建文件:** `backend/app/api/v1/green_screen.py`

```
POST   /api/v1/green-screen/preview        → 上传照片+设置 → 返回处理后预览
POST   /api/v1/green-screen/process        → 批量处理照片应用绿幕
GET    /api/v1/green-screen/settings/{event_id} → 获取事件绿幕设置
PUT    /api/v1/green-screen/settings/{event_id} → 更新事件绿幕设置
POST   /api/v1/green-screen/backgrounds    → 上传背景图像
DELETE /api/v1/green-screen/backgrounds/{id} → 删除背景
GET    /api/v1/green-screen/test-photo     → 拍摄测试照片并返回分析结果
```

### 5.5 前端: 绿幕设置页面
**新建文件:** `frontend/src/app/screens/GreenScreenScreen.tsx`

1. 三栏布局(参考BeautyScreen):
   - **左侧**: 模式选择(色度键控/AI分割/自动)
   - **中间**: 实时预览(原图 → 处理后)
   - **右侧**: 参数调节 + 背景管理

2. 功能组件:
   - 色度键控模式: 颜色选择器(吸管)、灵敏度滑块、平滑度滑块、闪光灯开关
   - AI分割模式: 模型选择、质量说明
   - 背景管理: 添加/删除背景、拖拽排序、预览缩略图
   - 测试照片: "拍摄测试照片"按钮 + 结果显示
   - 输出尺寸: 自动(模板)/1800x1200/最大

3. 背景选择模式:
   - 自动轮换: 每张照片循环切换
   - 手动选择: 来宾点击选择背景

### 5.6 前端: 拍摄屏幕集成绿幕
**修改文件:** `frontend/src/app/screens/CameraScreen.tsx`

1. 添加绿幕实时预览开关:
   - 在右侧面板添加"绿幕"开关
   - 开启后实时显示背景替换效果
   - 倒计时期间可显示/隐藏预览

2. 背景选择器(来宾可见):
   - 在当前相机预览下方显示背景缩略图
   - 点击切换背景

## 验收标准
1. 绿色背景前拍摄的照片能被正确抠图(色度键控)
2. 抠图边缘无明显的绿色溢出(spill)
3. 自动模式能根据背景复杂度选择色度键控或AI分割
4. AI分割能在CPU上3秒内完成一张照片的背景移除
5. 背景能按配置自动轮换
6. 叠加层(logo/装饰)能正确合成在人物之后或之前
7. 实时预览功能延迟<500ms
8. 测试照片能分析并给出参数调整建议

## 技术选型建议
- 色度键控: `opencv-python-headless` + `numpy`
- AI分割: `mediapipe` (轻量快速，CPU友好)
- 备选AI: `rembg` (更准确但更慢)
