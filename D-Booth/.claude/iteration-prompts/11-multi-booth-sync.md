# 多展位管理与同步 - 迭代提示词

## 目标
实现多台拍照亭设备之间的模板、设置和资产的云端同步，支持统一管理控制台查看所有展位状态和活动数据。

## 当前状态
- `team_repository.py` 有多团队支持
- `event_service.py` 有跨团队事件查询
- 但无任何多展位同步功能
- dslrBooth 的 fotoShare Cloud 提供了完整的多展位同步

## 需要实现的功能

### 11.1 后端: 展位注册与管理
**新建文件:** `backend/app/services/booth_service.py`

1. 展位模型:
   ```python
   class Booth(BaseModel):
       id: UUID
       team_id: UUID
       name: str                    # "主舞台拍照亭"
       device_id: str               # 设备唯一标识
       status: BoothStatus          # ONLINE/OFFLINE/BUSY/ERROR
       version: str                 # 软件版本
       last_heartbeat: datetime
       ip_address: str
       os_info: str
       current_event_id: Optional[UUID]
       config_hash: str             # 当前配置哈希
   ```

2. 展位心跳:
   ```python
   async def heartbeat(booth_id: UUID) -> None:
       # 更新 last_heartbeat
       # 超过60秒无心跳 → 标记为OFFLINE
   ```

#### 展位API:
```
POST   /api/v1/booths/register       → 注册新展位
POST   /api/v1/booths/{id}/heartbeat → 展位心跳(30秒间隔)
GET    /api/v1/booths                → 团队所有展位状态
GET    /api/v1/booths/{id}           → 展位详情
PUT    /api/v1/booths/{id}           → 更新展位配置
DELETE /api/v1/booths/{id}           → 注销展位
```

### 11.2 后端: 配置同步服务
**新建文件:** `backend/app/services/sync_service.py`

1. 同步范围:
   - 模板(Template)
   - 事件设置(Event settings)
   - 绿幕设置(GreenScreen settings)
   - 道具(Props)
   - 水印(Watermark)
   - 全局设置(部分)

2. 同步机制:
   ```python
   async def get_sync_state(team_id: UUID, booth_id: UUID) -> SyncState:
       """返回当前展位与云端配置的差异"""
       return SyncState(
           templates_hash='abc123',
           settings_hash='def456',
           need_sync_templates=3,   # 需要同步的模板数
           need_sync_settings=2,     # 需要同步的设置数
       )
   
   async def sync_booth(booth_id: UUID, sync_type: str) -> dict:
       """将云端的配置推送到指定展位"""
   ```

3. 冲突解决:
   - 最后写入者胜出(Last Write Wins)
   - 基于内容哈希的增量同步
   - 同步日志记录

#### 同步API:
```
GET    /api/v1/sync/state/{booth_id}        → 获取同步状态
POST   /api/v1/sync/push/{booth_id}         → 推送配置到展位
POST   /api/v1/sync/pull/{booth_id}         → 从展位拉取配置
GET    /api/v1/sync/log/{team_id}           → 同步历史日志
```

### 11.3 后端: 统一数据看板
**修改文件:** `backend/app/services/analytics_service.py`

1. 多展位聚合统计:
   ```python
   async def get_multi_booth_stats(team_id: UUID) -> MultiBoothStats:
       """聚合所有展位的数据"""
       return MultiBoothStats(
           total_sessions=...,
           total_photos=...,
           total_prints=...,
           total_shares=...,
           active_booths=...,
           by_booth=[              # 每台展位的详细数据
               BoothStats(booth_id=..., sessions=..., photos=...),
           ]
       )
   ```

### 11.4 前端: 展位管理控制台
**新建文件:** `frontend/src/app/screens/BoothManagerScreen.tsx`

1. 仪表盘:
   ```
   ┌──────────────────────────────────────────┐
   │  展位管理                    [+添加展位]  │
   ├──────────────────────────────────────────┤
   │  ● 主舞台拍照亭    ONLINE   192.168.1.10 │
   │  ● VIP拍照亭       ONLINE   192.168.1.11 │
   │  ○ 户外拍照亭      OFFLINE  --          │
   │  ⚠ 入口拍照亭      ERROR   192.168.1.13 │
   ├──────────────────────────────────────────┤
   │  今日统计                                │
   │  总会话: 1,248  总照片: 5,632            │
   │  总打印: 892    总分享: 456              │
   └──────────────────────────────────────────┘
   ```

2. 展位详情:
   - 实时照片计数
   - 打印队列状态
   - 存储空间使用
   - 错误日志
   - 配置同步状态

3. 操作:
   - 远程更新配置
   - 同步模板
   - 发送消息到展位屏幕
   - 远程锁定/解锁展位

### 11.5 前端: 数据看板增强
**修改文件:** `frontend/src/app/screens/AnalyticsScreen.tsx`

添加:
- 展位选择器(全部/单个)
- 展位间数据对比图表
- 实时数据刷新(30秒间隔)

## 验收标准
1. 多台展位设备能注册到同一团队
2. 展位在线状态实时显示(心跳30秒)
3. 云端修改模板后，在线展位自动同步(<1分钟)
4. 展位离线期间修改云端配置，恢复连接后自动同步
5. 统一看板能聚合所有展位数据
6. 管理员可远程锁定/解锁任意展位
7. 同步日志可追溯每次变更

## 技术选型建议
- 实时通信: WebSocket (FastAPI原生支持)
- 配置哈希: SHA256
- 增量同步: 基于内容哈希的diff
