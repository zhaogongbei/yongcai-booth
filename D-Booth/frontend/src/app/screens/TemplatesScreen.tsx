import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, Check, Copy, Heart, Star, Building, Trophy, Sparkles, Grid3X3, Search, Filter, Plus, RefreshCw, LayoutTemplate, Trash2, ImagePlus } from "lucide-react";
import { motion } from "motion/react";
import { GlassCard } from "../components/GlassCard";
import { NeonBadge } from "../components/NeonBadge";
import { GlowBtn } from "../components/GlowBtn";
import { TemplateThumbnailPreview } from "../components/TemplateThumbnailPreview";
import { showToast } from "../stores/useToast";
import { useSettings } from "../stores/useSettings";
import { useCaptureFlow } from "../stores/useCaptureFlow";
import { JUST_SAVED_TEMPLATE_SESSION_KEY, SELECTED_TEMPLATE_SESSION_KEY, TEMPLATE_EDITOR_UPLOAD_BACKGROUND_SESSION_KEY } from "../constants/templateNavigation";
import { TEMPLATE_EDITOR_QUICK_LAYOUT_SESSION_KEY } from "../constants/printLayoutPresets";
import { createTemplate, deleteTemplate, duplicateTemplate, getMyTeams, getTemplateCatalog, getTemplates, tokenStorage, type TemplateCatalogResponse, type TemplateResponse } from "../../lib/api";
import type { Screen } from "../types";
import type { TemplateLayout } from "../types/template";

type MarketTemplate = {
  template: TemplateCatalogResponse;
  layout: TemplateLayout;
  ratio: string;
  feature: "推荐" | "热门" | "公开";
  category: string;
  style: string;
  scene: string;
  accentColor: string;
};

function isTemplateLayout(value: unknown): value is TemplateLayout {
  const layout = value as Partial<TemplateLayout>;
  return Boolean(
    layout &&
    typeof layout === "object" &&
    layout.paperSize &&
    typeof layout.resolution === "number" &&
    layout.background &&
    Array.isArray(layout.elements)
  );
}

function getTemplateRatioLabel(layout: TemplateLayout): string {
  const shortSide = Math.min(layout.paperSize.width, layout.paperSize.height);
  const longSide = Math.max(layout.paperSize.width, layout.paperSize.height);
  const ratio = longSide / shortSide;
  if (Math.abs(ratio - 3) < 0.08) return "2×6";
  if (Math.abs(ratio - 1.5) < 0.08) return "4×6";
  if (Math.abs(ratio - 4 / 3) < 0.08) return "6×8";
  return "其他";
}

function toMarketTemplate(template: TemplateCatalogResponse): MarketTemplate | null {
  if (!isTemplateLayout(template.layers)) return null;

  const metadata = template.layers.catalog;
  const backgroundColor = template.layers.background.type === "color"
    && /^#[0-9a-f]{3,8}$/i.test(template.layers.background.value)
    ? template.layers.background.value
    : "#8b5cf6";

  return {
    template,
    layout: template.layers,
    ratio: getTemplateRatioLabel(template.layers),
    feature: metadata?.feature === "recommended"
      ? "推荐"
      : metadata?.feature === "popular" ? "热门" : "公开",
    category: metadata?.category?.trim() || "自定义",
    style: metadata?.style?.trim() || "其他",
    scene: metadata?.scene?.trim() || "其他",
    accentColor: metadata?.accentColor && /^#[0-9a-f]{3,8}$/i.test(metadata.accentColor)
      ? metadata.accentColor
      : backgroundColor,
  };
}

export function TemplatesScreen({ navigate }: { navigate: (s: Screen) => void }) {
  const { currentEvent } = useSettings();
  const {
    activePrintTemplate,
    authToken,
    photos,
    teamId: captureTeamId,
    setActivePrintTemplate,
    templateSelectionReturnScreen,
    setTemplateSelectionReturnScreen,
  } = useCaptureFlow();
  const [activeCategory, setActiveCategory] = useState("全部");
  const [searchTerm, setSearchTerm] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedColor, setSelectedColor] = useState<string | null>(null);
  const [selectedRatio, setSelectedRatio] = useState("全部");
  const [selectedStyle, setSelectedStyle] = useState("全部");
  const [selectedScene, setSelectedScene] = useState("全部");
  const [savedTemplates, setSavedTemplates] = useState<TemplateResponse[]>([]);
  const [marketTemplates, setMarketTemplates] = useState<TemplateCatalogResponse[]>([]);
  const [savedTemplatesLoading, setSavedTemplatesLoading] = useState(false);
  const [savedTemplatesError, setSavedTemplatesError] = useState<string | null>(null);
  const [operatingTemplateId, setOperatingTemplateId] = useState<string | null>(null);
  const [recentlySavedTemplateId, setRecentlySavedTemplateId] = useState<string | null>(null);

  const categories = ["全部", "婚礼", "生日", "企业", "毕业", "节日", "派对", "自定义"];
  const parsedMarketTemplates = useMemo(
    () => marketTemplates
      .map(toMarketTemplate)
      .filter((template): template is MarketTemplate => template !== null),
    [marketTemplates]
  );

  const filterMarketTemplate = (template: MarketTemplate) => {
    const normalizedSearchTerm = searchTerm.trim().toLowerCase();
    const searchableText = `${template.template.name}${template.style}${template.scene}${template.category}${template.ratio}`.toLowerCase();
    if (normalizedSearchTerm && !searchableText.includes(normalizedSearchTerm)) return false;
    if (selectedCategory && template.category !== selectedCategory) return false;
    if (selectedRatio !== "全部" && template.ratio !== selectedRatio) return false;
    if (selectedStyle !== "全部" && template.style !== selectedStyle) return false;
    if (selectedScene !== "全部" && template.scene !== selectedScene) return false;
    if (selectedColor && template.accentColor !== selectedColor) return false;
    return true;
  };

  const filteredMarketTemplates = parsedMarketTemplates.filter(filterMarketTemplate);

  const loadSavedTemplates = useCallback(async () => {
    const hasStoredAuthSession = Boolean(tokenStorage.access || tokenStorage.refresh || authToken);
    if (!hasStoredAuthSession) {
      setSavedTemplates([]);
      setMarketTemplates([]);
      setSavedTemplatesError(null);
      return;
    }

    setSavedTemplatesLoading(true);
    try {
      let teamId = currentEvent?.teamId;
      if (!teamId && captureTeamId) {
        teamId = captureTeamId;
      }
      if (!teamId) {
        const teams = await getMyTeams(authToken ?? undefined);
        teamId = teams[0]?.id;
      }
      if (!teamId) {
        setSavedTemplates([]);
        setMarketTemplates([]);
        setSavedTemplatesError(null);
        return;
      }

      const [teamTemplates, catalogTemplates] = await Promise.all([
        getTemplates(teamId, authToken ?? undefined),
        getTemplateCatalog(authToken ?? undefined),
      ]);
      setSavedTemplates(teamTemplates);
      setMarketTemplates(catalogTemplates);
      setSavedTemplatesError(null);
    } catch {
      setSavedTemplatesError("已保存模板加载失败");
    } finally {
      setSavedTemplatesLoading(false);
    }
  }, [authToken, captureTeamId, currentEvent?.teamId]);

  useEffect(() => {
    loadSavedTemplates();
  }, [loadSavedTemplates]);

  useEffect(() => {
    const justSavedTemplateId = sessionStorage.getItem(JUST_SAVED_TEMPLATE_SESSION_KEY);
    if (!justSavedTemplateId) {
      return;
    }

    setRecentlySavedTemplateId(justSavedTemplateId);
    sessionStorage.removeItem(JUST_SAVED_TEMPLATE_SESSION_KEY);
  }, []);

  const filteredSavedTemplates = savedTemplates.filter(t => {
    const normalizedSearchTerm = searchTerm.trim().toLowerCase();
    if (normalizedSearchTerm && !t.name.toLowerCase().includes(normalizedSearchTerm)) return false;
    if (selectedCategory && selectedCategory !== "自定义") return false;
    return true;
  });

  const categoryCards = [
    { label: "婚礼模板", icon: Heart, color: "from-pink-600 to-rose-800", filter: "婚礼" },
    { label: "生日模板", icon: Star, color: "from-yellow-600 to-orange-800", filter: "生日" },
    { label: "企业模板", icon: Building, color: "from-blue-600 to-indigo-800", filter: "企业" },
    { label: "毕业模板", icon: Trophy, color: "from-emerald-600 to-teal-800", filter: "毕业" },
    { label: "节日模板", icon: Sparkles, color: "from-violet-600 to-purple-800", filter: "节日" },
    { label: "自定义模板", icon: Grid3X3, color: "from-gray-600 to-slate-800", filter: "自定义" },
  ].map(card => ({
    ...card,
    count: card.filter === "自定义"
      ? savedTemplates.length + parsedMarketTemplates.filter(template => template.category === card.filter).length
      : parsedMarketTemplates.filter(template => template.category === card.filter).length,
  }));

  const openTemplateEditor = (templateId?: string) => {
    sessionStorage.removeItem(TEMPLATE_EDITOR_QUICK_LAYOUT_SESSION_KEY);
    sessionStorage.removeItem(TEMPLATE_EDITOR_UPLOAD_BACKGROUND_SESSION_KEY);
    if (templateId) {
      sessionStorage.setItem(SELECTED_TEMPLATE_SESSION_KEY, templateId);
    } else {
      sessionStorage.removeItem(SELECTED_TEMPLATE_SESSION_KEY);
    }
    navigate("template-editor");
  };

  const openTemplateEditorForBackgroundUpload = () => {
    sessionStorage.removeItem(SELECTED_TEMPLATE_SESSION_KEY);
    sessionStorage.removeItem(TEMPLATE_EDITOR_QUICK_LAYOUT_SESSION_KEY);
    sessionStorage.setItem(TEMPLATE_EDITOR_UPLOAD_BACKGROUND_SESSION_KEY, "1");
    navigate("template-editor");
  };

  const resolveTemplateTeamId = useCallback(async () => {
    if (currentEvent?.teamId) return currentEvent.teamId;
    if (captureTeamId) return captureTeamId;
    const teams = await getMyTeams(authToken ?? undefined);
    return teams[0]?.id;
  }, [authToken, captureTeamId, currentEvent?.teamId]);

  const selectTemplateForPrint = (template: TemplateResponse) => {
    if (!isTemplateLayout(template.layers)) {
      showToast.error("该模板缺少可打印版式，请先打开编辑器保存一次");
      return;
    }

    setActivePrintTemplate({
      id: template.id,
      name: template.name,
      layout: {
        ...template.layers,
        id: template.layers.id || template.id,
        name: template.name,
      },
    });
    showToast.success(`已使用模板：${template.name}`);
    const returnScreen = templateSelectionReturnScreen === "print" ? "print" : "camera";
    setTemplateSelectionReturnScreen(null);
    navigate(returnScreen);
  };

  const isTemplateSelectionMode = templateSelectionReturnScreen === "print" || templateSelectionReturnScreen === "camera";
  const selectTemplateButtonLabel = templateSelectionReturnScreen === "print" ? "使用并返回预览" : "使用并返回拍照";
  const selectionModeTitle = templateSelectionReturnScreen === "print" ? "正在为打印预览选择模板" : "正在为拍照流程选择模板";
  const selectionModeReturnLabel = templateSelectionReturnScreen === "print" ? "返回打印预览" : "返回拍照";
  const selectionModeDescription = templateSelectionReturnScreen === "print"
    ? "选择后会回到打印预览页，若版式需要更多照片，预览页会提示继续补拍。"
    : "选择后会回到相机页，并按版式照片槽位继续拍摄。";

  const returnToSelectionSource = () => {
    const returnScreen = templateSelectionReturnScreen === "print" ? "print" : "camera";
    setTemplateSelectionReturnScreen(null);
    navigate(returnScreen);
  };

  const clearVisualFilters = () => {
    setSelectedCategory(null);
    setActiveCategory("全部");
    setSelectedColor(null);
    setSelectedRatio("全部");
    setSelectedStyle("全部");
    setSelectedScene("全部");
  };

  const importMarketTemplate = async (marketTemplate: MarketTemplate) => {
    setOperatingTemplateId(marketTemplate.template.id);
    try {
      const teamId = await resolveTemplateTeamId();
      if (!teamId) {
        showToast.error("未找到可保存模板的团队");
        return;
      }

      const copy = await createTemplate({
        team_id: teamId,
        name: marketTemplate.template.name,
        description: marketTemplate.template.description || "从模板市场导入",
        size: marketTemplate.template.size,
        canvas_width: marketTemplate.template.canvas_width == null
          ? null
          : Number(marketTemplate.template.canvas_width),
        canvas_height: marketTemplate.template.canvas_height == null
          ? null
          : Number(marketTemplate.template.canvas_height),
        layers: marketTemplate.layout as unknown as Record<string, unknown>,
        thumbnail_url: marketTemplate.template.thumbnail_url,
        is_public: false,
      }, authToken ?? undefined);
      setSavedTemplates(prev => [copy, ...prev.filter(item => item.id !== copy.id)]);

      if (isTemplateSelectionMode) {
        selectTemplateForPrint(copy);
        return;
      }

      showToast.success("市场模板已加入我的模板");
      openTemplateEditor(copy.id);
    } catch (err) {
      showToast.error(err instanceof Error ? err.message : "市场模板导入失败");
    } finally {
      setOperatingTemplateId(null);
    }
  };

  const duplicateSavedTemplate = async (template: TemplateResponse) => {
    setOperatingTemplateId(template.id);
    try {
      const copy = await duplicateTemplate(template.id, `${template.name} 副本`);
      setSavedTemplates(prev => [copy, ...prev]);
      showToast.success("模板副本已创建");
    } catch (err) {
      showToast.error(err instanceof Error ? err.message : "复制模板失败");
    } finally {
      setOperatingTemplateId(null);
    }
  };

  const deleteSavedTemplate = async (template: TemplateResponse) => {
    if (!window.confirm(`删除模板「${template.name}」？此操作无法撤销。`)) return;

    setOperatingTemplateId(template.id);
    try {
      await deleteTemplate(template.id);
      setSavedTemplates(prev => prev.filter(item => item.id !== template.id));
      if (activePrintTemplate?.id === template.id) {
        setActivePrintTemplate(null);
      }
      showToast.success("模板已删除");
    } catch (err) {
      showToast.error(err instanceof Error ? err.message : "删除模板失败");
    } finally {
      setOperatingTemplateId(null);
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Main content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {isTemplateSelectionMode && (
          <GlassCard className="p-4">
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-sm font-semibold text-white">
                  <LayoutTemplate size={16} className="text-emerald-300" />
                  {selectionModeTitle}
                </div>
                <div className="mt-1 text-xs text-white/45">
                  {selectionModeDescription}
                  当前模板：{activePrintTemplate?.name ?? "未选择"} · 已拍照片：{photos.length}
                </div>
              </div>
              <button
                type="button"
                className="flex flex-shrink-0 items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-white/65 hover:bg-white/10 hover:text-white"
                onClick={returnToSelectionSource}
              >
                <ArrowLeft size={13} />
                {selectionModeReturnLabel}
              </button>
            </div>
          </GlassCard>
        )}

        {/* Search */}
        <div className="flex items-center gap-3">
          <div className="flex-1 relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
            <input className="w-full bg-white/5 border border-white/10 rounded-xl pl-9 pr-4 py-2.5 text-sm text-white placeholder-white/30 outline-none focus:border-violet-500/50"
              placeholder="搜索模板名称、风格、标签..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)} />
          </div>
          <GlowBtn size="sm" variant="ghost" onClick={() => setShowFilters(f => !f)}>
            <Filter size={14} />筛选
          </GlowBtn>
          <GlowBtn size="sm" variant="ghost" onClick={openTemplateEditorForBackgroundUpload}>
            <ImagePlus size={14} />上传底图
          </GlowBtn>
          <GlowBtn size="sm" variant="primary" onClick={() => openTemplateEditor()}>
            <Plus size={14} />新建
          </GlowBtn>
        </div>

        {/* Category tabs */}
        <div className="flex gap-2 overflow-x-auto pb-1">
          {categories.map(c => (
            <button key={c} onClick={() => { setActiveCategory(c); setSelectedCategory(c === "全部" ? null : c); }}
              className={`flex-shrink-0 px-4 py-1.5 rounded-full text-sm transition-all ${activeCategory === c ? "bg-violet-500 text-white shadow-[0_0_15px_rgba(139,92,246,0.4)]" : "bg-white/5 text-white/60 hover:bg-white/10"}`}>
              {c}
            </button>
          ))}
        </div>

        {/* Category cards */}
        <div className="grid grid-cols-6 gap-3">
          {categoryCards.map(c => (
            <motion.div key={c.label}
              className={`relative rounded-2xl p-4 text-center cursor-pointer overflow-hidden bg-gradient-to-br ${c.color} ${selectedCategory === c.filter ? "ring-2 ring-white/60" : ""}`}
              whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
              onClick={() => setSelectedCategory(selectedCategory === c.filter ? null : c.filter)}
            >
              <c.icon size={28} className="text-white mx-auto mb-2" />
              <div className="text-xs font-semibold text-white">{c.label}</div>
              <div className="text-[10px] text-white/60 mt-0.5">{c.count} 套可用</div>
            </motion.div>
          ))}
        </div>

        {(savedTemplatesLoading || savedTemplatesError || filteredSavedTemplates.length > 0) && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-white">已保存模板</span>
                <NeonBadge color="green">{filteredSavedTemplates.length}</NeonBadge>
              </div>
              <button className="text-xs text-violet-400 hover:text-violet-300 flex items-center gap-1"
                onClick={loadSavedTemplates}>
                <RefreshCw size={12} className={savedTemplatesLoading ? "animate-spin" : ""} />
                刷新
              </button>
            </div>

            {savedTemplatesError && (
              <GlassCard className="p-4 mb-3 text-xs text-amber-300">{savedTemplatesError}</GlassCard>
            )}

            <div className="grid grid-cols-6 gap-4">
              {filteredSavedTemplates.map(t => {
                const isRecentlySavedTemplate = recentlySavedTemplateId === t.id;
                const savedLayout = isTemplateLayout(t.layers) ? t.layers : null;

                return (
                  <motion.div key={t.id} whileHover={{ scale: 1.03 }} className="cursor-pointer group"
                    onClick={() => {
                      if (isTemplateSelectionMode) {
                        selectTemplateForPrint(t);
                        return;
                      }
                      openTemplateEditor(t.id);
                    }}>
                    <div className={`relative rounded-xl overflow-hidden aspect-[2/5] border transition-all bg-white ${isRecentlySavedTemplate ? "border-emerald-400 ring-2 ring-emerald-400/40 shadow-[0_0_24px_rgba(52,211,153,0.22)]" : "border-white/10 group-hover:border-emerald-500/40"}`}>
                      <TemplateThumbnailPreview layout={savedLayout} />
                      {isRecentlySavedTemplate && (
                        <div className="absolute top-2 left-2 z-10">
                          <NeonBadge color="green">刚保存</NeonBadge>
                        </div>
                      )}
                      <div className="absolute top-2 right-2">
                        <NeonBadge color={activePrintTemplate?.id === t.id ? "purple" : "green"}>
                          {activePrintTemplate?.id === t.id ? "使用中" : "已保存"}
                        </NeonBadge>
                      </div>
                      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-2">
                        <div className="grid w-full grid-cols-2 gap-1.5">
                          <GlowBtn
                            size="sm"
                            variant="primary"
                            className="justify-center px-2"
                            onClick={(event) => {
                              event.stopPropagation();
                              selectTemplateForPrint(t);
                            }}
                          >
                            <Check size={12} />{selectTemplateButtonLabel}
                          </GlowBtn>
                          <GlowBtn
                            size="sm"
                            variant="ghost"
                            className="justify-center px-2"
                            onClick={(event) => {
                              event.stopPropagation();
                              openTemplateEditor(t.id);
                            }}
                          >
                            编辑
                          </GlowBtn>
                        </div>
                      </div>
                    </div>
                    <div className="mt-2">
                      <div className="text-xs font-medium text-white truncate">{t.name}</div>
                      <div className="flex items-center justify-between gap-1">
                        <div className="text-[10px] text-white/40 truncate">{t.size || "自定义尺寸"}</div>
                        <div className="flex items-center gap-1">
                          <button
                            className="rounded p-1 text-white/35 hover:bg-white/10 hover:text-white/80 disabled:opacity-40"
                            title="复制模板"
                            disabled={operatingTemplateId === t.id}
                            onClick={(event) => {
                              event.stopPropagation();
                              void duplicateSavedTemplate(t);
                            }}
                          >
                            <Copy size={11} />
                          </button>
                          <button
                            className="rounded p-1 text-white/35 hover:bg-red-500/10 hover:text-red-300 disabled:opacity-40"
                            title="删除模板"
                            disabled={operatingTemplateId === t.id}
                            onClick={(event) => {
                              event.stopPropagation();
                              void deleteSavedTemplate(t);
                            }}
                          >
                            <Trash2 size={11} />
                          </button>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        )}

        {/* Persisted public template catalog */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-white">模板市场</span>
              <NeonBadge color="purple">{filteredMarketTemplates.length}</NeonBadge>
            </div>
            <button className="text-xs text-violet-400 hover:text-violet-300" onClick={clearVisualFilters}>查看全部</button>
          </div>
          {savedTemplatesLoading ? (
            <div className="py-8 text-center text-xs text-white/40">正在加载公开模板...</div>
          ) : filteredMarketTemplates.length === 0 ? (
            <div className="border border-dashed border-white/10 py-8 text-center text-xs text-white/40">
              {savedTemplatesError ? "模板市场加载失败" : "暂无符合条件的公开模板"}
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
              {filteredMarketTemplates.map(item => (
                <motion.div
                  key={item.template.id}
                  whileHover={{ scale: 1.03 }}
                  className={`group ${operatingTemplateId === item.template.id ? "cursor-wait opacity-60" : "cursor-pointer"}`}
                  onClick={() => {
                    if (operatingTemplateId !== item.template.id) {
                      void importMarketTemplate(item);
                    }
                  }}
                >
                  <div className="relative overflow-hidden rounded-lg aspect-[2/5] border border-white/10 bg-white transition-all group-hover:border-violet-500/40">
                    <TemplateThumbnailPreview layout={item.layout} />
                    <div className="absolute top-2 right-2">
                      <NeonBadge color={item.feature === "热门" ? "pink" : item.feature === "推荐" ? "purple" : "green"}>
                        {item.feature}
                      </NeonBadge>
                    </div>
                    <div className="absolute left-2 top-2 h-3 w-3 rounded-full border border-white/60" style={{ background: item.accentColor }} />
                    <div className="absolute inset-0 flex items-end bg-gradient-to-t from-black/70 via-transparent p-2 opacity-0 transition-opacity group-hover:opacity-100">
                      <span className="w-full rounded bg-violet-500/90 px-2 py-1 text-center text-[10px] font-medium text-white">
                        {operatingTemplateId === item.template.id
                          ? "正在导入"
                          : isTemplateSelectionMode ? "导入并使用" : "加入我的模板"}
                      </span>
                    </div>
                  </div>
                  <div className="mt-2">
                    <div className="truncate text-xs font-medium text-white">{item.template.name}</div>
                    <div className="truncate text-[10px] text-white/40">
                      {item.ratio} · {item.category} · {item.style}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right filter panel */}
      <GlassCard className={`w-48 rounded-none border-l border-white/5 p-4 space-y-4 overflow-y-auto transition-all ${showFilters ? "" : "hidden"}`}>
        <div className="text-xs font-semibold text-white/60 uppercase tracking-wider">筛选条件</div>
        {[
          { label: "比例", key: "ratio", options: ["全部", "2×6", "4×6", "6×8", "其他"] },
          { label: "风格", key: "style", options: ["全部", "清新", "复古", "国潮", "欧美", "日系"] },
          { label: "场景", key: "scene", options: ["全部", "户外", "室内", "工作室"] },
          { label: "颜色", special: "colors" },
        ].map(f => (
          <div key={f.label} className="space-y-2">
            <div className="text-xs text-white/50">{f.label}</div>
            {f.special === "colors" ? (
              <div className="flex flex-wrap gap-1.5">
                {["#ec4899", "#8b5cf6", "#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#06b6d4", "#f97316", "#fff", "#333"].map(c => (
                  <div key={c}
                    className={`w-5 h-5 rounded-full cursor-pointer border hover:scale-110 transition-transform ${selectedColor === c ? "border-white ring-2 ring-white/50" : "border-white/10"}`}
                    style={{ background: c }}
                    onClick={() => setSelectedColor(selectedColor === c ? null : c)} />
                ))}
              </div>
            ) : (
              <div className="flex flex-wrap gap-1">
                {f.options?.map(o => {
                  const isSelected = (f.key === "ratio" && selectedRatio === o)
                    || (f.key === "style" && selectedStyle === o)
                    || (f.key === "scene" && selectedScene === o);
                  return (
                    <button key={o}
                      className={`px-2 py-0.5 rounded text-[10px] ${isSelected ? "bg-violet-500/20 text-violet-400 border border-violet-500/30" : "bg-white/5 text-white/40 hover:bg-white/10"}`}
                      onClick={() => {
                        if (f.key === "ratio") setSelectedRatio(o);
                        else if (f.key === "style") setSelectedStyle(o);
                        else if (f.key === "scene") setSelectedScene(o);
                      }}>
                      {o}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        ))}
        <GlowBtn size="sm" variant="primary" className="w-full justify-center"
          onClick={clearVisualFilters}>
          清空筛选
        </GlowBtn>
      </GlassCard>
    </div>
  );
}
