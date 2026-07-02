#!/usr/bin/env node

/**
 * 图片下载脚本
 * 从 Unsplash API 下载项目所需的图片素材
 * 
 * 使用方法:
 * 1. 设置环境变量 UNSPLASH_ACCESS_KEY
 * 2. 运行: node scripts/download-images.mjs
 */

import fs from 'fs';
import path from 'path';
import https from 'https';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Unsplash API 配置
const UNSPLASH_ACCESS_KEY = process.env.UNSPLASH_ACCESS_KEY || 'YOUR_ACCESS_KEY_HERE';
const BASE_URL = 'https://api.unsplash.com';

// 图片配置
const IMAGE_CONFIGS = [
  // 场景图片
  {
    key: 'wedding-couple-booth',
    query: 'wedding photo booth couple elegant',
    width: 1920,
    height: 1080,
    category: 'scenes'
  },
  {
    key: 'wedding-guests-fun',
    query: 'wedding guests photo booth fun',
    width: 1920,
    height: 1080,
    category: 'scenes'
  },
  {
    key: 'corporate-event-group',
    query: 'corporate team event photo booth',
    width: 1920,
    height: 1080,
    category: 'scenes'
  },
  {
    key: 'conference-networking',
    query: 'business conference networking',
    width: 1920,
    height: 1080,
    category: 'scenes'
  },
  {
    key: 'birthday-party-fun',
    query: 'birthday party celebration family',
    width: 1920,
    height: 1080,
    category: 'scenes'
  },
  {
    key: 'kids-birthday-booth',
    query: 'kids birthday party balloons',
    width: 1920,
    height: 1080,
    category: 'scenes'
  },
  {
    key: 'brand-popup-mall',
    query: 'brand activation pop up mall',
    width: 1920,
    height: 1080,
    category: 'scenes'
  },
  {
    key: 'festival-outdoor-booth',
    query: 'music festival outdoor event',
    width: 1920,
    height: 1080,
    category: 'scenes'
  },
  
  // 产品图片
  {
    key: 'ipad-booth-setup',
    query: 'ipad pro setup professional photography',
    width: 1600,
    height: 900,
    category: 'products'
  },
  {
    key: 'camera-equipment',
    query: 'professional camera dslr equipment',
    width: 1600,
    height: 900,
    category: 'products'
  },
  {
    key: 'printer-dnp-ds620',
    query: 'photo printer professional printing',
    width: 1600,
    height: 900,
    category: 'products'
  },
  {
    key: 'photo-prints-showcase',
    query: 'printed photos showcase collection',
    width: 1600,
    height: 900,
    category: 'products'
  },
  {
    key: 'polaroid-style-prints',
    query: 'polaroid instant photos vintage',
    width: 1600,
    height: 900,
    category: 'products'
  },
  {
    key: 'photo-album-collection',
    query: 'photo album memory collection',
    width: 1600,
    height: 900,
    category: 'products'
  },
  
  // 背景图片
  {
    key: 'attract-screen-01',
    query: 'colorful party celebration lights',
    width: 2560,
    height: 1440,
    category: 'backgrounds'
  },
  {
    key: 'attract-screen-elegant',
    query: 'elegant wedding romantic flowers',
    width: 2560,
    height: 1440,
    category: 'backgrounds'
  },
  {
    key: 'attract-screen-corporate',
    query: 'modern corporate office professional',
    width: 2560,
    height: 1440,
    category: 'backgrounds'
  },
  {
    key: 'dashboard-bg-gradient',
    query: 'abstract gradient warm colors',
    width: 1920,
    height: 1080,
    category: 'backgrounds'
  },
  {
    key: 'stats-bg-pattern',
    query: 'geometric pattern minimal abstract',
    width: 1920,
    height: 1080,
    category: 'backgrounds'
  },
  
  // 头像图片
  {
    key: 'avatar-woman-asian-01',
    query: 'asian woman portrait professional smile',
    width: 400,
    height: 400,
    category: 'avatars',
    orientation: 'squarish'
  },
  {
    key: 'avatar-man-caucasian-01',
    query: 'caucasian man portrait professional business',
    width: 400,
    height: 400,
    category: 'avatars',
    orientation: 'squarish'
  },
  {
    key: 'avatar-woman-african-01',
    query: 'african woman portrait friendly professional',
    width: 400,
    height: 400,
    category: 'avatars',
    orientation: 'squarish'
  },
  {
    key: 'avatar-man-asian-01',
    query: 'asian man portrait professional business',
    width: 400,
    height: 400,
    category: 'avatars',
    orientation: 'squarish'
  },
  {
    key: 'avatar-woman-latina-01',
    query: 'latina woman portrait energetic smile',
    width: 400,
    height: 400,
    category: 'avatars',
    orientation: 'squarish'
  },
  {
    key: 'avatar-man-african-01',
    query: 'african man portrait stylish confident',
    width: 400,
    height: 400,
    category: 'avatars',
    orientation: 'squarish'
  },
  {
    key: 'avatar-elderly-couple',
    query: 'elderly couple portrait warm loving',
    width: 400,
    height: 400,
    category: 'avatars',
    orientation: 'squarish'
  },
  {
    key: 'avatar-teen-girl',
    query: 'teenage girl portrait happy cheerful',
    width: 400,
    height: 400,
    category: 'avatars',
    orientation: 'squarish'
  },
];

// 辅助函数
function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

function downloadFile(url, filepath) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(filepath);
    https.get(url, (response) => {
      response.pipe(file);
      file.on('finish', () => {
        file.close();
        resolve();
      });
    }).on('error', (err) => {
      fs.unlink(filepath, () => {});
      reject(err);
    });
  });
}

async function searchUnsplash(query, orientation = 'landscape') {
  return new Promise((resolve, reject) => {
    const url = `${BASE_URL}/search/photos?query=${encodeURIComponent(query)}&orientation=${orientation}&per_page=1`;
    const options = {
      headers: {
        'Authorization': `Client-ID ${UNSPLASH_ACCESS_KEY}`
      }
    };

    https.get(url, options, (response) => {
      let data = '';
      response.on('data', chunk => data += chunk);
      response.on('end', () => {
        try {
          const result = JSON.parse(data);
          if (result.results && result.results.length > 0) {
            resolve(result.results[0]);
          } else {
            reject(new Error('No results found'));
          }
        } catch (err) {
          reject(err);
        }
      });
    }).on('error', reject);
  });
}

async function downloadImage(config) {
  try {
    console.log(`\n🔍 Searching: ${config.query}`);
    
    const photo = await searchUnsplash(config.query, config.orientation || 'landscape');
    const downloadUrl = `${photo.urls.raw}&w=${config.width}&h=${config.height}&fit=crop`;
    
    const categoryDir = path.join(__dirname, '..', 'public', 'images', config.category);
    ensureDir(categoryDir);
    
    const filepath = path.join(categoryDir, `${config.key}.jpg`);
    
    console.log(`📥 Downloading: ${config.key}.jpg`);
    console.log(`   From: ${photo.user.name} (@${photo.user.username})`);
    console.log(`   URL: ${photo.links.html}`);
    
    await downloadFile(downloadUrl, filepath);
    
    console.log(`✅ Saved: ${filepath}`);
    
    // 延迟以遵守 API 速率限制
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    return {
      key: config.key,
      success: true,
      photographer: photo.user.name,
      photographerUrl: photo.user.links.html,
      photoUrl: photo.links.html
    };
  } catch (error) {
    console.error(`❌ Error downloading ${config.key}:`, error.message);
    return {
      key: config.key,
      success: false,
      error: error.message
    };
  }
}

async function main() {
  console.log('🎨 AI Booth Image Downloader');
  console.log('=============================\n');
  
  if (UNSPLASH_ACCESS_KEY === 'YOUR_ACCESS_KEY_HERE') {
    console.error('❌ 错误: 请设置 UNSPLASH_ACCESS_KEY 环境变量');
    console.log('\n获取 Access Key:');
    console.log('1. 访问 https://unsplash.com/developers');
    console.log('2. 注册并创建应用');
    console.log('3. 复制 Access Key');
    console.log('4. 设置环境变量: export UNSPLASH_ACCESS_KEY=your_key_here');
    process.exit(1);
  }
  
  console.log(`📦 Total images to download: ${IMAGE_CONFIGS.length}\n`);
  
  const results = [];
  
  for (const config of IMAGE_CONFIGS) {
    const result = await downloadImage(config);
    results.push(result);
  }
  
  // 生成归属信息文件
  const attributions = results
    .filter(r => r.success)
    .map(r => ({
      key: r.key,
      photographer: r.photographer,
      photographerUrl: r.photographerUrl,
      photoUrl: r.photoUrl
    }));
  
  const attributionsPath = path.join(__dirname, '..', 'public', 'images', 'ATTRIBUTIONS.json');
  fs.writeFileSync(attributionsPath, JSON.stringify(attributions, null, 2));
  
  console.log('\n=============================');
  console.log('📊 Download Summary');
  console.log('=============================');
  console.log(`✅ Success: ${results.filter(r => r.success).length}`);
  console.log(`❌ Failed: ${results.filter(r => !r.success).length}`);
  console.log(`\n📝 Attributions saved to: ${attributionsPath}`);
  console.log('\n✨ Done!');
}

main().catch(console.error);
