# UI/UX与响应式优化 - 迭代提示词

## 目标
修复当前前端的响应式适配问题，补全可访问性(a11y)支持，实现屏幕方向切换、虚拟键盘集成、锁屏模式和客界面文本全自定义。

## 当前状态
- 所有三栏布局屏幕(Camera/Beauty/TemplateEditor)宽度硬编码，仅桌面可用
- 可访问性仅有少量aria-label，无键盘导航
- `SettingsScreen.tsx` 有基础设置项但缺少大量可配置项
- 无锁屏模式

## 需要实现的功能

### 12.1 响应式布局适配

#### 全局断点系统
**新建文件:** `frontend/src/app/hooks/useResponsive.ts`

```typescript
type Breakpoint = 'mobile' | 'tablet' | 'desktop';

function useResponsive(): {
  breakpoint: Breakpoint;
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  orientation: 'portrait' | 'landscape';
}
```

断点定义:
- `mobile`: < 768px (手机竖屏)
- `tablet`: 768px - 1024px (平板)
- `desktop`: > 1024px (桌面)

#### 修改所有屏幕适配
**修改文件:** 所有 Screen 组件

1. CameraScreen 适配:
   - 桌面: 三栏(左侧照片条 + 中间取景器 + 右侧参数面板)
   - 平板: 两栏(左侧照片条折叠 + 中间取景器 + 右侧面板折叠)
   - 手机: 单栏(全屏取景器 + 底部浮动控制栏)

2. BeautyScreen 适配:
   - 桌面: 三栏(工具 + 预览 + 面板)
   - 移动端: 单栏(预览全屏 + 底部抽屉式面板)

3. TemplateEditorScreen 适配:
   - 桌面: 三栏完整布局
   - 移动端: 仅画布 + 浮动工具栏(不适合精密编辑，有提示)

4. 通用组件适配:
   - `GlassCard`: 移动端减小padding和圆角
   - `GlowBtn`: 移动端增大触摸区域(至少44×44px)
   - 导航: 移动端底部Tab栏(已实现但需调优)

### 12.2 可访问性(a11y)增强

#### 全局可访问性改进

1. 焦点管理:
   - 所有可交互元素添加可见焦点样式
   - Tab键导航顺序合理
   - 模态框打开时聚焦到模态框，关闭时恢复焦点

2. ARIA属性:
   ```tsx
   // 所有按钮
   <button aria-label="拍照" aria-describedby="shutter-help">...</button>
   
   // 滑块
   <input type="range" aria-valuemin={0} aria-valuemax={100} aria-valuenow={value}
     aria-label="磨皮强度" />
   
   // 图片
   <img alt="最近拍摄的第1张照片" />
   
   // 动态内容区域
   <div aria-live="polite" aria-atomic="true">{statusMessage}</div>
   ```

3. 屏幕阅读器支持:
   - 使用正确的语义HTML(header/main/nav/aside)
   - 自定义组件的role属性
   - 状态变更的live region通知

4. 键盘快捷键:
   ```
   Space/Enter: 拍照
   Esc: 取消/返回
   Tab: 下一元素
   Shift+Tab: 上一元素
   Arrow Keys: 切换照片/选项
   Ctrl+Z: 撤销(模板编辑器)
   Ctrl+Y: 重做(模板编辑器)
   Delete: 删除选中元素
   ```

### 12.3 屏幕方向切换

**修改文件:** `frontend/src/app/App.tsx`

1. 方向检测:
   ```typescript
   useEffect(() => {
     const mql = window.matchMedia('(orientation: portrait)');
     setOrientation(mql.matches ? 'portrait' : 'landscape');
     mql.addEventListener('change', handleOrientationChange);
   }, []);
   ```

2. 方向变化时适配布局:
   - 横屏: 默认布局
   - 竖屏: 拍照界面自动调整为全屏+浮动按钮

3. 方向锁定(可配置):
   ```typescript
   if (screen.orientation?.lock) {
     await screen.orientation.lock('landscape'); // 拍照亭默认横屏
   }
   ```

### 12.4 虚拟键盘集成

**新建文件:** `frontend/src/app/components/VirtualKeyboard.tsx`

1. 虚拟键盘组件:
   - 用于触摸屏没有物理键盘的场景
   - 显示/隐藏切换
   - 仅输入文本时显示
   - 可配置风格(Windows 10风格/自定义)

2. 使用场景:
   - 邮件地址输入(分享屏幕)
   - 手机号输入(短信分享)
   - 调查问卷文本输入
   - 管理员登录

### 12.5 锁屏模式

**新建文件:** `frontend/src/app/screens/LockScreen.tsx`

1. 锁屏功能:
   ```
   ┌────────────────────────────┐
   │                            │
   │    [自定义背景图片/文字]     │
   │                            │
   │   拍照亭已锁定               │
   │                            │
   │   [PIN输入框 ****]         │
   │   [数字键盘 1-9]            │
   │                            │
   └────────────────────────────┘
   ```

2. 功能:
   - 自定义锁屏背景图
   - 自定义锁屏文字
   - PIN码解锁(4-6位)
   - 自动锁屏定时器(可配置)
   - 手动锁定按钮
   - 仅显示背景图模式

3. PIN管理:
   - 管理员设置PIN
   - PIN验证API(后端)
   - 连续错误锁定(5次错误 → 锁定30秒)

#### 锁屏API:
```
PUT    /api/v1/settings/lock-screen    → 更新锁屏设置
POST   /api/v1/auth/unlock             → PIN解锁验证
GET    /api/v1/settings/lock-screen    → 获取锁屏设置
```

### 12.6 客界面文本自定义

#### 后端: 显示文本配置
**修改文件:** `backend/app/models/models.py` (或新建 display_texts.py)

```python
class DisplayTexts(BaseModel):
    """所有面向宾客的界面文本"""
    # 开始屏幕
    touch_to_start: str = "触摸开始"
    start_session: str = "开始拍照"
    photo_mode: str = "照片"
    gif_mode: str = "GIF"
    boomerang_mode: str = "回旋镖"
    video_mode: str = "视频"
    
    # 操作
    select_background: str = "选择背景"
    select_effect: str = "选择效果"
    print: str = "打印"
    email: str = "电子邮件"
    sms: str = "短信"
    scan_qr: str = "扫码下载"
    done: str = "完成"
    retake: str = "重拍"
    
    # 分享
    enter_email: str = "输入邮箱地址"
    send_email: str = "发送邮件"
    enter_phone: str = "输入手机号码"
    send_sms: str = "发送短信"
    
    # 签名
    sign_here: str = "请在下方签名"
    clear_signature: str = "清除签名"
    accept_signature: str = "确认签名"
    
    # 免责声明
    i_agree: str = "我已阅读并同意"
    disagree_cancel: str = "不同意，取消"
```

#### 后端API:
```
GET    /api/v1/settings/display-texts/{event_id} → 获取显示文本配置
PUT    /api/v1/settings/display-texts/{event_id} → 更新显示文本配置
```

#### 前端: 设置页面扩展
**修改文件:** `frontend/src/app/screens/SettingsScreen.tsx`

添加显示文本配置区域:
- 所有可自定义文本的列表
- 实时预览
- 重置为默认值
- 按屏幕分组(开始/拍摄/分享/签名)

### 12.7 视觉效果优化

1. 修复全局brightness滤镜问题:
   **修改文件:** `frontend/src/app/App.tsx:193`
   - 将滤镜从全局div移到仅背景元素
   - 确保SVG图标不受影响

2. 暗色模式优化:
   - 当前深色主题一致性好
   - 添加亮色主题选项(可选)

3. 动画性能优化:
   - 使用 `will-change` 提示浏览器
   - 仅对 `transform` 和 `opacity` 做动画
   - 使用 `layoutId` 做共享布局动画(已实施)

### 12.8 字体与国际化

1. 多语言系统:
   **新建文件:** `frontend/src/app/i18n/`
   - 使用 `i18next` + `react-i18next`
   - 提取所有硬编码中文字符串
   - 支持中文/英文/日文/韩文(至少中英)
   - 当前已有简体中文文本需提取为翻译文件

2. 字体优化:
   - 确保中文字体子集化(减少加载量)
   - 使用 `font-display: swap` 防止FOIT

## 验收标准
1. 手机横屏/竖屏下所有核心页面(拍照/美颜/打印/分享)正常显示和操作
2. Tab键可导航所有可交互元素，焦点样式可见
3. 屏幕阅读器(NVDA/VoiceOver)可正确读出操作提示
4. 虚拟键盘在触摸屏上能正常输入
5. 锁屏界面美观，PIN密码正确解锁/错误拒绝
6. 客界面所有文本可在设置中自定义
7. 语言切换(中→英)后所有界面一致显示目标语言
8. Lighthouse a11y评分 > 85

## 技术选型建议
- 响应式: Tailwind响应式断点 + useResponsive hook
- 国际化: `i18next` + `react-i18next`
- 虚拟键盘: `simple-keyboard` (轻量级)
- a11y检查: `@axe-core/react` + eslint-plugin-jsx-a11y
