import { v4 as uuidv4 } from 'uuid';

export interface CapturedPhoto {
  id: string;
  blob: Blob;
  eventId: string;
  sessionId?: string;
  metadata: Record<string, any>;
  timestamp: number;
  status: 'pending' | 'uploading' | 'completed' | 'failed';
  retryCount: number;
}

export interface PrintJob {
  id: string;
  photoId: string;
  copies: number;
  templateId?: string;
  timestamp: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  retryCount: number;
}

class IndexedDBStore<T> {
  private dbName: string;
  private storeName: string;
  private db: IDBDatabase | null = null;
  private version = 1;

  constructor(dbName: string, storeName: string) {
    this.dbName = dbName;
    this.storeName = storeName;
    this.init();
  }

  private async init(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!('indexedDB' in window)) {
        console.warn('IndexedDB is not supported');
        reject(new Error('IndexedDB is not supported'));
        return;
      }

      const request = indexedDB.open(this.dbName, this.version);

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains(this.storeName)) {
          db.createObjectStore(this.storeName, { keyPath: 'id' });
        }
      };

      request.onsuccess = (event) => {
        this.db = (event.target as IDBOpenDBRequest).result;
        resolve();
      };

      request.onerror = (event) => {
        console.error('IndexedDB init error:', (event.target as IDBOpenDBRequest).error);
        reject((event.target as IDBOpenDBRequest).error);
      };
    });
  }

  private async getStore(mode: IDBTransactionMode = 'readonly'): Promise<IDBObjectStore> {
    if (!this.db) {
      await this.init();
    }

    const transaction = this.db!.transaction(this.storeName, mode);
    return transaction.objectStore(this.storeName);
  }

  async add(item: T): Promise<void> {
    const store = await this.getStore('readwrite');
    return new Promise((resolve, reject) => {
      const request = store.add(item);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  async update(item: T): Promise<void> {
    const store = await this.getStore('readwrite');
    return new Promise((resolve, reject) => {
      const request = store.put(item);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  async delete(id: string): Promise<void> {
    const store = await this.getStore('readwrite');
    return new Promise((resolve, reject) => {
      const request = store.delete(id);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  async getAll(): Promise<T[]> {
    const store = await this.getStore('readonly');
    return new Promise((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async get(id: string): Promise<T | undefined> {
    const store = await this.getStore('readonly');
    return new Promise((resolve, reject) => {
      const request = store.get(id);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async count(): Promise<number> {
    const store = await this.getStore('readonly');
    return new Promise((resolve, reject) => {
      const request = store.count();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }
}

class OfflineQueue {
  private photoStore: IndexedDBStore<CapturedPhoto>;
  private printStore: IndexedDBStore<PrintJob>;
  private isSyncing: boolean = false;
  private maxRetries: number = 5;
  private syncInProgress: boolean = false;

  constructor() {
    this.photoStore = new IndexedDBStore<CapturedPhoto>('DBooth', 'offlinePhotos');
    this.printStore = new IndexedDBStore<PrintJob>('DBooth', 'printJobs');

    // Sync when network is restored
    if ('onLine' in navigator) {
      window.addEventListener('online', () => {
        this.startSync();
      });
    }

    // Also listen to custom network events from main.tsx
    window.addEventListener('network-restored', () => {
      this.startSync();
    });
  }

  /**
   * Add a captured photo to offline queue
   */
  async enqueuePhoto(
    blob: Blob,
    eventId: string,
    sessionId?: string,
    metadata: Record<string, any> = {}
  ): Promise<CapturedPhoto> {
    const photo: CapturedPhoto = {
      id: uuidv4(),
      blob,
      eventId,
      sessionId,
      metadata,
      timestamp: Date.now(),
      status: 'pending',
      retryCount: 0,
    };

    await this.photoStore.add(photo);
    console.log('Photo added to offline queue:', photo.id);

    // Try to sync immediately if online
    if (navigator.onLine) {
      this.startSync();
    }

    return photo;
  }

  /**
   * Add a print job to offline queue
   */
  async enqueuePrintJob(
    photoId: string,
    copies: number = 1,
    templateId?: string
  ): Promise<PrintJob> {
    const job: PrintJob = {
      id: uuidv4(),
      photoId,
      copies,
      templateId,
      timestamp: Date.now(),
      status: 'pending',
      retryCount: 0,
    };

    await this.printStore.add(job);
    console.log('Print job added to offline queue:', job.id);

    if (navigator.onLine) {
      this.processPrintQueue();
    }

    return job;
  }

  /**
   * Get all pending photos
   */
  async getPendingPhotos(): Promise<CapturedPhoto[]> {
    const allPhotos = await this.photoStore.getAll();
    return allPhotos.filter(photo => photo.status === 'pending' || photo.status === 'failed');
  }

  /**
   * Get queue size
   */
  async getQueueSize(): Promise<number> {
    return this.photoStore.count();
  }

  /**
   * Start syncing offline photos
   */
  async startSync(): Promise<void> {
    if (this.syncInProgress) {
      console.log('Sync already in progress, skipping');
      return;
    }

    if (!navigator.onLine) {
      console.log('Network offline, cannot sync');
      return;
    }

    this.syncInProgress = true;
    console.log('Starting offline photo sync...');

    try {
      const pendingPhotos = await this.getPendingPhotos();
      console.log(`Found ${pendingPhotos.length} pending photos to sync`);

      for (const photo of pendingPhotos) {
        if (photo.retryCount >= this.maxRetries) {
          console.log(`Photo ${photo.id} exceeded max retries, marking as failed`);
          photo.status = 'failed';
          await this.photoStore.update(photo);
          continue;
        }

        try {
          photo.status = 'uploading';
          await this.photoStore.update(photo);

          await this.uploadPhoto(photo);

          photo.status = 'completed';
          await this.photoStore.update(photo);

          // Remove after successful upload (optional, could keep for history)
          await this.photoStore.delete(photo.id);

          console.log('Successfully synced photo:', photo.id);
        } catch (error) {
          console.error(`Failed to upload photo ${photo.id}:`, error);
          photo.status = 'failed';
          photo.retryCount += 1;
          await this.photoStore.update(photo);
        }
      }

      // After syncing photos, process print queue
      await this.processPrintQueue();

      console.log('Offline sync completed');
    } catch (error) {
      console.error('Sync failed:', error);
    } finally {
      this.syncInProgress = false;
    }
  }

  /**
   * Process pending print jobs
   */
  async processPrintQueue(): Promise<void> {
    if (!navigator.onLine) {
      return;
    }

    const allJobs = await this.printStore.getAll();
    const pendingJobs = allJobs.filter(job => job.status === 'pending' || job.status === 'failed');

    console.log(`Found ${pendingJobs.length} pending print jobs`);

    for (const job of pendingJobs) {
      if (job.retryCount >= this.maxRetries) {
        job.status = 'failed';
        await this.printStore.update(job);
        continue;
      }

      try {
        job.status = 'processing';
        await this.printStore.update(job);

        await this.sendPrintJob(job);

        job.status = 'completed';
        await this.printStore.update(job);
        await this.printStore.delete(job.id);

        console.log('Successfully processed print job:', job.id);
      } catch (error) {
        console.error(`Failed to process print job ${job.id}:`, error);
        job.status = 'failed';
        job.retryCount += 1;
        await this.printStore.update(job);
      }
    }
  }

  /**
   * Upload photo to server
   */
  private async uploadPhoto(photo: CapturedPhoto): Promise<any> {
    const formData = new FormData();
    formData.append('file', photo.blob, `photo_${photo.id}.jpg`);
    formData.append('event_id', photo.eventId);
    if (photo.sessionId) {
      formData.append('session_id', photo.sessionId);
    }
    Object.entries(photo.metadata).forEach(([key, value]) => {
      formData.append(`metadata[${key}]`, String(value));
    });

    const response = await fetch('/api/v1/photos/upload', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed with status ${response.status}`);
    }

    return response.json();
  }

  /**
   * Send print job to server
   */
  private async sendPrintJob(job: PrintJob): Promise<any> {
    const response = await fetch('/api/v1/print', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        photo_id: job.photoId,
        copies: job.copies,
        template_id: job.templateId,
      }),
    });

    if (!response.ok) {
      throw new Error(`Print job failed with status ${response.status}`);
    }

    return response.json();
  }

  /**
   * Clear all completed items
   */
  async clearCompleted(): Promise<void> {
    const photos = await this.photoStore.getAll();
    for (const photo of photos.filter(p => p.status === 'completed')) {
      await this.photoStore.delete(photo.id);
    }

    const jobs = await this.printStore.getAll();
    for (const job of jobs.filter(j => j.status === 'completed')) {
      await this.printStore.delete(job.id);
    }
  }
}

// Singleton instance
export const offlineQueue = new OfflineQueue();

export default offlineQueue;
