/**
 * 图片占位符工具
 * 在开发阶段使用占位符，生产环境替换为真实图片
 */

export type ImageCategory = 'scenes' | 'avatars' | 'backgrounds' | 'products';

export interface ImageConfig {
  width: number;
  height: number;
  text: string;
  category: ImageCategory;
  filename: string;
}

/**
 * 图片资源配置
 */
export const IMAGE_ASSETS: Record<string, ImageConfig> = {
  // 场景图片
  'wedding-couple-booth': {
    width: 1920,
    height: 1080,
    text: 'Wedding Couple',
    category: 'scenes',
    filename: 'wedding-couple-booth.webp'
  },
  'wedding-guests-fun': {
    width: 1920,
    height: 1080,
    text: 'Wedding Guests',
    category: 'scenes',
    filename: 'wedding-guests-fun.webp'
  },
  'corporate-event-group': {
    width: 1920,
    height: 1080,
    text: 'Corporate Event',
    category: 'scenes',
    filename: 'corporate-event-group.webp'
  },
  'conference-networking': {
    width: 1920,
    height: 1080,
    text: 'Conference',
    category: 'scenes',
    filename: 'conference-networking.webp'
  },
  'birthday-party-fun': {
    width: 1920,
    height: 1080,
    text: 'Birthday Party',
    category: 'scenes',
    filename: 'birthday-party-fun.webp'
  },
  'kids-birthday-booth': {
    width: 1920,
    height: 1080,
    text: 'Kids Birthday',
    category: 'scenes',
    filename: 'kids-birthday-booth.webp'
  },
  'brand-popup-mall': {
    width: 1920,
    height: 1080,
    text: 'Brand Popup',
    category: 'scenes',
    filename: 'brand-popup-mall.webp'
  },
  'festival-outdoor-booth': {
    width: 1920,
    height: 1080,
    text: 'Festival',
    category: 'scenes',
    filename: 'festival-outdoor-booth.webp'
  },

  // 产品图片
  'ipad-booth-setup': {
    width: 1600,
    height: 900,
    text: 'iPad Booth',
    category: 'products',
    filename: 'ipad-booth-setup.webp'
  },
  'camera-equipment': {
    width: 1600,
    height: 900,
    text: 'Camera',
    category: 'products',
    filename: 'camera-equipment.webp'
  },
  'printer-dnp-ds620': {
    width: 1600,
    height: 900,
    text: 'Printer',
    category: 'products',
    filename: 'printer-dnp-ds620.webp'
  },
  'photo-prints-showcase': {
    width: 1600,
    height: 900,
    text: 'Photo Prints',
    category: 'products',
    filename: 'photo-prints-showcase.webp'
  },
  'polaroid-style-prints': {
    width: 1600,
    height: 900,
    text: 'Polaroid',
    category: 'products',
    filename: 'polaroid-style-prints.webp'
  },
  'photo-album-collection': {
    width: 1600,
    height: 900,
    text: 'Photo Album',
    category: 'products',
    filename: 'photo-album-collection.webp'
  },

  // 背景图片
  'attract-screen-01': {
    width: 2560,
    height: 1440,
    text: 'Party',
    category: 'backgrounds',
    filename: 'attract-screen-01.webp'
  },
  'attract-screen-elegant': {
    width: 2560,
    height: 1440,
    text: 'Elegant',
    category: 'backgrounds',
    filename: 'attract-screen-elegant.webp'
  },
  'attract-screen-corporate': {
    width: 2560,
    height: 1440,
    text: 'Corporate',
    category: 'backgrounds',
    filename: 'attract-screen-corporate.webp'
  },
  'dashboard-bg-gradient': {
    width: 1920,
    height: 1080,
    text: 'Gradient',
    category: 'backgrounds',
    filename: 'dashboard-bg-gradient.webp'
  },
  'stats-bg-pattern': {
    width: 1920,
    height: 1080,
    text: 'Pattern',
    category: 'backgrounds',
    filename: 'stats-bg-pattern.webp'
  },

  // 头像图片
  'avatar-woman-asian-01': {
    width: 400,
    height: 400,
    text: 'WA',
    category: 'avatars',
    filename: 'avatar-woman-asian-01.webp'
  },
  'avatar-man-caucasian-01': {
    width: 400,
    height: 400,
    text: 'MC',
    category: 'avatars',
    filename: 'avatar-man-caucasian-01.webp'
  },
  'avatar-woman-african-01': {
    width: 400,
    height: 400,
    text: 'WF',
    category: 'avatars',
    filename: 'avatar-woman-african-01.webp'
  },
  'avatar-man-asian-01': {
    width: 400,
    height: 400,
    text: 'MA',
    category: 'avatars',
    filename: 'avatar-man-asian-01.webp'
  },
  'avatar-woman-latina-01': {
    width: 400,
    height: 400,
    text: 'WL',
    category: 'avatars',
    filename: 'avatar-woman-latina-01.webp'
  },
  'avatar-man-african-01': {
    width: 400,
    height: 400,
    text: 'MF',
    category: 'avatars',
    filename: 'avatar-man-african-01.webp'
  },
  'avatar-elderly-couple': {
    width: 400,
    height: 400,
    text: 'EC',
    category: 'avatars',
    filename: 'avatar-elderly-couple.webp'
  },
  'avatar-teen-girl': {
    width: 400,
    height: 400,
    text: 'TG',
    category: 'avatars',
    filename: 'avatar-teen-girl.webp'
  },
};

/**
 * 生成占位符图片 URL (使用 placehold.co)
 */
export function getPlaceholder(key: string): string {
  const config = IMAGE_ASSETS[key];
  if (!config) {
    console.warn(`Image asset "${key}" not found`);
    return '';
  }
  
  const { width, height, text } = config;
  const bgColor = 'C4612F'; // Terracotta
  const textColor = 'FFFFFF';
  
  return `https://placehold.co/${width}x${height}/${bgColor}/${textColor}?text=${encodeURIComponent(text)}`;
}

/**
 * 获取图片 URL（优先使用本地文件，降级到占位符）
 */
export function getImageUrl(key: string, usePlaceholder = false): string {
  const config = IMAGE_ASSETS[key];
  if (!config) {
    return '';
  }
  
  const localPath = `/images/${config.category}/${config.filename}`;
  
  // 仅当明确指定使用占位符时才返回占位符
  if (usePlaceholder) {
    return getPlaceholder(key);
  }
  
  return localPath;
}

/**
 * 批量获取某个分类的所有图片
 */
export function getImagesByCategory(category: ImageCategory, usePlaceholder = false): Record<string, string> {
  const result: Record<string, string> = {};
  
  Object.entries(IMAGE_ASSETS).forEach(([key, config]) => {
    if (config.category === category) {
      result[key] = getImageUrl(key, usePlaceholder);
    }
  });
  
  return result;
}

/**
 * 预加载图片
 */
export function preloadImage(url: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve();
    img.onerror = reject;
    img.src = url;
  });
}

/**
 * 批量预加载图片
 */
export async function preloadImages(keys: string[]): Promise<void> {
  const urls = keys.map(key => getImageUrl(key, false));
  await Promise.all(urls.map(preloadImage));
}

/**
 * 检查图片是否存在
 */
export async function checkImageExists(url: string): Promise<boolean> {
  try {
    const response = await fetch(url, { method: 'HEAD' });
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * React Hook: 使用图片（自动降级）
 */
export function useImage(key: string): string {
  const config = IMAGE_ASSETS[key];
  if (!config) {
    return '';
  }
  
  // 在实际使用中，可以添加图片加载状态管理
  return getImageUrl(key);
}
