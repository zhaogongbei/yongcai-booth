# 水印与版权保护 - 迭代提示词

## 目标
实现照片水印叠加、打印锐化、LUT自定义滤镜(.cube文件)三大图片后期处理功能。

## 当前状态
- Photo模型有watermark相关字段但无业务逻辑
- 无打印锐化
- 无LUT滤镜支持

## 需要实现的功能

### 13.1 水印系统

#### 后端: 水印服务
**新建文件:** `backend/app/services/watermark_service.py`

1. 水印应用:
   ```python
   async def apply_watermark(
       image_bytes: bytes,
       watermark_bytes: bytes,  # 透明PNG水印
       position: WatermarkPosition,  # 位置
       opacity: float = 0.5,     # 透明度
       scale: float = 1.0,       # 缩放
       tile: bool = False        # 是否平铺
   ) -> bytes:
   ```

2. 水印位置枚举:
   - top_left / top_center / top_right
   - center
   - bottom_left / bottom_center / bottom_right
   - tile (全图平铺)

3. 水印检测:
   ```python
   async def detect_watermark_size(image_bytes: bytes) -> tuple:
       """检测水印文件的推荐尺寸"""
   ```

#### 水印API:
```
POST   /api/v1/watermark/upload        → 上传水印PNG
POST   /api/v1/watermark/apply/{photo_id} → 对照片应用水印
GET    /api/v1/watermark/preview       → 水印效果预览
PUT    /api/v1/watermark/settings/{event_id} → 更新水印设置
```

### 13.2 打印锐化

#### 后端: 锐化服务
**新建文件:** `backend/app/services/sharpen_service.py`

1. 锐化配置:
   ```python
   class SharpenProfile(str, Enum):
       NONE = "none"
       LOW = "low"     # 轻度锐化
       MEDIUM = "medium"
       HIGH = "high"   # 高度锐化(打印用)
   ```

2. 锐化算法:
   ```python
   async def apply_sharpen(
       image_bytes: bytes,
       profile: SharpenProfile,
       for_print: bool = True  # 打印锐化比屏幕锐化更强
   ) -> bytes:
       # 使用Pillow的ImageFilter.UnsharpMask
       # 或OpenCV的拉普拉斯锐化
   ```

3. 打印前自动锐化:
   - 在模板渲染流程中，最终输出前应用锐化
   - 根据纸张尺寸和分辨率调整锐化强度

### 13.3 LUT自定义滤镜(.cube文件)

#### 后端: LUT滤镜服务
**新建文件:** `backend/app/services/lut_service.py`

1. LUT解析:
   ```python
   async def parse_cube_file(cube_bytes: bytes) -> np.ndarray:
       """解析.cube 3D LUT文件为numpy数组"""
       # .cube格式: 标准3D查找表
       # LUT_3D_SIZE 32 (32x32x32 = 32768条记录)
       # 使用np.meshgrid进行三线性插值
   ```

2. LUT应用:
   ```python
   async def apply_lut(
       image_bytes: bytes,
       lut_data: np.ndarray,
       intensity: float = 1.0  # 强度 0-1
   ) -> bytes:
       """将3D LUT应用到图像"""
       # 将RGB值映射到LUT空间
       # 三线性插值取色
   ```

3. LUT管理:
   ```python
   class LUT(BaseModel):
       id: UUID
       name: str
       category: str          # 电影感/复古/清新/黑白/自定义
       file_url: str          # .cube文件存储URL
       preview_url: str       # 效果预览图
       is_public: bool
   ```

#### LUT API:
```
GET    /api/v1/luts                    → 获取LUT列表
POST   /api/v1/luts                    → 上传.cube文件
DELETE /api/v1/luts/{id}              → 删除LUT
POST   /api/v1/luts/{id}/preview      → LUT效果预览(使用演示照片)
POST   /api/v1/luts/apply/{photo_id}  → 对照片应用LUT
```

### 13.4 前端: 滤镜系统扩展

#### 修改 BeautyScreen / CameraScreen
1. 添加LUT滤镜选择器:
   - 与现有预设滤镜并列
   - 显示LUT效果预览缩略图
   - 在线获取LUT列表
   - 自定义LUT上传入口

2. 水印预览:
   - 在美颜/模板编辑中显示水印位置
   - 水印透明度调节

## 验收标准
1. 透明PNG水印正确叠加到照片指定位置
2. 平铺水印模式覆盖整个照片
3. 打印输出比屏幕预览清晰度明显提升
4. .cube LUT文件能正确解析和应用
5. LUT滤镜数量不限，效果与原LUT预期一致

## 技术选型建议
- LUT解析: 纯Python numpy实现
- 三线性插值: `scipy.ndimage.map_coordinates` 或手动实现
- 锐化: Pillow `ImageFilter.UnsharpMask`
