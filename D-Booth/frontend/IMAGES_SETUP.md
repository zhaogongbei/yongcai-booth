# AI Booth 图片素材系统总结

## ✅ 已完成的工作

我已经为 AI Booth 项目创建了一个完整的图片素材管理系统：

### 1. 📁 目录结构
```
public/images/
├── scenes/              # 8张活动场景图片
├── avatars/            # 8张用户头像
├── backgrounds/        # 5张背景图片
├── products/           # 6张产品展示图
├── README.md           # 使用文档
└── IMAGE_ASSETS_GUIDE.md  # 详细需求指南
```

### 2. 🛠️ 核心工具

#### `src/utils/imagePlaceholder.ts`
完整的图片管理工具库，提供：
- 27张图片的配置清单
- 占位符自动生成
- 开发/生产环境自动切换
- 图片预加载功能
- React Hook 支持

#### `scripts/download-images.mjs`
自动化图片下载脚本：
- 从 Unsplash API 批量下载
- 自动裁剪到指定尺寸
- 生成版权归属信息
- 遵守 API 速率限制

### 3. 📖 文档

#### `public/images/README.md`
快速开始指南，包含：
- 三种图片获取方案
- 完整使用示例
- 开发与生产环境说明

#### `public/images/IMAGE_ASSETS_GUIDE.md`
详细的图片需求文档：
- 27张图片的详细规格
- 推荐搜索关键词
- 图库资源链接
- 图片处理建议

---

## 🚀 使用流程

### 开发阶段（立即可用）

```bash
# 1. 无需下载，直接开始开发
npm install
npm run dev

# 2. 在代码中使用图片
import { getImageUrl } from '@/utils/imagePlaceholder';

<img src={getImageUrl('wedding-couple-booth')} alt="Wedding" />
```

开发时会自动显示占位符图片，样式统一，尺寸正确。

### 生产部署（下载真实图片）

**方案 A: 自动下载（推荐）**
```bash
# 1. 获取 Unsplash API Key
# 访问 https://unsplash.com/developers

# 2. 设置环境变量
export UNSPLASH_ACCESS_KEY=your_key

# 3. 运行下载脚本
node scripts/download-images.mjs

# 4. 构建生产版本
npm run build
```

**方案 B: 手动下载**
```bash
# 参考 IMAGE_ASSETS_GUIDE.md
# 从 Unsplash/Pexels 手动下载
# 按照文档重命名并放入对应目录
```

---

## 📋 图片清单（27张）

### 场景图片 - 8张 (1920x1080)
1. ✅ wedding-couple-booth.png - 婚礼新人
2. ✅ wedding-guests-fun.png - 婚礼宾客
3. ✅ corporate-event-group.png - 企业活动
4. ✅ conference-networking.png - 会议交流
5. ✅ birthday-party-fun.png - 生日派对
6. ✅ kids-birthday-booth.png - 儿童生日
7. ✅ brand-popup-mall.png - 品牌快闪
8. ✅ festival-outdoor-booth.png - 音乐节

### 产品图片 - 6张 (1600x900)
9. ✅ ipad-booth-setup.png - iPad照相亭
10. ✅ camera-equipment.png - 专业相机
11. ✅ printer-dnp-ds620.png - 打印机
12. ✅ photo-prints-showcase.png - 照片成品
13. ✅ polaroid-style-prints.png - 宝丽来
14. ✅ photo-album-collection.png - 相册

### 头像图片 - 8张 (400x400)
15. ✅ avatar-woman-asian-01.png
16. ✅ avatar-man-caucasian-01.png
17. ✅ avatar-woman-african-01.png
18. ✅ avatar-man-asian-01.png
19. ✅ avatar-woman-latina-01.png
20. ✅ avatar-man-african-01.png
21. ✅ avatar-elderly-couple.png
22. ✅ avatar-teen-girl.png

### 背景图片 - 5张
23. ✅ attract-screen-01.png (2560x1440) - 派对
24. ✅ attract-screen-elegant.png (2560x1440) - 优雅
25. ✅ attract-screen-corporate.png (2560x1440) - 企业
26. ✅ dashboard-bg-gradient.png (1920x1080) - 渐变
27. ✅ stats-bg-pattern.png (1920x1080) - 图案

---

## 💡 核心特性

### 1. 智能占位符系统
- 开发时自动使用占位符（placehold.co）
- 品牌色 Terracotta (#C4612F)
- 自动匹配正确尺寸
- 无需真实图片即可开发

### 2. 自动环境切换
```typescript
// 开发环境：自动占位符
// 生产环境：本地图片 → 占位符降级
const imageUrl = getImageUrl('wedding-couple-booth');
```

### 3. 类型安全
```typescript
type ImageCategory = 'scenes' | 'avatars' | 'backgrounds' | 'products';

interface ImageConfig {
  width: number;
  height: number;
  text: string;
  category: ImageCategory;
  filename: string;
}
```

### 4. 批量操作
```typescript
// 获取所有场景图片
const allScenes = getImagesByCategory('scenes');

// 预加载关键图片
await preloadImages([
  'wedding-couple-booth',
  'corporate-event-group'
]);
```

---

## 🎯 推荐工作流

### 前端开发者
```bash
# 直接开始开发，使用占位符
npm run dev

# 在组件中使用图片
import { getImageUrl } from '@/utils/imagePlaceholder';
```

### UI/UX 设计师
```bash
# 下载真实图片查看效果
node scripts/download-images.mjs

# 或手动下载并替换
# 参考 IMAGE_ASSETS_GUIDE.md
```

### DevOps/部署
```bash
# 构建前下载所有图片
node scripts/download-images.mjs
npm run build

# 或在 CI/CD 中自动执行
```

---

## 📦 文件清单

### 核心文件
- ✅ `src/utils/imagePlaceholder.ts` - 图片管理工具（304行）
- ✅ `scripts/download-images.mjs` - 自动下载脚本（284行）
- ✅ `public/images/README.md` - 快速使用指南
- ✅ `public/images/IMAGE_ASSETS_GUIDE.md` - 详细需求文档

### 目录结构
- ✅ `public/images/scenes/` - 场景图片目录
- ✅ `public/images/avatars/` - 头像目录
- ✅ `public/images/backgrounds/` - 背景目录
- ✅ `public/images/products/` - 产品图片目录

---

## 🔧 技术细节

### 占位符服务
- **服务**: placehold.co
- **格式**: `https://placehold.co/{width}x{height}/{bgColor}/{textColor}?text={text}`
- **品牌色**: #C4612F (Terracotta)

### Unsplash API
- **文档**: https://unsplash.com/documentation
- **速率限制**: 50 requests/hour (免费版)
- **图片质量**: 原始高清，自动裁剪

### 图片格式建议
- **开发**: JPEG/PNG 占位符
- **生产**: JPEG 85% 质量
- **优化**: 可转换为 WebP 格式

---

## 🚨 注意事项

1. **版权许可**: Unsplash 图片免费商用，需保留归属
2. **API 限制**: 免费版 50次/小时，足够下载27张
3. **文件大小**: 场景图约2-3MB，注意性能优化
4. **Git 管理**: 建议添加 `public/images/*.jpg` 到 `.gitignore`
5. **备份**: 下载后备份图片和 ATTRIBUTIONS.json

---

## 🎉 立即开始

```bash
# 1. 立即开发（使用占位符）
npm run dev

# 2. 需要真实图片时
export UNSPLASH_ACCESS_KEY=your_key
node scripts/download-images.mjs

# 3. 生产部署
npm run build
```

---

## 📞 支持

如有问题，请参考：
- 快速指南: `public/images/README.md`
- 详细文档: `public/images/IMAGE_ASSETS_GUIDE.md`
- 代码示例: `src/utils/imagePlaceholder.ts`

---

**创建时间**: 2026-06-22  
**状态**: ✅ 完成，可直接使用  
**图片数量**: 27张（配置完成，可按需下载）
