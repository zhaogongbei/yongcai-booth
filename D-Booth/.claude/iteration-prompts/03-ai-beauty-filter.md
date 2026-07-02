# AI美颜真实集成 - 迭代提示词

## 目标
将当前纯CSS滤镜模拟的"AI美颜"替换为基于计算机视觉SDK的真实AI美颜处理，实现人脸关键点检测、智能磨皮、美白、瘦脸、大眼等真实图像处理效果。

## 当前状态
- `BeautyScreen.tsx` 使用CSS `brightness/contrast/saturate/blur` 滤镜模拟美颜
- 9项美颜参数(磨皮/瘦脸/大眼/眼神光/美白/祛痘/祛法令纹/牙齿美白/唇色)仅影响CSS视觉效果
- 这些CSS滤镜不支持真正的:
  - 人脸检测与关键点定位
  - GPU加速的图像处理
  - 皮肤纹理保留的智能磨皮
  - 面部几何变形(瘦脸/大眼)
  - 牙齿/嘴唇区域精准处理

## 需要实现的功能

### 3.1 后端: AI美颜处理服务
**新建文件:** `backend/app/services/beauty_service.py`

1. `BeautyProcessor` 类:
   ```
   process_image(
       image_bytes: bytes,
       params: BeautyParams  # 9项参数的TypedDict
   ) -> bytes  # 返回处理后的JPEG/PNG字节
   ```

2. `BeautyParams` Schema:
   ```python
   class BeautyParams(BaseModel):
       smooth: int = 50        # 磨皮 0-100
       thin_face: int = 30     # 瘦脸 0-100
       big_eye: int = 20       # 大眼 0-100
       eye_light: int = 10     # 眼神光 0-100
       whiten: int = 40        # 美白 0-100
       acne_remove: int = 30   # 祛痘 0-100
       nasolabial: int = 20    # 祛法令纹 0-100
       teeth_whiten: int = 20  # 牙齿美白 0-100
       lip_color: int = 15     # 唇色增强 0-100
   ```

3. 实现方案(按优先级):

   **方案A: 基于OpenCV + Dlib(推荐优先实现)**
   - 人脸检测: OpenCV Haar Cascade 或 Dlib HOG
   - 68点/81点人脸关键点: Dlib shape_predictor
   - 磨皮: 双边滤波(bilateralFilter) + 细节增强
   - 美白: 查找表(LUT)色阶映射 + 亮度调整
   - 瘦脸: 基于关键点的局部缩放变形(Interactive Image Warping / Moving Least Squares)
   - 大眼: 眼部关键点区域局部缩放
   - 祛痘: 斑点检测 + 中值滤波修复
   - 美白牙齿: 口腔区域检测 + 饱和度降低 + 亮度提升
   - 唇色: 唇部区域检测 + 颜色映射

   **方案B: 腾讯优图/旷视Face++ API**
   - 调用云API进行美颜处理
   - 优点: 效果好、免部署
   - 缺点: 需要付费、依赖网络

   **方案C: ncnn + 自训练模型**
   - 使用开源美颜模型(LookBook等)
   - ncnn推理(CPU亦可，GPU加速)
   - 优点: 离线可用、效果好
   - 缺点: 模型部署复杂

4. 创建 Celery 异步任务:
   ```python
   # backend/app/tasks/beauty_tasks.py
   @celery_app.task
   def apply_beauty_filter(photo_id: UUID, params: dict):
       # 下载原图 → 美颜处理 → 上传处理后图片 → 更新Photo记录
   ```

### 3.2 后端: 美颜API端点
**新建文件:** `backend/app/api/v1/beauty.py`

```
POST   /api/v1/beauty/preview     → 上传照片 + 美颜参数 → 返回处理后照片URL
POST   /api/v1/beauty/apply       → 对已有Photo应用美颜 → 创建派生Photo
GET    /api/v1/beauty/presets     → 获取预设美颜参数组合
POST   /api/v1/beauty/detect-face → 检测照片中的人脸 → 返回人脸框+关键点
```

### 3.3 前端: 美颜屏幕重构
**修改文件:** `frontend/src/app/screens/BeautyScreen.tsx`

1. 替换CSS滤镜为真实美颜:
   - 移除 `cssFilter` 的 useMemo 计算
   - 每次参数变化时调用 `POST /api/v1/beauty/preview`
   - 显示返回的处理后图片
   - 使用debounce(300ms)防止频繁请求

2. 添加人脸关键点可视化:
   - 调用 `GET /api/v1/beauty/detect-face`
   - 在原图上叠加关键点和网格
   - 可选显示/隐藏

3. 增强对比模式:
   - 左侧: 原图(保持原始Blob URL)
   - 右侧: AI处理后图片(从后端获取)
   - 分割线拖动(替换当前固定50%分割)

4. 添加美颜前后缩略图对比:
   - 在预设列表下方显示 "处理前 → 处理后" 对比条

5. 处理中状态:
   - 美颜处理需要100ms-500ms
   - 显示加载骨架屏/进度指示器
   - 取消上一次未完成请求(AbortController)

### 3.4 前端: 美颜预设系统增强
**修改文件:** `frontend/src/app/constants/index.ts`

1. 预设改为包含完整参数:
   ```typescript
   interface BeautyPreset {
     name: string;
     params: BeautyParams;  // 包含所有9项参数
     thumbnail: string;     // 处理后的示例图
     avatar: string;        // 预设缩略图
   }
   ```

2. 预设一键对比:
   - 点击预设后显示处理效果
   - 前后图片并排展示
   - 确认后应用

### 3.5 前端: SliderControl 组件增强
**修改文件:** `frontend/src/app/components/SliderControl.tsx`

1. 添加数值输入框(可选精确数值)
2. 添加"重置此项"按钮

### 3.6 配置和后端集成
**修改文件:** `backend/app/core/config.py`

添加美颜配置项:
```python
BEAUTY_ENGINE: Literal["opencv", "tencent_cloud", "facepp", "ncnn"] = "opencv"
BEAUTY_GPU_ENABLED: bool = False
BEAUTY_MAX_IMAGE_PIXELS: int = 12_000_000  # 12MP
```

## 验收标准
1. 上传照片后，能检测到人脸并显示人脸框和关键点
2. 调整磨皮参数(0→100)，照片皮肤纹理有明显变化，边缘保持清晰
3. 调整美白参数(0→100)，肤色有明显提亮但不过曝
4. 调整瘦脸参数(0→100)，脸型有明显收缩但不变形
5. 调整大眼参数(0→100)，眼睛有明显放大但保持自然
6. 所有9项参数可同时调节并实时预览效果(处理耗时<500ms)
7. 预设能一键应用全部9项参数
8. 对比模式能清晰展示处理前后差异
9. 处理后的照片可正常保存、打印、分享
10. 无可检测人脸时优雅降级(仅应用全局滤镜)

## 技术选型建议
- 优先: `opencv-python-headless` + `dlib` + `numpy`
- 人脸检测: OpenCV Haar Cascade (快速) → Dlib HOG (准确)
- 关键点: Dlib 68/81-point shape predictor (需下载 shape_predictor_68_face_landmarks.dat)
- 备选: `mediapipe` (Google，轻量级，效果好)
- GPU加速(可选): `opencv-python-headless` + CUDA
