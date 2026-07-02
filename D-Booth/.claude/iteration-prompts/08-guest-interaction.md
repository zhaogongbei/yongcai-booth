# 来宾互动系统 - 迭代提示词

## 目标
实现来宾签名采集、调查问卷、免责声明确认三大互动功能，增强拍照亭的互动性和合规性。

## 当前状态
- 项目完全无此三项功能
- dslrBooth 有完整的调查问卷、签名采集、免责声明系统

## 需要实现的功能

### 8.1 来宾签名采集

#### 后端: 签名API
**新建文件:** `backend/app/api/v1/signatures.py`

```
POST   /api/v1/signatures             → 上传签名PNG + 关联到Session
GET    /api/v1/signatures/{session_id} → 获取会话的签名
DELETE /api/v1/signatures/{id}        → 删除签名
```

签名存储:
- 透明背景PNG格式
- 存储到R2
- 关联到PhotoSession

#### 前端: 签名采集页面
**新建文件:** `frontend/src/app/screens/SignatureScreen.tsx`

1. Canvas签名板:
   - 使用HTML5 Canvas
   - 触摸/鼠标绘制
   - 笔触样式(颜色/粗细)
   - 清除按钮
   - 确认/重签

2. UI布局:
   ```
   [请在此区域签名]
   ┌──────────────────┐
   │                  │
   │   (Canvas画板)   │
   │                  │
   └──────────────────┘
   [清除]        [确认签名]
   ```

3. 签名导出:
   - Canvas.toBlob() → 上传到后端
   - 保存为透明PNG
   - 签名可嵌入打印模板(签名占位符)

### 8.2 调查问卷系统

#### 后端: 调查模型和服务
**新建文件:** `backend/app/models/survey.py`

```python
class Survey(BaseModel):
    id: UUID
    event_id: UUID
    enabled: bool
    title: str
    questions: List[SurveyQuestion]

class SurveyQuestion(BaseModel):
    id: UUID
    type: Literal["text_short", "text_long", "multiple_choice", "rating"]
    text: str                     # 问题文本
    required: bool
    options: List[str]            # 选择题选项(空=文本题)
    order: int

class SurveyResponse(BaseModel):
    id: UUID
    session_id: UUID
    question_id: UUID
    answer: str                   # 文本答案或选项值
```

#### 后端: 调查API
**新建文件:** `backend/app/api/v1/surveys.py`

```
GET    /api/v1/surveys/event/{event_id}     → 获取事件调查配置
PUT    /api/v1/surveys/event/{event_id}     → 更新事件调查配置
POST   /api/v1/surveys/responses             → 提交调查回答(关联Session)
GET    /api/v1/surveys/responses/{session_id} → 查看某次会话的回答
GET    /api/v1/surveys/responses/export/{event_id} → 导出CSV
```

#### 前端: 调查问卷页面(来宾)
**新建文件:** `frontend/src/app/screens/SurveyScreen.tsx`

1. 布局:
   ```
   [活动主题] 调查问卷
   
   1. 您是如何了解到本次活动的?
      ○ 社交媒体  ○ 朋友推荐  ○ 路过看到  ○ 其他
   
   2. 请对我们的服务评分:
      ★★★★☆
   
   3. 有什么想对我们说的?
      ┌─────────────────────┐
      │                     │
      └─────────────────────┘
   
   [跳过]              [提交]
   ```

2. 问题类型渲染:
   - text_short: 单行输入框
   - text_long: 多行文本框
   - multiple_choice: 单选/多选按钮
   - rating: 星级评分(1-5星)

3. 验证:
   - 必填问题必须回答
   - 提交前显示摘要确认

#### 前端: 调查配置页面(管理员)
**新建文件:** `frontend/src/app/screens/SurveyConfigScreen.tsx`

1. 问题编辑器:
   - 添加/删除/排序问题
   - 设置问题类型、文本、必填
   - 选择题添加/删除选项
   - 预览

2. 回答查看:
   - 表格展示所有回答
   - 按问题筛选
   - 导出CSV

### 8.3 免责声明确认

#### 后端: 免责声明管理
**新建文件:** `backend/app/services/disclaimer_service.py`

```python
class Disclaimer(BaseModel):
    id: UUID
    event_id: UUID
    enabled: bool
    title: str     # "拍照前请阅读并同意"
    text: str       # 完整法律文本
    require_signature: bool  # 是否需要签名确认
```

#### 后端: 免责声明API
**新建文件:** `backend/app/api/v1/disclaimers.py`

```
GET    /api/v1/disclaimers/event/{event_id}      → 获取事件免责声明
PUT    /api/v1/disclaimers/event/{event_id}      → 更新事件免责声明
POST   /api/v1/disclaimers/accept                 → 来宾确认免责声明(关联Session)
GET    /api/v1/disclaimers/acceptances/{event_id} → 查看所有已确认记录
```

#### 前端: 免责声明页面(来宾)
**新建文件:** `frontend/src/app/screens/DisclaimerScreen.tsx`

1. 布局:
   ```
   ⚠️ 拍照前请阅读并同意
   
   [可滚动的法律文本区域]
   [肖像权/隐私权/使用权条款]
   
   [✓] 我已阅读并同意上述条款
   
   [取消]          [同意并开始拍照]
   ```

2. 行为:
   - 显示在拍照流程之前
   - 必须勾选同意才能继续
   - 如果是首次访问活动，显示此页面
   - 确认后记录到Session

### 8.4 流程集成

#### 修改拍照流程
**修改文件:** `frontend/src/app/stores/useCaptureFlow.tsx`

添加流程状态:
```typescript
type CaptureStep = 'disclaimer' | 'survey' | 'capture' | 'signature' | 'share_print';
```

流程顺序:
1. `disclaimer` - 免责声明(如启用)
2. `survey` - 调查问卷(如启用，可配置在拍照前/后)
3. `capture` - 拍照
4. `signature` - 签名(如启用)
5. `share_print` - 分享/打印

#### 修改App.tsx
**修改文件:** `frontend/src/app/App.tsx`

在路由中添加新屏幕:
```typescript
case 'signature': return <SignatureScreen />;
case 'survey': return <SurveyScreen />;
case 'disclaimer': return <DisclaimerScreen />;
```

## 验收标准
1. 签名板支持触摸和鼠标输入，绘制流畅
2. 签名保存为透明PNG，可嵌入打印模板
3. 调查问卷支持4种问题类型(简答/长答/选择/评分)
4. 管理员可自由添加/删除/排序问题
5. 调查回答可导出CSV
6. 免责声明在拍照前显示，必须勾选同意
7. 免责声明确认记录可追溯
8. 整个来宾流程(免责声明→拍照→签名→分享/打印)顺畅完整

## 技术选型建议
- 签名板: HTML5 Canvas + Pointer Events API
- 名板笔触: 可变宽度笔触(模拟真实签名)
- 调查导出: csv模块(标准库)
