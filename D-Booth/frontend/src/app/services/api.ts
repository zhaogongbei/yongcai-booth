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

  // 同步展位配置
  syncBooth: async (boothId: string) => {
    const token = tokenStorage.access || '';
    return pushConfig(boothId, 'current-team-id', token);
  },
};

export { boothApi };
