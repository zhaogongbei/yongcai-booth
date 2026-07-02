# 图片素材管理系统

AI Booth 项目的图片资源管理方案，支持占位符开发和真实图片替换。

## 📁 目录结构

```
public/images/
├── scenes/              # 活动场景图片 (8张)
├── avatars/            # 用户头像 (8张)
├── backgrounds/        # 背景图片 (5张)
├── products/           # 产品展示 (6张)
├── IMAGE_ASSETS_GUIDE.md   # 详细的图片需求文档
└── ATTRIBUTIONS.json   # 图片版权归属信息
```

## 🚀 快速开始

### 方案 1: 使用占位符（开发阶段）

在开发时自动使用占位符图片，无需下载真实图片：

```typescript
import { getImageUrl } from '@/utils/imagePlaceholder';

function MyComponent() {
  return (
    <img 
      src={getImageUrl('wedding-couple-booth')} 
      alt="Wedding Couple" 
    />
  );
}
```

### 方案 2: 自动下载真实图片（推荐）

使用 Unsplash API 自动下载高质量免费图片：

```bash
# 1. 获取 Unsplash Access Key
# 访问 https://unsplash.com/developers 注册应用

# 2. 设置环境变量
export UNSPLASH_ACCESS_KEY=your_access_key_here

# 3. 运行下载脚本
node scripts/download-images.mjs
```

下载完成后会自动：
- 下载 27 张高质量图片到对应目录
- 生成版权归属信息文件
- 自动裁剪到指定尺寸

### 方案 3: 手动下载图片

参考 `IMAGE_ASSETS_GUIDE.md` 文档：

1. 访问 [Unsplash](https://unsplash.com) 或 [Pexels](https://pexels.com)
2. 按照文档中的关键词搜索
3. 下载图片并重命名
4. 放入对应的类别目录

## 📸 图片清单

### 场景图片（Scenes）- 1920x1080
- ✅ `wedding-couple-booth.png` - 婚礼新人
- ✅ `wedding-guests-fun.png` - 婚礼宾客
- ✅ `corporate-event-group.png` - 企业活动
- ✅ `conference-networking.png` - 会议交流
- ✅ `birthday-party-fun.png` - 生日派对
- ✅ `kids-birthday-booth.png` - 儿童生日
- ✅ `brand-popup-mall.png` - 品牌快闪
- ✅ `festival-outdoor-booth.png` - 户外音乐节

### 产品图片（Products）- 1600x900
- ✅ `ipad-booth-setup.png` - iPad 照相亭
- ✅ `camera-equipment.png` - 专业相机
- ✅ `printer-dnp-ds620.png` - 打印机
- ✅ `photo-prints-showcase.png` - 照片成品
- ✅ `polaroid-style-prints.png` - 宝丽来风格
- ✅ `photo-album-collection.png` - 照片相册

### 头像图片（Avatars）- 400x400
- ✅ `avatar-woman-asian-01.png`
- ✅ `avatar-man-caucasian-01.png`
- ✅ `avatar-woman-african-01.png`
- ✅ `avatar-man-asian-01.png`
- ✅ `avatar-woman-latina-01.png`
- ✅ `avatar-man-african-01.png`
- ✅ `avatar-elderly-couple.png`
- ✅ `avatar-teen-girl.png`

### 背景图片（Backgrounds）
- ✅ `attract-screen-01.png` - 2560x1440 派对风格
- ✅ `attract-screen-elegant.png` - 2560x1440 优雅婚礼
- ✅ `attract-screen-corporate.png` - 2560x1440 企业风格
- ✅ `dashboard-bg-gradient.png` - 1920x1080 渐变背景
- ✅ `stats-bg-pattern.png` - 1920x1080 图案背景

## 💻 使用方法

### 基础用法

```typescript
import { getImageUrl, getImagesByCategory } from '@/utils/imagePlaceholder';

// 获取单张图片
const weddingImage = getImageUrl('wedding-couple-booth');

// 获取某个分类的所有图片
const allScenes = getImagesByCategory('scenes');

// 强制使用本地图片（不使用占位符）
const localImage = getImageUrl('wedding-couple-booth', false);
```

### React 组件示例

```tsx
import { getImageUrl } from '@/utils/imagePlaceholder';

export function EventCard() {
  return (
    <div className="card">
      <img 
        src={getImageUrl('wedding-couple-booth')}
        alt="Wedding Event"
        className="w-full h-64 object-cover rounded-lg"
      />
      <h3>婚礼活动</h3>
      <p>为您的特殊时刻留下美好回忆</p>
    </div>
  );
}
```

### 图片预加载

```typescript
import { preloadImages } from '@/utils/imagePlaceholder';

// 在应用启动时预加载关键图片
async function init() {
  await preloadImages([
    'wedding-couple-booth',
    'corporate-event-group',
    'birthday-party-fun'
  ]);
}
```

## 🎨 占位符系统

开发阶段使用 [placehold.co](https://placehold.co) 生成占位符：

- **背景色**: `#C4612F`（Terracotta 陶土色）
- **文字色**: `#FFFFFF`（白色）
- **自动尺寸**: 根据配置自动生成正确尺寸

示例：
```
https://placehold.co/1920x1080/C4612F/FFFFFF?text=Wedding+Couple
```

## 🔄 开发与生产切换

系统会自动根据环境切换图片来源：

**开发环境** (`npm run dev`)
- 自动使用占位符
- 无需下载真实图片
- 快速启动项目

**生产环境** (`npm run build`)
- 使用本地真实图片
- 如果图片不存在会显示占位符
- 建议在构建前下载所有图片

## 📝 版权归属

使用 Unsplash API 下载的图片会自动生成归属信息：

```json
{
  "key": "wedding-couple-booth",
  "photographer": "John Doe",
  "photographerUrl": "https://unsplash.com/@johndoe",
  "photoUrl": "https://unsplash.com/photos/abc123"
}
```

在应用的 About 或 Credits 页面展示这些信息。

## 🛠️ 工具脚本

### 下载脚本

```bash
# 下载所有图片
node scripts/download-images.mjs

# 只下载特定分类
# (需要修改脚本配置)
```

### 图片优化

```bash
# 使用 ImageMagick 批量优化
cd public/images/scenes
for img in *.jpg; do
  convert "$img" -quality 85 -strip "optimized_$img"
done

# 转换为 WebP 格式
for img in *.jpg; do
  cwebp -q 80 "$img" -o "${img%.jpg}.webp"
done
```

## 🔗 相关资源

- **详细文档**: `IMAGE_ASSETS_GUIDE.md`
- **工具代码**: `src/utils/imagePlaceholder.ts`
- **下载脚本**: `scripts/download-images.mjs`

## 📌 注意事项

1. **版权许可**: 确保所有图片都有商业使用许可
2. **图片尺寸**: 严格按照配置的尺寸下载，避免加载性能问题
3. **文件命名**: 使用小写字母和连字符，保持一致性
4. **归属信息**: 使用 Unsplash 图片时必须保留归属信息
5. **Git 忽略**: 可以将 `public/images/*` 添加到 `.gitignore`，避免图片进入版本控制

## 🤝 贡献

如果你有更好的图片资源或改进建议：

1. 按照规范添加到对应目录
2. 更新 `imagePlaceholder.ts` 配置
3. 更新本文档
4. 提交 Pull Request

---

**维护者**: AI Booth Team  
**更新时间**: 2026-06-22
