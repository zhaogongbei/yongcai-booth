/**
 * 虚拟助手语音播放器服务
 */
export interface PlaylistItem {
  timing: string;
  enabled: boolean;
  text: string;
  language: string;
  voice: string;
}

class AttendantPlayer {
  private audio: HTMLAudioElement | null = null;
  private playlist: Map<string, PlaylistItem> = new Map();
  private currentEventId: string = '';
  private volume: number = 1.0;
  private muted: boolean = false;
  private preloadedAudios: Map<string, HTMLAudioElement> = new Map();
  private isPlaying: boolean = false;

  /**
   * 加载播放列表
   */
  async loadPlaylist(eventId: string): Promise<void> {
    this.currentEventId = eventId;
    this.playlist.clear();

    try {
      const response = await fetch(`/api/v1/virtual-attendant/playlist/${eventId}`);
      if (!response.ok) {
        throw new Error(`Failed to load playlist: ${response.statusText}`);
      }

      const items: PlaylistItem[] = await response.json();
      items.forEach(item => {
        this.playlist.set(item.timing, item);
      });

      // 预加载所有启用的语音
      await this.preloadAllAudios();
    } catch (error) {
      console.error('Failed to load virtual attendant playlist:', error);
    }
  }

  /**
   * 预加载所有启用的音频
   */
  private async preloadAllAudios(): Promise<void> {
    this.preloadedAudios.clear();

    for (const [timing, item] of this.playlist.entries()) {
      if (!item.enabled) continue;

      try {
        const audio = new Audio();
        audio.src = this.getAudioUrl(timing);
        audio.volume = this.volume;
        audio.muted = this.muted;
        audio.preload = 'auto';

        // 加载音频
        await new Promise((resolve) => {
          audio.addEventListener('canplaythrough', resolve, { once: true });
          audio.addEventListener('error', resolve, { once: true }); // 忽略加载错误
          audio.load();
        });

        this.preloadedAudios.set(timing, audio);
      } catch (error) {
        console.warn(`Failed to preload audio for timing ${timing}:`, error);
      }
    }
  }

  /**
   * 获取音频URL
   */
  private getAudioUrl(timing: string): string {
    const item = this.playlist.get(timing);
    if (!item) return '';

    return `/api/v1/virtual-attendant/tts/${timing}?event_id=${encodeURIComponent(this.currentEventId)}&language=${encodeURIComponent(item.language)}&voice=${encodeURIComponent(item.voice)}`;
  }

  /**
   * 播放指定时机的语音
   */
  async playForTiming(timing: string): Promise<void> {
    if (this.muted) return;

    const item = this.playlist.get(timing);
    if (!item || !item.enabled) {
      return;
    }

    try {
      // 停止当前正在播放的音频
      this.stop();

      // 优先使用预加载的音频
      let audio = this.preloadedAudios.get(timing);

      if (!audio) {
        audio = new Audio(this.getAudioUrl(timing));
        audio.volume = this.volume;
        audio.muted = this.muted;
      }

      this.audio = audio;
      this.isPlaying = true;

      audio.addEventListener('ended', () => {
        this.isPlaying = false;
      }, { once: true });

      audio.addEventListener('error', (e) => {
        console.error(`Failed to play audio for timing ${timing}:`, e);
        this.isPlaying = false;
      }, { once: true });

      await audio.play();
    } catch (error) {
      console.error(`Failed to play audio for timing ${timing}:`, error);
      this.isPlaying = false;
    }
  }

  /**
   * 停止播放
   */
  stop(): void {
    if (this.audio && this.isPlaying) {
      try {
        this.audio.pause();
        this.audio.currentTime = 0;
      } catch (error) {
        console.warn('Failed to stop audio:', error);
      }
    }
    this.isPlaying = false;
    this.audio = null;
  }

  /**
   * 设置音量
   */
  setVolume(volume: number): void {
    this.volume = Math.max(0, Math.min(1, volume));

    if (this.audio) {
      this.audio.volume = this.volume;
    }

    // 更新预加载音频的音量
    this.preloadedAudios.forEach(audio => {
      audio.volume = this.volume;
    });
  }

  /**
   * 设置静音
   */
  setMuted(muted: boolean): void {
    this.muted = muted;

    if (this.audio) {
      this.audio.muted = muted;
    }

    // 更新预加载音频的静音状态
    this.preloadedAudios.forEach(audio => {
      audio.muted = muted;
    });

    if (muted && this.isPlaying) {
      this.stop();
    }
  }

  /**
   * 获取当前播放状态
   */
  getIsPlaying(): boolean {
    return this.isPlaying;
  }

  /**
   * 清空缓存
   */
  clearCache(): void {
    this.stop();
    this.preloadedAudios.clear();
    this.playlist.clear();
    this.currentEventId = '';
  }
}

// 导出单例
export const attendantPlayer = new AttendantPlayer();
