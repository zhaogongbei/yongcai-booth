import { getTeamBooths, updateBooth, pushConfig, tokenStorage } from '../lib/api';

// boothApi facade - Booth information
const boothApi = {
  // 获取团队所有展位
  getTeamBooths: async (teamId: string) => {
    const token = tokenStorage.access || '';
    return getTeamBooths(teamId, token);
  },

  // 更新展位状态
  updateBooth: async (boothId: string, data: Record<string, unknown>) => {
    const token = tokenStorage.access || '';
    return updateBooth(boothId, token, data);
  },

  // 同步展位配置（推送配置到展位）。teamId 必须是展位所属团队的真实 ID，
  // 后端 /sync/push/{boothId} 会通过 check_team_member 校验调用者是否该团队成员。
  syncBooth: async (boothId: string, teamId: string) => {
    const token = tokenStorage.access || '';
    return pushConfig(boothId, teamId, token);
  },
};

export { boothApi };
