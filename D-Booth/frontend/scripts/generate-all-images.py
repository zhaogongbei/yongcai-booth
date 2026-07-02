"""
批量生成 AI Booth 项目所需的图片
"""
import subprocess
import time
import os

# 图片配置
IMAGES = [
    # 场景图片 (1920x1080)
    {
        'key': 'wedding-couple-booth',
        'prompt': 'Professional wedding scene, elegant couple in formal white dress and black suit posing at modern iPad photo booth with ring lights, romantic warm lighting, floral decorations in background, joyful expressions, high quality event photography, 8k',
        'size': '2K',
        'category': 'scenes'
    },
    {
        'key': 'wedding-guests-fun',
        'prompt': 'Wedding guests having fun at photo booth, group of happy people making funny poses, colorful props, festive atmosphere, candid photography, warm lighting, celebration vibes',
        'size': '2K',
        'category': 'scenes'
    },
    {
        'key': 'corporate-event-group',
        'prompt': 'Corporate team building event, diverse group of professionals in business casual attire laughing together at photo booth, modern office party setting, branded backdrop, energetic atmosphere, professional photography',
        'size': '2K',
        'category': 'scenes'
    },
    {
        'key': 'conference-networking',
        'prompt': 'Business conference networking scene, professionals exchanging ideas at photo booth area, modern convention center, bright lighting, contemporary corporate environment',
        'size': '2K',
        'category': 'scenes'
    },
    {
        'key': 'birthday-party-fun',
        'prompt': 'Joyful birthday party celebration, family with children and adults gathered around photo booth, colorful balloons and decorations, birthday cake visible, happy expressions, festive indoor setting',
        'size': '2K',
        'category': 'scenes'
    },
    {
        'key': 'kids-birthday-booth',
        'prompt': 'Vibrant kids birthday party, children making silly faces at photo booth, rainbow balloons, colorful streamers, playful atmosphere, bright cheerful lighting',
        'size': '2K',
        'category': 'scenes'
    },
    {
        'key': 'brand-popup-mall',
        'prompt': 'Modern brand activation pop-up booth in shopping mall, stylish customers trying photo booth, sleek minimalist design with branded elements, bright retail environment, contemporary commercial photography',
        'size': '2K',
        'category': 'scenes'
    },
    {
        'key': 'festival-outdoor-booth',
        'prompt': 'Outdoor music festival scene, young people enjoying photo booth at summer event, creative colorful setup, festival atmosphere, natural daylight, energetic vibe',
        'size': '2K',
        'category': 'scenes'
    },
    
    # 产品图片 (1600x900)
    {
        'key': 'ipad-booth-setup',
        'prompt': 'Professional iPad Pro photo booth setup on elegant stand, ring light attached, clean white background, studio product photography, high-end tech equipment, minimalist aesthetic, 8k quality',
        'size': '2K',
        'category': 'products'
    },
    {
        'key': 'camera-equipment',
        'prompt': 'Professional Canon mirrorless camera setup for photo booth, camera body and lenses on wooden table, professional photography equipment, studio lighting, product photography style',
        'size': '2K',
        'category': 'products'
    },
    {
        'key': 'printer-dnp-ds620',
        'prompt': 'DNP thermal sublimation photo printer, professional photo printing equipment, compact design, white and black printer on desk, product photography, clean background',
        'size': '2K',
        'category': 'products'
    },
    {
        'key': 'photo-prints-showcase',
        'prompt': 'Collection of 2x6 photo booth prints displayed on white marble surface, multiple photo strips showing different people at events, professional print quality, soft studio lighting, product showcase',
        'size': '2K',
        'category': 'products'
    },
    {
        'key': 'polaroid-style-prints',
        'prompt': 'Stack of instant Polaroid-style photo prints, vintage aesthetic, warm tones, scattered on wooden table, nostalgic feel, product photography',
        'size': '2K',
        'category': 'products'
    },
    {
        'key': 'photo-album-collection',
        'prompt': 'Beautiful photo album collection, event memories organized in elegant albums, photos displayed on table, high quality print products, lifestyle photography',
        'size': '2K',
        'category': 'products'
    },
    
    # 背景图片
    {
        'key': 'attract-screen-01',
        'prompt': 'Vibrant party atmosphere background, colorful bokeh lights, festive celebration vibes, abstract colorful light effects, dynamic energy, perfect for digital display',
        'size': '4K',
        'category': 'backgrounds'
    },
    {
        'key': 'attract-screen-elegant',
        'prompt': 'Elegant wedding background, soft romantic lighting, delicate flowers, pastel color palette, dreamy bokeh, sophisticated ambiance',
        'size': '4K',
        'category': 'backgrounds'
    },
    {
        'key': 'attract-screen-corporate',
        'prompt': 'Professional corporate background, modern minimalist design, clean geometric patterns, navy blue and white color scheme, business environment aesthetic',
        'size': '4K',
        'category': 'backgrounds'
    },
    {
        'key': 'dashboard-bg-gradient',
        'prompt': 'Warm gradient background, smooth color transition from terracotta to cream, soft elegant texture, abstract minimal design',
        'size': '2K',
        'category': 'backgrounds'
    },
    {
        'key': 'stats-bg-pattern',
        'prompt': 'Subtle geometric pattern background, minimal grid design, soft neutral colors, data visualization aesthetic, clean modern look',
        'size': '2K',
        'category': 'backgrounds'
    },
]

# Avatars - 使用更简单的提示词
AVATAR_PROMPTS = [
    ('avatar-woman-asian-01', 'Professional portrait of young Asian woman, age 25-30, friendly smile, business casual attire, neutral background, headshot photography'),
    ('avatar-man-caucasian-01', 'Professional portrait of Caucasian man, age 30-35, confident expression, business suit, neutral background, corporate headshot'),
    ('avatar-woman-african-01', 'Professional portrait of African woman, age 30-40, warm smile, professional attire, neutral background, friendly headshot'),
    ('avatar-man-asian-01', 'Professional portrait of Asian man, age 28-35, business casual, confident pose, neutral background, corporate photography'),
    ('avatar-woman-latina-01', 'Professional portrait of Latina woman, age 25-30, energetic smile, casual professional attire, neutral background'),
    ('avatar-man-african-01', 'Professional portrait of African man, age 30-40, stylish confident look, modern attire, neutral background'),
    ('avatar-elderly-couple', 'Warm portrait of elderly couple, age 65+, loving expressions, casual comfortable clothing, soft background'),
    ('avatar-teen-girl', 'Portrait of teenage girl, age 15-17, cheerful smile, casual clothing, bright friendly atmosphere'),
]

def generate_image(config):
    """生成单张图片"""
    base_path = r"d:\安装包归档\咏彩booth\AI Booth 2026 App Design\public\images"
    output_path = os.path.join(base_path, config['category'], f"{config['key']}.png")
    
    cmd = [
        'python',
        'scripts/generate_image.py',
        '--size', config['size'],
        config['prompt'],
        output_path
    ]
    
    print(f"\n{'='*60}")
    print(f"Generating: {config['key']}")
    print(f"Category: {config['category']}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print(f"[SUCCESS] {config['key']}")
            return True
        else:
            print(f"[FAILED] {config['key']}")
            print(f"Error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] {config['key']}")
        return False
    except Exception as e:
        print(f"[ERROR] {config['key']} - {str(e)}")
        return False

def main():
    os.chdir(r"C:\Users\Administrator\.claude\skills\imagen")
    
    print("AI Booth Batch Image Generation")
    print("=" * 60)
    
    # 添加头像配置
    for key, prompt in AVATAR_PROMPTS:
        IMAGES.append({
            'key': key,
            'prompt': prompt,
            'size': '1K',
            'category': 'avatars'
        })
    
    total = len(IMAGES)
    success = 0
    failed = 0
    
    for i, config in enumerate(IMAGES, 1):
        print(f"\nProgress: {i}/{total}")
        if generate_image(config):
            success += 1
        else:
            failed += 1
        
        # Avoid API rate limiting
        if i < total:
            time.sleep(2)
    
    print(f"\n{'='*60}")
    print("Generation Summary")
    print(f"{'='*60}")
    print(f"Total: {total}")
    print(f"Success: {success}")
    print(f"Failed: {failed}")
    print(f"\nDone!")

if __name__ == '__main__':
    main()
