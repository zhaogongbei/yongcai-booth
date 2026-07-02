# 模板编辑器完善 - 迭代提示词

## 目标
将当前仅UI框架的模板编辑器升级为功能完整、支持拖拽编辑的专业模板设计工具，实现13种预设布局、图层系统、动态数据元素和模板导入/导出。

## 当前状态
- `TemplateEditorScreen.tsx` 有三栏布局(元素库+画布+属性面板)
- 画布内容为硬编码的静态图片占位，无实际编辑功能
- 图层列表仅为静态展示，无实际操作
- 属性面板仅为静态展示，无双向绑定
- 工具栏按钮(移动/复制/图层/对齐/文字/调色)无实际功能
- 后端 `template_service.py` 仅基础CRUD，无渲染/验证逻辑

## 需要实现的功能

### 4.1 前端: 模板数据结构定义
**新建文件:** `frontend/src/app/types/template.ts`

```typescript
interface TemplateElement {
  id: string;
  type: 'photo' | 'text' | 'shape' | 'image' | 'qr_code' | 'date' | 'datetime' | 'filename' | 'survey_answer' | 'session_number' | 'signature';
  x: number;     // 位置(像素)
  y: number;
  width: number;  // 尺寸(像素)
  height: number;
  rotation: number; // 旋转角度 0-360
  opacity: number;  // 透明度 0-1
  zIndex: number;   // 图层顺序
  locked: boolean;  // 是否锁定
  visible: boolean; // 是否可见
  // 类型特有属性
  props: PhotoElementProps | TextElementProps | ShapeElementProps | ImageElementProps;
}

interface TemplateLayout {
  id: string;
  name: string;
  paperSize: { width: number; height: number }; // 毫米
  resolution: number;   // DPI (300)
  orientation: 'portrait' | 'landscape';
  background: { type: 'color' | 'gradient' | 'image'; value: string };
  elements: TemplateElement[];
}
```

### 4.2 前端: 画布拖拽编辑系统
**修改文件:** `frontend/src/app/screens/TemplateEditorScreen.tsx`

1. 集成 `@dnd-kit/core` + `@dnd-kit/sortable`:
   - 元素拖拽移动(位置更新)
   - 元素缩放(8个控制手柄)
   - 元素旋转(旋转手柄)
   - 多选(Shift+点击 / 框选)
   - 键盘方向键微调(1px / Shift+10px)

2. 基于 `react-konva` 或纯Canvas/SVG实现:
   - 实际画布渲染(非静态图片)
   - 元素选中高亮(蓝色边框+8点控制手柄)
   - 对齐辅助线(磁吸到其他元素/画布边缘/中心)
   - 网格背景
   - 出血线显示

3. 画布操作:
   - 缩放: 鼠标滚轮 / 按钮 25%/50%/75%/100%/150%/200%
   - 平移: 空格+拖拽 / 鼠标中键
   - 撤销/重做: Ctrl+Z / Ctrl+Y (命令模式)
   - 适应画布: 双击缩放按钮

### 4.3 前端: 13种预设布局实现
**新建文件:** `frontend/src/app/constants/templatePresets.ts`

1. 每种预设的完整元素布局数据:
   - 四姿单条水平 (Four poses, single strip horizontal)
   - 四姿双条垂直 (Four poses, double strip vertical)
   - 四姿单条垂直 (Four poses, single strip vertical)
   - 一大三小 (One Large, Three small horizontal)
   - 一姿双条水平/垂直
   - 一姿单条水平/垂直
   - 三姿双条垂直
   - 两姿双条水平
   - 经典2x6照片条

2. 预设选择对话框:
   - 布局缩略图预览
   - 点击一键应用
   - 可基于预设继续编辑

### 4.4 前端: 图层系统完善
**修改面板右侧图层列表:**

1. 图层操作:
   - 点击选中图层 → 画布同步高亮
   - 拖拽排序(zIndex)
   - 锁定/解锁(Lock)
   - 复制图层(Duplicate)
   - 删除图层(Delete) → 确认对话框
   - 显示/隐藏(眼睛图标)
   - 双击重命名图层

2. 对齐与分布:
   - 多选图层后可用
   - 水平: 左对齐/居中/右对齐/水平分布
   - 垂直: 顶部对齐/居中/底部对齐/垂直分布
   - 匹配宽度/高度

### 4.5 前端: 属性面板动态绑定
**修改右侧属性面板:**

1. 根据选中元素类型显示不同属性:
   - **照片框**: 照片编号(1/2/3/4)、裁剪模式(填充/适应/拉伸)、圆角
   - **文本**: 文本内容、字体、大小、粗细、颜色、对齐、行高
   - **形状**: 填充色、描边色、描边宽度、圆角、形状类型
   - **日期/时间**: 格式选择(YYYY-MM-DD / MM/DD/YYYY / DD.MM.YYYY 等)
   - **二维码**: 链接URL、尺寸
   - **通用**: X/Y/W/H/Rotation/Opacity

2. 属性修改实时同步到画布:
   - 双向数据绑定
   - 支持撤销/重做

### 4.6 前端: 元素库完善
**修改左侧元素库面板:**

1. 可添加元素类型:
   - 照片占位符(拖到画布创建照片框)
   - 文本(创建文本元素)
   - 形状(线条/矩形/椭圆/星形)
   - 动态数据(日期/时间/活动名/会话号)
   - 二维码
   - 背景(纯色/渐变/图片)

2. 拖拽从元素库到画布:
   - 使用 @dnd-kit 的跨容器拖拽
   - 创建新元素在放置位置

### 4.7 后端: 模板验证与渲染
**修改文件:** `backend/app/services/template_service.py`

1. 模板JSON结构验证:
   ```python
   def validate_template(template_data: dict) -> bool:
       # 验证尺寸在纸张范围内
       # 验证照片占位符数量匹配
       # 验证必填元素存在
       # 验证JSON schema
   ```

2. 模板预览图生成:
   ```python
   async def generate_preview(template_id: UUID, sample_photos: List[Bytes]) -> bytes:
       # 使用TemplateRenderService渲染预览
   ```

### 4.8 后端: 模板导入/导出
**修改文件:** `backend/app/api/v1/templates.py`

```
POST   /api/v1/templates/import     → 上传.template文件 → 解析并创建
GET    /api/v1/templates/{id}/export → 导出为.template文件(JSON)
POST   /api/v1/templates/{id}/preview → 使用演示照片生成预览图
POST   /api/v1/templates/{id}/duplicate → 复制模板
```

## 验收标准
1. 元素可从左侧元素库拖到画布上
2. 元素在画布上可拖动、缩放、旋转
3. 多选元素后可使用对齐/分布工具
4. 图层列表中可拖拽调整顺序，锁定/隐藏/复制/删除操作正常
5. 属性面板根据选中元素类型显示对应属性，修改后画布实时更新
6. 13种预设布局可一键应用，并基于预设继续编辑
7. 撤销/重做(Ctrl+Z/Y)支持所有编辑操作
8. 模板可导出为JSON文件并重新导入
9. 模板预览图正确体现所有图层合成效果
10. 编辑后保存 → 刷新 → 加载的模板与保存时刻一致

## 技术选型建议
- 画布渲染: `react-konva` (基于HTML5 Canvas，非DOM，性能好)
- 拖拽: `@dnd-kit/core` + `@dnd-kit/sortable`（已在项目中使用）
- 撤销/重做: 自定义 `useUndoRedo` hook (命令栈模式)
- 备选: `fabric.js` (更成熟的Canvas编辑库，但较重)
