# 高级拍照模式 - 迭代提示词

## 目标
实现GIF动画、回旋镖(Boomerang)、视频录制、360慢动作等高级拍摄模式，丰富拍照亭的产品形态。

## 当前状态
- `CameraScreen.tsx` 仅支持单张静态照片拍摄
- `useCaptureFlow.tsx` 的 `addPhoto` 只处理单帧
- 无任何视频/GIF录制逻辑

## 需要实现的功能

### 6.1 前端: 拍摄模式选择器
**修改文件:** `frontend/src/app/screens/CameraScreen.tsx`

1. 在拍照界面顶部添加模式切换条:
   ```
   [照片] [GIF] [回旋镖] [视频] [连拍]
   ```

2. 每种模式的独立UI:
   - 照片: 保持当前行为(3秒倒计时 → 单帧捕获)
   - GIF: N帧连拍(N=3-8可配置) → GIF合成
   - 回旋镖: N帧连拍 → 正放+倒放合成
   - 视频: 开始录制 → 停止录制 → MP4保存
   - 连拍: 快速N帧 → 多照片选择

### 6.2 前端: GIF模式
**新建文件:** `frontend/src/app/services/gifRecorder.ts`

1. GIF录制逻辑:
   ```typescript
   class GifRecorder {
     startRecording(frameCount: number, frameDelay: number): void;
     captureFrame(): Promise<Blob>;          // 捕获一帧
     stopRecording(): Promise<Blob>;         // 合成GIF，返回Blob
     generateBoomerang(frames: Blob[]): Promise<Blob>; // 回旋镖合成
   }
   ```

2. GIF参数:
   - 帧数: 3/4/5/6/7/8
   - 帧间延迟: 50ms/100ms/150ms/200ms
   - 尺寸: 720×480 / 1080×720 / 720×720
   - 反向播放(回旋镖模式)

3. GIF合成:
   - 使用 `gif.js` 或 `gif.js.optimized` 前端合成
   - 或上传帧序列到后端合成

### 6.3 前端: 视频模式
**新建文件:** `frontend/src/app/services/videoRecorder.ts`

1. 视频录制逻辑:
   ```typescript
   class VideoRecorder {
     startRecording(options: VideoOptions): void;
     pauseRecording(): void;
     resumeRecording(): void;
     stopRecording(): Promise<Blob>;
     getRecordingDuration(): number; // 当前录制时长(秒)
   }
   ```

2. 使用 MediaRecorder API:
   - 从canvas.captureStream()获取流
   - 编码: VP8 (webm) / H.264 (mp4)
   - 最大录制时间: 15秒/30秒/60秒可配置

3. 视频参数:
   - 分辨率: 720p / 1080p
   - 帧率: 30fps / 60fps
   - 前置/后置视频: 录制前后各加一段

### 6.4 前端: 360慢动作模式
**新建文件:** `frontend/src/app/services/slowMotionRecorder.ts`

1. 高速帧捕获(仅DSLR模式下可用):
   - 以120fps/240fps捕获
   - 以30fps回放 = 4x/8x慢动作

2. UI:
   - 旋转速度(OrcaVue 360转台控制)
   - 录制时长指示器
   - 慢动作预览

### 6.5 后端: GIF/视频处理
**新建文件:** `backend/app/services/media_processing_service.py`

1. GIF合成:
   ```python
   async def compose_gif(
       frames: List[bytes],
       frame_delay: int = 100,  # ms
       size: tuple = (720, 480),
       reverse: bool = False
   ) -> bytes:
       # 使用Pillow合成GIF
       # 如果reverse=True，追加倒序帧(回旋镖)
   ```

2. 视频处理:
   ```python
   async def process_video(
       video_bytes: bytes,
       operations: List[VideoOperation]  # trim/crop/resize/overlay/slow_motion
   ) -> bytes:
       # 使用ffmpeg-python或subprocess调用ffmpeg
   ```

3. ffmpeg操作封装:
   - 裁剪/缩放
   - 慢动作(slow motion)
   - 视频拼接(pre-roll/post-roll)
   - 音频混合(MP3背景音乐)
   - 视频叠加(透明WEBM叠加层)
   - 动画叠加(火焰/心形/闪光/星星)

### 6.6 后端: GIF/视频API
**修改文件:** `backend/app/api/v1/photos.py` (或新建 media.py)

```
POST   /api/v1/media/gif/compose       → 上传帧序列 → 返回合成GIF
POST   /api/v1/media/video/upload      → 上传视频 → 返回处理后视频
POST   /api/v1/media/video/process     → 对已上传视频应用处理
GET    /api/v1/media/video/{id}/progress → 视频处理进度
```

### 6.7 前端: 新增模式屏幕(可选独立页面)
**新建文件:** `frontend/src/app/screens/GifCaptureScreen.tsx`
**新建文件:** `frontend/src/app/screens/VideoCaptureScreen.tsx`

如果模式UI差异较大，可拆分为独立屏幕。

### 6.8 Celery任务
**新建文件:** `backend/app/tasks/media_tasks.py`

```python
@celery_app.task
def compose_gif_task(gif_job_id: UUID):
    # 下载帧 → 合成GIF → 上传 → 更新状态

@celery_app.task
def process_video_task(video_job_id: UUID):
    # 下载视频 → ffmpeg处理 → 上传 → 更新状态
```

## 验收标准
1. GIF模式: 点击拍摄 → N帧自动连拍 → 自动合成GIF → 预览播放
2. 回旋镖: N帧正向+反向合成，播放流畅
3. 视频: 开始录制 → 实时计时器 → 停止 → MP4保存
4. 慢动作: 高速录制 → 慢速回放
5. 所有模式在无DSLR时降级为Web摄像头模式
6. GIF/视频可与模板合成(在模板的照片占位符位置嵌入GIF/视频)
7. 动画叠加(火焰/心形等)能正确叠加在视频上

## 技术选型建议
- 前端GIF: `gif.js.optimized` (Web Worker合成，不阻塞主线程)
- 前端录制: MediaRecorder API
- 后端GIF: Pillow
- 后端视频: ffmpeg (需在Docker中安装)
- 视频封装: `ffmpeg-python`
