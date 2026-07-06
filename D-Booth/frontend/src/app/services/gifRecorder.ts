import GIF from "gif.js.optimized";

export interface GifOptions {
  frameDelay?: number;
  quality?: number;
  width?: number;
  height?: number;
  workers?: number;
}

export class GifRecorder {
  private frames: Blob[] = [];
  private videoElement: HTMLVideoElement;
  private options: Required<GifOptions>;

  constructor(videoElement: HTMLVideoElement, options: GifOptions = {}) {
    this.videoElement = videoElement;
    this.options = {
      frameDelay: 100,
      quality: 10,
      width: videoElement.videoWidth || 1280,
      height: videoElement.videoHeight || 720,
      workers: 2,
      ...options
    };
  }

  /**
   * 捕获当前视频帧
   */
  async captureFrame(): Promise<Blob> {
    const canvas = document.createElement("canvas");
    canvas.width = this.options.width;
    canvas.height = this.options.height;
    const ctx = canvas.getContext("2d");

    if (!ctx) {
      throw new Error("无法获取Canvas上下文");
    }

    ctx.drawImage(this.videoElement, 0, 0, canvas.width, canvas.height);

    return new Promise((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (!blob) {
          reject(new Error("无法捕获帧"));
          return;
        }
        this.frames.push(blob);
        resolve(blob);
      }, "image/png");
    });
  }

  /**
   * 获取已捕获的帧列表
   */
  getFrames(): Blob[] {
    return [...this.frames];
  }

  /**
   * 清除所有已捕获的帧
   */
  clearFrames(): void {
    this.frames = [];
  }

  /**
   * 合成GIF
   * @param reverse 是否生成回旋镖效果(正向+反向)
   */
  async composeGif(reverse: boolean = false): Promise<Blob> {
    if (this.frames.length === 0) {
      throw new Error("没有可合成的帧");
    }

    const gif = new GIF({
      workers: this.options.workers,
      quality: this.options.quality,
      width: this.options.width,
      height: this.options.height,
      workerScript: "/gif.worker.js"
    });

    // 处理帧序列
    let processFrames = [...this.frames];
    if (reverse && processFrames.length > 1) {
      // 回旋镖模式：正向帧 + 反向帧(去掉首尾避免重复)
      const reversedFrames = [...processFrames].slice(1, -1).reverse();
      processFrames = [...processFrames, ...reversedFrames];
    }

    // 加载所有帧图片
    const objectUrls: string[] = [];
    const imagePromises = processFrames.map(blob => {
      return new Promise<HTMLImageElement>((resolve, reject) => {
        const img = new Image();
        const objectUrl = URL.createObjectURL(blob);
        objectUrls.push(objectUrl);
        img.onload = () => resolve(img);
        img.onerror = reject;
        img.src = objectUrl;
      });
    });

    let images: HTMLImageElement[];
    try {
      images = await Promise.all(imagePromises);
    } catch (error) {
      objectUrls.forEach(url => URL.revokeObjectURL(url));
      throw error;
    }

    // 添加帧到GIF
    images.forEach(img => {
      gif.addFrame(img, { delay: this.options.frameDelay });
    });

    const cleanupObjectUrls = () => {
      objectUrls.forEach(url => URL.revokeObjectURL(url));
    };

    // 渲染GIF
    return new Promise((resolve, reject) => {
      gif.on("finished", (blob: Blob) => {
        cleanupObjectUrls();
        resolve(blob);
      });

      gif.on("error", (error: Error) => {
        cleanupObjectUrls();
        reject(error);
      });

      gif.render();
    });
  }

  /**
   * 生成回旋镖GIF
   */
  async generateBoomerang(): Promise<Blob> {
    return this.composeGif(true);
  }
}