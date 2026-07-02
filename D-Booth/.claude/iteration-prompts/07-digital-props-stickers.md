# 数字道具与贴纸系统 - 迭代提示词

## 目标
实现类似SNOW/B612的数字道具和贴纸功能，支持透明PNG道具拖拽放置、缩放旋转、多层叠加，以及道具分类管理。

## 当前状态
- `BeautyScreen.tsx` 有"贴纸"工具按钮但无实际功能
- 无任何道具管理后端
- 无道具库

## 需要实现的功能

### 7.1 后端: 道具管理系统
**新建文件:** `backend/app/services/props_service.py`

1. 道具模型:
   ```python
   class DigitalProp(Base):
       id: UUID
       team_id: UUID
       name: str
       category: str        # 节日/婚礼/生日/动物/眼镜/帽子/胡须/自定义
       image_url: str       # 透明PNG存储URL
       thumbnail_url: str
       is_public: bool      # 公共道具(所有团队可见)
       is_default: bool     # 内置默认道具
       tags: List[str]
   ```

2. 道具CRUD:
   - 上传道具(透明PNG)
   - 道具分类管理
   - 公共道具库浏览
   - 团队私有道具

### 7.2 后端: 道具API
**新建文件:** `backend/app/api/v1/props.py`

```
GET    /api/v1/props                    → 获取道具列表(分页/分类筛选)
POST   /api/v1/props                    → 上传自定义道具
DELETE /api/v1/props/{id}              → 删除道具
GET    /api/v1/props/categories         → 获取道具分类列表
GET    /api/v1/props/defaults           → 获取内置默认道具
```

### 7.3 后端: 道具合成服务
**修改文件:** `backend/app/services/template_render_service.py` (或新建 props_render_service.py)

```python
async def apply_props(
    image_bytes: bytes,
    props: List[AppliedProp]  # 道具 + 位置/缩放/旋转
) -> bytes:
    """
    将道具叠加到照片上
    - 利用透明PNG的alpha通道
    - 支持缩放/旋转/翻转
    - 多层合成(z-index排序)
    """
```

其中:
```python
class AppliedProp(BaseModel):
    prop_id: UUID
    x: float       # 位置(相对于图像宽度的比例 0-1)
    y: float
    scale: float   # 缩放 0.1-3.0
    rotation: float # 旋转 0-360
    flip_h: bool   # 水平翻转
    flip_v: bool   # 垂直翻转
    opacity: float  # 透明度 0-1
```

### 7.4 前端: 贴纸选择器(在美颜页面)
**修改文件:** `frontend/src/app/screens/BeautyScreen.tsx`

1. 当 `activeTool === "贴纸"` 时:
   - 左侧面板切换为贴纸分类列表
   - 显示贴纸缩略图网格(每行3个)
   - 分类切换(节日/婚礼/生日/动物/眼镜/帽子等)

2. 贴纸操作:
   - 点击贴纸 → 添加到照片中央
   - 添加到照片上的贴纸显示为一个可拖拽元素
   - 选中贴纸后显示控制手柄(缩放/旋转/删除)
   - 支持多层贴纸叠加
   - 已添加的贴纸列表显示在右侧面板

### 7.5 前端: 新建立贴纸编辑组件
**新建文件:** `frontend/src/app/components/StickerOverlay.tsx`

1. 贴纸拖拽功能:
   ```tsx
   interface StickerOverlayProps {
     imageUrl: string;
     stickers: AppliedSticker[];
     onStickersChange: (stickers: AppliedSticker[]) => void;
     selectedStickerId: string | null;
     onSelectSticker: (id: string | null) => void;
   }
   ```

2. 使用 `react-konva` Stage/Layer/Image:
   - 照片作为底层
   - 每个贴纸作为独立的Konva.Image
   - Transformer节点处理缩放/旋转
   - 双击贴纸删除

3. 或使用纯DOM方案:
   - 绝对定位的 `<img>` 元素
   - CSS `transform` 处理缩放/旋转
   - `onPointerDown/Move/Up` 处理拖拽
   - 更轻量，但缩放体验不如Konva

### 7.6 前端: 道具管理页面(管理员)
**新建文件:** `frontend/src/app/screens/PropsManagerScreen.tsx`

1. 道具上传:
   - 拖放透明PNG文件
   - 自动生成缩略图
   - 设置名称/分类/标签

2. 道具库浏览:
   - 瀑布流网格
   - 分类筛选
   - 搜索
   - 删除确认

### 7.7 前端: 贴纸状态集成到CaptureFlow
**修改文件:** `frontend/src/app/stores/useCaptureFlow.tsx`

在 `CapturedPhoto` 接口添加:
```typescript
interface CapturedPhoto {
  // ...existing fields
  appliedProps?: AppliedProp[];  // 已应用的道具
  propsApplied: boolean;          // 是否已应用道具
}
```

### 7.8 默认道具资源
需要在 `frontend/public/images/props/` 目录下准备默认道具包:
- 眼镜类: 墨镜、圆框眼镜、心形眼镜
- 帽子类: 皇冠、圣诞帽、棒球帽
- 胡须类: 络腮胡、八字胡
- 节日类: 圣诞鹿角、万圣节面具、新年装饰
- 表情类: 爱心、星星、气泡
- 约20-30个基础透明PNG道具

## 验收标准
1. 贴纸选择器展示所有可用贴纸的分类缩略图
2. 点击贴纸后正确添加到照片上
3. 贴纸可拖拽移动、双指缩放、旋转
4. 支持多层贴纸叠加(至少5层)
5. 贴纸可单独删除
6. 已贴贴纸的照片可正常保存、打印(后端合成正确)
7. 管理员可上传自定义透明PNG道具
8. 内置至少20个默认道具

## 技术选型建议
- 贴纸交互: `react-konva` (如果已经在模板编辑器中使用)
- 备选: 纯DOM + CSS transforms (更轻量)
- 道具存储: Cloudflare R2 (复用现有storage_service)
- 道具合成: Pillow alpha compositing
