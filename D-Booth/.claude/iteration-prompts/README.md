# 咏彩 AI 拍照亭 (D-Booth) 迭代升级索引

基于 dslrBooth Professional 7.47.1112.1 的全面审查，按15个板块生成详细迭代提示词。

## 优先级说明
- **P0 (红色)**: 核心商业闭环，缺一不可上线
- **P1 (橙色)**: 关键差异化功能，增强竞争力
- **P2 (蓝色)**: 体验提升，锦上添花
- **P3 (灰色)**: 运营/管理增强

## 迭代板块总览

### P0 - 核心商业闭环
| 编号 | 板块 | 文件 | 工作量 | 依赖 |
|------|------|------|--------|------|
| 01 | 物理相机SDK集成 | [01-camera-sdk-integration.md](./01-camera-sdk-integration.md) | 大 | 无 |
| 02 | 物理打印机集成 | [02-printer-integration.md](./02-printer-integration.md) | 大 | 04(模板渲染) |
| 03 | AI美颜真实集成 | [03-ai-beauty-filter.md](./03-ai-beauty-filter.md) | 中 | 无 |

### P1 - 核心差异化功能
| 编号 | 板块 | 文件 | 工作量 | 依赖 |
|------|------|------|--------|------|
| 04 | 模板编辑器完善 | [04-template-editor.md](./04-template-editor.md) | 大 | 无 |
| 05 | 绿幕与背景替换 | [05-green-screen.md](./05-green-screen.md) | 中 | 01(DSLR) |
| 06 | 高级拍照模式 | [06-advanced-capture-modes.md](./06-advanced-capture-modes.md) | 中 | 01(DSLR) |
| 07 | 数字道具/贴纸系统 | [07-digital-props-stickers.md](./07-digital-props-stickers.md) | 小 | 03(美颜) |

### P2 - 体验提升
| 编号 | 板块 | 文件 | 工作量 | 依赖 |
|------|------|------|--------|------|
| 08 | 来宾互动系统 | [08-guest-interaction.md](./08-guest-interaction.md) | 中 | 无 |
| 09 | 分享与社交集成 | [09-sharing-social.md](./09-sharing-social.md) | 中 | 无 |
| 10 | 性能与离线优化 | [10-performance-offline.md](./10-performance-offline.md) | 中 | 无 |
| 12 | UI/UX与响应式 | [12-ui-ux-responsive.md](./12-ui-ux-responsive.md) | 中 | 无 |
| 13 | 水印与LUT滤镜 | [13-watermark-lut-sharpen.md](./13-watermark-lut-sharpen.md) | 小 | 02(打印锐化) |
| 14 | 虚拟助手语音引导 | [14-virtual-attendant.md](./14-virtual-attendant.md) | 小 | 无 |

### P3 - 运营管理
| 编号 | 板块 | 文件 | 工作量 | 依赖 |
|------|------|------|--------|------|
| 11 | 多展位管理与同步 | [11-multi-booth-sync.md](./11-multi-booth-sync.md) | 大 | 无 |
| 15 | API/触发器/外部集成 | [15-api-triggers-external.md](./15-api-triggers-external.md) | 中 | 无 |

## 使用方式

将对应的 `.md` 文件内容作为提示词传递给子agent，即可启动该板块的迭代开发。

示例:
```
请根据 D:\安装包归档\咏彩booth\D-Booth\.claude\iteration-prompts\01-camera-sdk-integration.md 
中的迭代提示词，完成物理相机SDK集成的开发工作。
```

## 迭代顺序建议

```
第1轮 (P0核心):  01相机SDK → 03AI美颜 → 04模板编辑器 → 02打印机
第2轮 (P1差异):  05绿幕 → 06高级模式 → 07贴纸道具
第3轮 (P2体验):  08来宾互动 → 09分享 → 10性能 → 12UI → 13水印 → 14语音
第4轮 (P3运营):  11多展位 → 15触发器
```
