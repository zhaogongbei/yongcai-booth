export interface VideoRecorderOptions {
  mimeType?: string;
  videoBitsPerSecond?: number;
  framerate?: number;
}

export class VideoRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private recordedChunks: BlobPart[] = [];
  private canvas: HTMLCanvasElement | null = null;
  private stream: MediaStream | null = null;
  private startTime: number = 0;
  private options: Required<VideoRecorderOptions>;

  constructor(options: VideoRecorderOptions = {}) {
    this.options = {
      mimeType: "video/webm;codecs=vp9",
      videoBitsPerSecond: 5_000_000, // 5Mbps
      framerate: 30,
      ...options
    };
  }

  /**
   * 开始录制
   * @param canvas 要录制的Canvas元素
   */
  startRecording(canvas: HTMLCanvasElement): void {
    if (this.mediaRecorder?.state === "recording") {
      throw new Error("已经在录制中");
    }

    this.canvas = canvas;
    this.recordedChunks = [];

    // 从Canvas获取视频流
    this.stream = canvas.captureStream(this.options.framerate);

    // 创建MediaRecorder
    this.mediaRecorder = new MediaRecorder(this.stream, {
      mimeType: this.options.mimeType,
      videoBitsPerSecond: this.options.videoBitsPerSecond
    });

    // 监听数据可用事件
    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        this.recordedChunks.push(event.data);
      }
    };

    this.mediaRecorder.start();
    this.startTime = Date.now();
  }

  /**
   * 暂停录制
   */
  pauseRecording(): void {
    if (this.mediaRecorder?.state === "recording") {
      this.mediaRecorder.pause();
    }
  }

  /**
   * 恢复录制
   */
  resumeRecording(): void {
    if (this.mediaRecorder?.state === "paused") {
      this.mediaRecorder.resume();
    }
  }

  /**
   * 停止录制并返回视频Blob
   */
  async stopRecording(): Promise<Blob> {
    if (!this.mediaRecorder) {
      throw new Error("录制未开始");
    }

    return new Promise((resolve, reject) => {
      this.mediaRecorder!.onstop = () => {
        const blob = new Blob(this.recordedChunks, {
          type: this.options.mimeType
        });

        // 清理资源
        this.stream?.getTracks().forEach(track => track.stop());
        this.mediaRecorder = null;
        this.stream = null;

        resolve(blob);
      };

      this.mediaRecorder!.onerror = (error) => {
        reject(error);
      };

      if (this.mediaRecorder!.state !== "inactive") {
        this.mediaRecorder!.stop();
      }
    });
  }

  /**
   * 获取当前录制时长(秒)
   */
  getRecordingDuration(): number {
    if (!this.mediaRecorder || this.startTime === 0) {
      return 0;
    }
    return (Date.now() - this.startTime) / 1000;
  }

  /**
   * 检查浏览器是否支持指定的MIME类型
   */
  static isMimeTypeSupported(mimeType: string): boolean {
    return MediaRecorder.isTypeSupported(mimeType);
  }

  /**
   * 获取推荐的MIME类型
   */
  static getRecommendedMimeType(): string {
    const types = [
      "video/mp4;codecs=h264",
      "video/webm;codecs=vp9",
      "video/webm;codecs=vp8"
    ];

    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) {
        return type;
      }
    }

    return "";
  }
}