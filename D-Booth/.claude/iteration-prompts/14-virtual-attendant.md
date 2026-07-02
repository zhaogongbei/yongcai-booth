# 虚拟助手与语音引导 - 迭代提示词

## 目标
实现拍照各阶段的TTS语音引导和视频播放功能，支持多语言配音，增强拍照亭的互动体验和品牌专业感。

## 当前状态
- 项目完全无虚拟助手功能
- dslrBooth 有完整的虚拟助手(多语言TTS + 视频播放)
- AttractScreen 有基础音乐播放器

## 需要实现的功能

### 14.1 后端: TTS语音合成服务
**新建文件:** `backend/app/services/tts_service.py`

1. TTS引擎封装:
   ```python
   class TTSEngine:
       async def synthesize(
           text: str,
           language: str = "zh-CN",
           voice: str = "female",
           speed: float = 1.0
       ) -> bytes:  # 返回MP3音频字节
   ```

2. TTS方案(按优先级):
   - **方案A: Edge TTS (推荐)**
     - `pip install edge-tts`
     - 免费、质量好、支持中文
     - 中文女声: zh-CN-XiaoxiaoNeural
     - 中文男声: zh-CN-YunxiNeural
     - 英文女声: en-US-JennyNeural
     - 英文男声: en-US-GuyNeural

   - **方案B: Azure Cognitive Services**
     - 付费、质量最佳
     - 更多语音选择

   - **方案C: 本地TTS**
     - pyttsx3 (无需网络，质量一般)
     - 作为离线fallback

3. 语音缓存:
   - 按(text, language, voice)缓存已合成的音频
   - 避免重复合成相同文本

### 14.2 后端: 虚拟助手服务
**新建文件:** `backend/app/services/virtual_attendant_service.py`

1. 播放时机配置:
   ```python
   class PlaybackTiming(str, Enum):
       ATTRACT_SCREEN = "attract_screen"      # 欢迎屏
       BEFORE_COUNTDOWN = "before_countdown"  # 倒计时前
       AFTER_CAPTURE = "after_capture"        # 拍摄后
       BEFORE_SIGNATURE = "before_signature"  # 签名前
       DURING_PROCESSING = "during_processing" # 处理中
       AFTER_PROCESSING = "after_processing"   # 处理后
       SESSION_END = "session_end"            # 会话结束
   ```

2. 提示文本模板(中英文):
   ```python
   PROMPT_TEMPLATES = {
       "attract_screen": {
           "zh-CN": "欢迎光临！点击屏幕开始拍照吧！",
           "en-US": "Welcome! Tap the screen to start taking photos!"
       },
       "before_countdown": {
           "zh-CN": "准备拍照！请看镜头，微笑！",
           "en-US": "Get ready! Look at the camera and smile!"
       },
       "after_capture": {
           "zh-CN": "拍得真棒！点击下一步继续。",
           "en-US": "Great shot! Tap next to continue."
       },
       # ...更多时机
   }
   ```

3. 媒体播放:
   ```python
   async def get_playlist(event_id: UUID) -> List[PlaylistItem]:
       """获取事件的虚拟助手播放列表"""
       return [
           PlaylistItem(
               timing=PlaybackTiming.BEFORE_COUNTDOWN,
               type="tts",       # tts / mp3 / video
               text="准备拍照！", # TTS文本
               media_url=None,   # mp3或mp4的URL
               language="zh-CN",
               voice="female",
               loop=False,       # 是否循环
               random=False      # 是否随机选择
           ),
       ]
   ```

### 14.3 后端API
**新建文件:** `backend/app/api/v1/virtual_attendant.py`

```
GET    /api/v1/virtual-attendant/playlist/{event_id}  → 获取播放列表
PUT    /api/v1/virtual-attendant/playlist/{event_id}  → 更新播放列表
POST   /api/v1/virtual-attendant/preview              → 预览TTS语音(合成并返回)
POST   /api/v1/virtual-attendant/tts/generate         → 合成TTS并返回MP3
POST   /api/v1/virtual-attendant/media/upload         → 上传自定义MP3/MP4
```

### 14.4 前端: 虚拟助手播放器
**新建文件:** `frontend/src/app/services/attendantPlayer.ts`

1. 播放器类:
   ```typescript
   class AttendantPlayer {
     private audioCtx: AudioContext;
     private currentSource: AudioBufferSourceNode | null;
   
     async loadPlaylist(eventId: string): Promise<void>;
     async playForTiming(timing: PlaybackTiming): Promise<void>;
     async stop(): Promise<void>;
     async preloadAll(): Promise<void>;  // 预加载全部音频
   }
   ```

2. 集成到拍照流程:
   - `CameraScreen`: 倒计时前播放TTS
   - `AttractScreen`: 循环播放欢迎语音
   - 拍照后: 播放称赞语音
   - 处理中: 循环播放等待语音/音乐

### 14.5 前端: 虚拟助手配置页面
**新建文件:** `frontend/src/app/screens/AttendantConfigScreen.tsx`

1. 配置:
   - 语言选择(中文/英文)
   - 语音选择(男声/女声)
   - 每个时机启用/禁用
   - 自定义文本(替换默认提示)
   - 音频/视频上传(替代TTS)
   - 音量调节
   - 试听按钮

## 验收标准
1. 客人点击"开始拍照"后听到"准备拍照，请看镜头！"
2. 拍照完成后听到"拍得真棒！"
3. 欢迎屏循环播放欢迎语音
4. TTS语音自然流畅(非机械音)
5. 管理员可自定义各阶段的提示文本
6. 支持上传自定义MP3替代TTS
7. 语音缓存机制避免重复合成

## 技术选型建议
- TTS: `edge-tts` (免费、高质量、支持中英文)
- 音频播放: Web Audio API (精确控制)
- TTS缓存: Redis 或本地文件缓存
