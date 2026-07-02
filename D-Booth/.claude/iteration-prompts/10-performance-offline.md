# 性能优化与离线能力 - 迭代提示词

## 目标
优化图片加载性能、实现Service Worker离线缓存、GPU加速图像处理、CDN分发优化，提升整体用户体验。

## 当前状态
- 前端使用 `loading="lazy"` 和 React.lazy 基础优化
- 无Service Worker
- 无CDN配置
- 照片直接加载原图无缩略图策略
- SQLAlchemy有连接池但无查询缓存

## 需要实现的功能

### 10.1 图片加载优化

#### 后端: 缩略图预生成服务
**修改文件:** `backend/app/services/photo_service.py`

1. 多尺寸缩略图生成:
   ```python
   THUMBNAIL_SIZES = {
       'micro': (48, 48),       # 极缩略图(列表快速预览)
       'thumb': (200, 200),     # 缩略图(网格列表)
       'medium': (600, 600),    # 中图(详情预览)
       'large': (1200, 1200),   # 大图(全屏预览)
   }
   ```

2. 上传时自动生成所有尺寸:
   ```python
   async def generate_thumbnails(image_bytes: bytes) -> dict:
       thumbnails = {}
       for name, size in THUMBNAIL_SIZES.items():
           thumbnails[name] = await resize_image(image_bytes, size)
       return thumbnails
   ```

3. 缩略图API:
   ```
   GET /api/v1/media/photo/{id}/thumbnail?size=micro|thumb|medium|large
   ```

#### 后端: WebP/AVIF转码
**修改文件:** `backend/app/services/photo_service.py`

1. 上传时自动转码为WebP:
   ```python
   async def transcode_to_webp(image_bytes: bytes, quality: int = 80) -> bytes:
       # 使用Pillow保存为WebP
   ```

2. 根据Accept头返回最佳格式:
   - `Accept: image/webp` → 返回WebP
   - `Accept: image/avif` → 返回AVIF
   - Fallback: JPEG

#### 前端: 渐进式图片组件
**新建文件:** `frontend/src/app/components/ProgressiveImage.tsx`

1. 模糊预览 → 高清加载:
   ```tsx
   function ProgressiveImage({ src, alt, className }) {
     // 1. 显示极缩略图(放大+模糊)作为占位
     // 2. 加载中缩略图
     // 3. 加载原图
     // 4. 平滑过渡
   }
   ```

2. 使用 Intersection Observer 懒加载:
   - 仅在元素进入视口时加载
   - 提前200px预加载

### 10.2 查询缓存优化

#### 后端: Redis缓存层
**新建文件:** `backend/app/core/cache.py`

1. 缓存装饰器:
   ```python
   @cache_result(ttl=300)  # 5分钟
   async def get_event_statistics(event_id: UUID) -> dict: ...
   ```

2. 缓存策略:
   - 事件统计: 5分钟TTL
   - 模板列表: 10分钟TTL
   - 打印机状态: 30秒TTL
   - 活动照片列表: 60秒TTL
   - 失效策略: 写操作后主动清除相关缓存

3. 缓存键命名规范:
   ```
   event:{event_id}:stats
   team:{team_id}:templates
   photo:{photo_id}:metadata
   ```

### 10.3 Service Worker 离线支持

#### 前端: Service Worker配置
**新建文件:** `frontend/public/sw.js`

1. 预缓存策略:
   ```javascript
   const CACHE_VERSION = 'v1';
   const PRECACHE_URLS = [
     '/', '/index.html',
     '/assets/main.js', '/assets/main.css',
     // 核心UI资源
   ];
   ```

2. 运行时缓存策略:
   - **Cache First**: 静态资源(字体/CSS/JS)
   - **Network First**: API数据
   - **Stale While Revalidate**: 照片缩略图
   - **Network Only**: 关键操作(拍照/打印)

#### 前端: Service Worker注册
**修改文件:** `frontend/src/main.tsx`

```typescript
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js');
}
```

### 10.4 离线照片队列

#### 前端: IndexedDB 离线存储
**新建文件:** `frontend/src/app/services/offlineQueue.ts`

1. 离线拍照队列:
   ```typescript
   class OfflineQueue {
     async enqueue(photo: CapturedPhoto): Promise<void>;
     async dequeue(): Promise<CapturedPhoto | null>;
     async peek(): Promise<CapturedPhoto[]>;
     async sync(): Promise<void>;       // 恢复网络后上传
     async getQueueSize(): Promise<number>;
   }
   ```

2. 离线打印队列:
   ```typescript
   class PrintQueue {
     async enqueue(job: PrintJob): Promise<void>;
     async processQueue(): Promise<void>;
   }
   ```

3. 网络状态监听:
   ```typescript
   // 使用 navigator.onLine + online/offline 事件
   // 离线时本地排队，恢复网络后自动同步
   ```

### 10.5 CDN分发优化

#### 后端: 静态资源CDN URL生成
**修改文件:** `backend/app/services/storage_service.py`

1. 配置R2公共桶 + 自定义域名:
   ```
   CDN_BASE_URL=https://cdn.aibooth.app
   ```

2. 响应头优化:
   - `Cache-Control: public, max-age=31536000, immutable` (1年缓存)
   - `ETag` 内容哈希
   - `Vary: Accept` (内容协商)

#### 前端: 构建产物哈希
**修改文件:** `frontend/vite.config.ts`

1. 文件名哈希:
   ```typescript
   build: {
     rollupOptions: {
       output: {
         assetFileNames: 'assets/[name].[hash][extname]',
         chunkFileNames: 'chunks/[name].[hash].js',
         entryFileNames: 'entries/[name].[hash].js',
       }
     }
   }
   ```

### 10.6 数据库查询优化

#### 后端: 查询优化
**修改文件:** `backend/app/models/models.py` 和各 Repository

1. 添加缺失索引:
   - Share: `(photo_id, created_at)` 复合索引
   - AITask: `(user_id, status, created_at)` 复合索引
   - AnalyticsEvent: `(event_id, event_type, created_at)` 复合索引
   - PhotoSession: `(event_id, status)` 复合索引

2. 查询超时配置:
   ```python
   # database.py
   connect_args={"statement_timeout": "30000"}  # 30秒
   ```

3. N+1查询消除:
   - 使用 `selectinload` 预加载关联(已部分实现)
   - 批量查询代替循环单查

### 10.7 前端性能优化

#### 代码分割优化
**修改文件:** `frontend/src/app/App.tsx`

1. 更细粒度的懒加载:
   ```typescript
   const CameraScreen = lazy(() => import('./screens/CameraScreen'));
   const BeautyScreen = lazy(() => import('./screens/BeautyScreen'));
   const TemplateEditorScreen = lazy(() => import('./screens/TemplateEditorScreen'));
   // 大屏幕分开打包
   ```

2. 预加载关键路径:
   ```html
   <!-- index.html -->
   <link rel="preload" href="/images/scenes/wedding-guests-fun.webp" as="image">
   ```

#### 虚拟列表
**新建文件:** `frontend/src/app/components/VirtualPhotoGrid.tsx`

1. 对于大量照片的列表/网格:
   - 使用 `react-window` 或 `@tanstack/virtual`
   - 仅渲染可见行/列
   - 回收DOM节点

### 10.8 监控与性能分析

#### 后端: 慢查询日志
**修改文件:** `backend/app/core/database.py`

```python
# 记录超过500ms的查询
event.listen(Engine, "before_cursor_execute", log_slow_queries)
```

#### 前端: 性能监控
**新建文件:** `frontend/src/app/utils/performance.ts`

1. Web Vitals监控:
   - LCP (Largest Contentful Paint)
   - FID (First Input Delay)
   - CLS (Cumulative Layout Shift)
   - 上报到分析端点

## 验收标准
1. 照片缩略图加载时间从原图的3-5秒降低到<200ms
2. WebP格式照片体积比JPEG减少30-50%
3. 模板/事件数据列表加载<200ms(Redis缓存命中)
4. Service Worker安装后，静态资源从缓存加载<50ms
5. 断网状态下能继续拍照(本地队列)
6. 恢复网络后离线照片自动上传
7. 1000张照片的相册页滚动不掉帧(虚拟列表)
8. Lighthouse评分 > 90

## 技术选型建议
- 缩略图: Pillow + Pillow-SIMD
- 缓存: Redis (已有)
- SW: Workbox (Google的SW工具库)
- 虚拟列表: `@tanstack/virtual` 或 `react-window`
- 监控: Sentry (已有) + Web Vitals
