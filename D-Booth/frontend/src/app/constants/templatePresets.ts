import type { TemplatePreset } from '../types/template';

// 4×6英寸 = 101.6×152.4毫米 = 1200×1800像素 @ 300DPI
const BASE_PAPER_SIZE = { width: 101.6, height: 152.4 };
const BASE_RESOLUTION = 300;

// 像素转换: 毫米 × DPI / 25.4
const mmToPx = (mm: number) => Math.round(mm * BASE_RESOLUTION / 25.4);
const PHOTO_PADDING = mmToPx(3); // 3毫米边距

export const TEMPLATE_PRESETS: TemplatePreset[] = [
  {
    id: 'four-poses-single-strip-horizontal',
    name: '四姿单条水平',
    description: '4张照片水平排列',
    thumbnail: '/images/templates/preset-1.webp',
    layout: {
      paperSize: BASE_PAPER_SIZE,
      resolution: BASE_RESOLUTION,
      orientation: 'landscape',
      background: { type: 'color', value: '#ffffff' },
      elements: [
        {
          id: 'photo-1',
          type: 'photo',
          x: PHOTO_PADDING,
          y: PHOTO_PADDING,
          width: mmToPx(85.6 / 4), // 每张照片宽度
          height: mmToPx(50),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 1,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        },
        {
          id: 'photo-2',
          type: 'photo',
          x: PHOTO_PADDING * 2 + mmToPx(85.6 / 4),
          y: PHOTO_PADDING,
          width: mmToPx(85.6 / 4),
          height: mmToPx(50),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 2,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        },
        {
          id: 'photo-3',
          type: 'photo',
          x: PHOTO_PADDING * 3 + mmToPx(85.6 / 4 * 2),
          y: PHOTO_PADDING,
          width: mmToPx(85.6 / 4),
          height: mmToPx(50),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 3,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        },
        {
          id: 'photo-4',
          type: 'photo',
          x: PHOTO_PADDING * 4 + mmToPx(85.6 / 4 * 3),
          y: PHOTO_PADDING,
          width: mmToPx(85.6 / 4),
          height: mmToPx(50),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 4,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        },
        {
          id: 'brand-text',
          type: 'text',
          x: mmToPx(5),
          y: mmToPx(70),
          width: mmToPx(90),
          height: mmToPx(10),
          rotation: 0,
          opacity: 1,
          zIndex: 2,
          locked: false,
          visible: true,
          props: {
            content: 'YOUR BRAND HERE',
            fontFamily: 'Inter',
            fontSize: mmToPx(4),
            fontWeight: 700,
            color: '#000000',
            textAlign: 'center',
            lineHeight: 1.2
          }
        }
      ]
    }
  },
  {
    id: 'four-poses-double-strip-vertical',
    name: '四姿双条垂直',
    description: '4张照片2列排列',
    thumbnail: '/images/templates/preset-2.webp',
    layout: {
      paperSize: BASE_PAPER_SIZE,
      resolution: BASE_RESOLUTION,
      orientation: 'portrait',
      background: { type: 'color', value: '#ffffff' },
      elements: [
        {
          id: 'photo-1',
          type: 'photo',
          x: PHOTO_PADDING,
          y: PHOTO_PADDING,
          width: mmToPx(45),
          height: mmToPx(65),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 1,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        },
        {
          id: 'photo-2',
          type: 'photo',
          x: PHOTO_PADDING * 2 + mmToPx(45),
          y: PHOTO_PADDING,
          width: mmToPx(45),
          height: mmToPx(65),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 2,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        },
        {
          id: 'photo-3',
          type: 'photo',
          x: PHOTO_PADDING,
          y: PHOTO_PADDING * 2 + mmToPx(65),
          width: mmToPx(45),
          height: mmToPx(65),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 3,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        },
        {
          id: 'photo-4',
          type: 'photo',
          x: PHOTO_PADDING * 2 + mmToPx(45),
          y: PHOTO_PADDING * 2 + mmToPx(65),
          width: mmToPx(45),
          height: mmToPx(65),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 4,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        }
      ]
    }
  },
  {
    id: 'four-poses-single-strip-vertical',
    name: '四姿单条垂直',
    description: '4张照片垂直排列',
    thumbnail: '/images/templates/preset-3.webp',
    layout: {
      paperSize: BASE_PAPER_SIZE,
      resolution: BASE_RESOLUTION,
      orientation: 'portrait',
      background: { type: 'color', value: '#ffffff' },
      elements: [
        {
          id: 'photo-1',
          type: 'photo',
          x: mmToPx(10),
          y: mmToPx(10),
          width: mmToPx(80),
          height: mmToPx(32),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 1,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        },
        {
          id: 'photo-2',
          type: 'photo',
          x: mmToPx(10),
          y: mmToPx(10 + 32 + 5),
          width: mmToPx(80),
          height: mmToPx(32),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 2,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        },
        {
          id: 'photo-3',
          type: 'photo',
          x: mmToPx(10),
          y: mmToPx(10 + 32*2 + 5*2),
          width: mmToPx(80),
          height: mmToPx(32),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 3,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        },
        {
          id: 'photo-4',
          type: 'photo',
          x: mmToPx(10),
          y: mmToPx(10 + 32*3 + 5*3),
          width: mmToPx(80),
          height: mmToPx(32),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 4,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        },
        {
          id: 'footer-text',
          type: 'text',
          x: mmToPx(10),
          y: mmToPx(10 + 32*4 + 5*4),
          width: mmToPx(80),
          height: mmToPx(8),
          rotation: 0,
          opacity: 1,
          zIndex: 2,
          locked: false,
          visible: true,
          props: {
            content: 'Powered by PhotoBooth',
            fontFamily: 'Inter',
            fontSize: mmToPx(3),
            fontWeight: 400,
            color: '#666666',
            textAlign: 'center',
            lineHeight: 1.2
          }
        }
      ]
    }
  },
  {
    id: 'one-large-three-small',
    name: '一大三小',
    description: '1张大图 + 3张小图水平排列',
    thumbnail: '/images/templates/preset-4.webp',
    layout: {
      paperSize: BASE_PAPER_SIZE,
      resolution: BASE_RESOLUTION,
      orientation: 'landscape',
      background: { type: 'color', value: '#ffffff' },
      elements: [
        {
          id: 'photo-1-large',
          type: 'photo',
          x: PHOTO_PADDING,
          y: PHOTO_PADDING,
          width: mmToPx(70),
          height: mmToPx(90),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 1,
            cropMode: 'fill',
            borderRadius: mmToPx(3)
          }
        },
        {
          id: 'photo-2-small',
          type: 'photo',
          x: PHOTO_PADDING * 2 + mmToPx(70),
          y: PHOTO_PADDING,
          width: mmToPx(55),
          height: mmToPx(28),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 2,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        },
        {
          id: 'photo-3-small',
          type: 'photo',
          x: PHOTO_PADDING * 2 + mmToPx(70),
          y: PHOTO_PADDING * 2 + mmToPx(28),
          width: mmToPx(55),
          height: mmToPx(28),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 3,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        },
        {
          id: 'photo-4-small',
          type: 'photo',
          x: PHOTO_PADDING * 2 + mmToPx(70),
          y: PHOTO_PADDING * 3 + mmToPx(28 * 2),
          width: mmToPx(55),
          height: mmToPx(28),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 4,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        }
      ]
    }
  },
  {
    id: 'one-pose-double-strip-horizontal',
    name: '一姿双条水平',
    description: '1张照片重复2条水平排列',
    thumbnail: '/images/templates/preset-5.webp',
    layout: {
      paperSize: BASE_PAPER_SIZE,
      resolution: BASE_RESOLUTION,
      orientation: 'landscape',
      background: { type: 'color', value: '#ffffff' },
      elements: [
        {
          id: 'photo-1-left',
          type: 'photo',
          x: PHOTO_PADDING,
          y: PHOTO_PADDING,
          width: mmToPx(47),
          height: mmToPx(90),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 1,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        },
        {
          id: 'photo-1-right',
          type: 'photo',
          x: PHOTO_PADDING * 2 + mmToPx(47),
          y: PHOTO_PADDING,
          width: mmToPx(47),
          height: mmToPx(90),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 1,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        }
      ]
    }
  },
  {
    id: 'classic-2x6-photo-strip',
    name: '经典2x6照片条',
    description: '经典4张照片垂直排列，带品牌区域',
    thumbnail: '/images/templates/preset-11.webp',
    layout: {
      paperSize: { width: 50.8, height: 152.4 }, // 2x6英寸
      resolution: BASE_RESOLUTION,
      orientation: 'portrait',
      background: { type: 'color', value: '#ffffff' },
      elements: [
        {
          id: 'photo-1',
          type: 'photo',
          x: mmToPx(3),
          y: mmToPx(3),
          width: mmToPx(44.8),
          height: mmToPx(32),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 1,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        },
        {
          id: 'photo-2',
          type: 'photo',
          x: mmToPx(3),
          y: mmToPx(3 + 32 + 3),
          width: mmToPx(44.8),
          height: mmToPx(32),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 2,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        },
        {
          id: 'photo-3',
          type: 'photo',
          x: mmToPx(3),
          y: mmToPx(3 + 32*2 + 3*2),
          width: mmToPx(44.8),
          height: mmToPx(32),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 3,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        },
        {
          id: 'photo-4',
          type: 'photo',
          x: mmToPx(3),
          y: mmToPx(3 + 32*3 + 3*3),
          width: mmToPx(44.8),
          height: mmToPx(32),
          rotation: 0,
          opacity: 1,
          zIndex: 1,
          locked: false,
          visible: true,
          props: {
            photoNumber: 4,
            cropMode: 'fill',
            borderRadius: mmToPx(2)
          }
        },
        {
          id: 'brand-area',
          type: 'text',
          x: mmToPx(3),
          y: mmToPx(3 + 32*4 + 3*4),
          width: mmToPx(44.8),
          height: mmToPx(12),
          rotation: 0,
          opacity: 1,
          zIndex: 2,
          locked: false,
          visible: true,
          props: {
            content: 'YOUR LOGO HERE',
            fontFamily: 'Inter',
            fontSize: mmToPx(5),
            fontWeight: 700,
            color: '#000000',
            textAlign: 'center',
            lineHeight: 1.2
          }
        },
        {
          id: 'date-text',
          type: 'date',
          x: mmToPx(3),
          y: mmToPx(3 + 32*4 + 3*4 + 10),
          width: mmToPx(44.8),
          height: mmToPx(5),
          rotation: 0,
          opacity: 1,
          zIndex: 2,
          locked: false,
          visible: true,
          props: {
            format: 'YYYY-MM-DD'
          }
        }
      ]
    }
  }
];