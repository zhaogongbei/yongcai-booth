import { useCallback, useEffect, useState } from "react";
import {
  Camera, Sun, Settings2, Zap, CheckCircle2, ArrowLeft, ArrowRight,
  RefreshCw, Image, ChevronRight
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { toast } from "sonner";
import { request } from "../../lib/api";
import { GlassCard } from "../components/GlassCard";
import { GlowBtn } from "../components/GlowBtn";
import type { Screen } from "../types";

interface WizardStep {
  step: number;
  title: string;
  description: string;
  data?: Record<string, unknown>;
}

const STEP_ICONS = [Camera, Sun, Image, Zap, CheckCircle2];

export function CameraWizardScreen({ navigate }: { navigate: (s: Screen) => void }) {
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [wizardData, setWizardData] = useState<WizardStep | null>(null);
  const [useFlash, setUseFlash] = useState(true);
  const [flashPower, setFlashPower] = useState("1/2");
  const [testPhotoSrc, setTestPhotoSrc] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Record<string, unknown> | null>(null);
  const [finalSettings, setFinalSettings] = useState<Record<string, unknown> | null>(null);

  // Step 1: 检测相机型号
  const loadStep1 = useCallback(async () => {
    setLoading(true);
    try {
      const data = await request<Record<string, unknown>>("/camera/wizard/step1");
      setWizardData({
        step: 1,
        title: String(data.title || "检测相机型号"),
        description: String(data.description || ""),
        data: {
          model: data.model ?? "未检测到DSLR相机",
          presets: data.presets ?? {},
          recommendations: data.recommendations ?? []
        }
      });
    } catch {
      setWizardData({
        step: 1,
        title: "检测相机型号",
        description: "未能连接到后端，请检查服务是否运行",
        data: {
          model: "Web Camera (降级模式)",
          presets: { iso: 800, shutter_speed: "1/125", aperture: "f/5.6" },
          recommendations: ["Webcam模式无需USB连接DSLR"]
        }
      });
    } finally {
      setLoading(false);
    }
  }, []);

  // Step 2: 闪光灯配置
  const loadStep2 = useCallback(async () => {
    setLoading(true);
    try {
      const data = await request<Record<string, unknown>>("/camera/wizard/step2", { method: "POST" });
      setWizardData({
        step: 2,
        title: String(data.title || "闪光灯配置"),
        description: String(data.description || ""),
        data: data.flash_settings as Record<string, unknown> ?? {}
      });
    } catch {
      setWizardData({
        step: 2,
        title: "闪光灯配置",
        description: "选择是否使用闪光灯及功率",
        data: {}
      });
    } finally {
      setLoading(false);
    }
  }, []);

  // Step 3: 拍摄测试照片
  const loadStep3 = useCallback(async () => {
    setLoading(true);
    try {
      const data = await request<Record<string, unknown>>("/camera/wizard/step3", { method: "POST" });

      if (data.test_photo) {
        setTestPhotoSrc(String(data.test_photo));
      }
      if (data.analysis) {
        setAnalysis(data.analysis as Record<string, unknown>);
      }

      setWizardData({
        step: 3,
        title: String(data.title || "测试照片分析"),
        description: String(data.description || ""),
        data: (data.analysis as Record<string, unknown> | undefined) ?? undefined
      });
    } catch {
      setWizardData({
        step: 3,
        title: "测试照片分析",
        description: "请先在拍照界面拍摄测试照片",
        data: undefined
      });
    } finally {
      setLoading(false);
    }
  }, []);

  // Step 4: 闪光灯功率微调
  const loadStep4 = useCallback(async () => {
    setLoading(true);
    try {
      const data = await request<Record<string, unknown>>("/camera/wizard/step4", { method: "POST" });
      setWizardData({
        step: 4,
        title: String(data.title || "闪光灯功率配置"),
        description: String(data.description || ""),
        data: data.flash_settings as Record<string, unknown> ?? {}
      });
    } catch {
      setWizardData({
        step: 4,
        title: "闪光灯功率配置",
        description: "微调闪光灯输出功率",
        data: {}
      });
    } finally {
      setLoading(false);
    }
  }, []);

  // Step 5: 最终确认
  const loadStep5 = useCallback(async () => {
    setLoading(true);
    try {
      const data = await request<Record<string, unknown>>("/camera/wizard/step5", { method: "POST" });
      if (data.final_settings) {
        setFinalSettings(data.final_settings as Record<string, unknown>);
      }
      setWizardData({
        step: 5,
        title: String(data.title || "最终确认"),
        description: String(data.description || ""),
        data: {
          settings: data.final_settings ?? {},
          tips: data.tips ?? []
        }
      });
      toast.success("相机设置向导完成");
    } catch {
      setWizardData({
        step: 5,
        title: "最终确认",
        description: "确认所有设置，点击完成进入拍照",
        data: { settings: {}, tips: ["拍摄时保持相机稳定", "及时检查照片效果"] }
      });
    } finally {
      setLoading(false);
    }
  }, []);

  // 加载当前步骤
  const loadCurrentStep = useCallback(async (step: number) => {
    switch (step) {
      case 1:
        await loadStep1();
        break;
      case 2:
        await loadStep2();
        break;
      case 3:
        await loadStep3();
        break;
      case 4:
        await loadStep4();
        break;
      case 5:
        await loadStep5();
        break;
    }
  }, [loadStep1, loadStep2, loadStep3, loadStep4, loadStep5]);

  useEffect(() => {
    loadCurrentStep(currentStep);
  }, [currentStep]);

  const goNext = () => {
    if (currentStep < 5) {
      setCurrentStep(prev => prev + 1);
    } else {
      navigate("camera");
    }
  };

  const goPrev = () => {
    if (currentStep > 1) {
      setCurrentStep(prev => prev - 1);
    } else {
      navigate("camera");
    }
  };

  const FLASH_POWERS = ["1/1", "1/2", "1/4", "1/8", "1/16"];

  return (
    <main className="flex-1 flex overflow-hidden">
      <div className="flex-1 flex flex-col p-6 overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-white">相机设置向导</h1>
            <p className="text-xs text-white/40 mt-1">逐步引导完成相机参数配置</p>
          </div>
          <button
            onClick={() => navigate("camera")}
            className="text-white/40 hover:text-white/80 transition-colors text-sm"
          >
            跳过向导
          </button>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-1 mb-8">
          {[1, 2, 3, 4, 5].map(i => {
            const Icon = STEP_ICONS[i - 1];
            const active = i === currentStep;
            const done = i < currentStep;
            return (
              <div key={i} className="flex items-center gap-1">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                    active
                      ? "bg-violet-500 text-white shadow-lg shadow-violet-500/30"
                      : done
                        ? "bg-violet-500/50 text-white"
                        : "bg-white/10 text-white/30"
                  }`}
                >
                  <Icon size={14} />
                </div>
                <span
                  className={`text-[10px] ${active ? "text-violet-400" : done ? "text-violet-400/50" : "text-white/20"}`}
                >
                  {i === 1 ? "检测" : i === 2 ? "闪光灯" : i === 3 ? "测试" : i === 4 ? "功率" : "确认"}
                </span>
                {i < 5 && (
                  <div
                    className={`w-6 h-0.5 rounded-full mx-1 ${done ? "bg-violet-500/50" : "bg-white/10"}`}
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Progress bar */}
        <div className="w-full h-1 bg-white/10 rounded-full mb-8 overflow-hidden">
          <motion.div
            className="h-full bg-violet-500 rounded-full"
            animate={{ width: `${(currentStep / 5) * 100}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>

        {/* Step content */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentStep}
            className="flex-1"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
          >
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <RefreshCw size={32} className="text-violet-400 animate-spin" />
              </div>
            ) : (
              <GlassCard className="p-6 space-y-4">
                <h2 className="text-lg font-semibold text-white">
                  {wizardData?.title || `步骤 ${currentStep}`}
                </h2>
                <p className="text-sm text-white/50">{wizardData?.description}</p>

                {/* Step 1 content */}
                {currentStep === 1 && (
                  <div className="space-y-4">
                    <div className="bg-white/5 rounded-lg p-4">
                      <div className="text-xs text-white/40 mb-2">检测到的相机</div>
                      <div className="flex items-center gap-2">
                        <Camera size={20} className="text-violet-400" />
                        <span className="text-white font-mono">
                          {String((wizardData?.data as Record<string, unknown>)?.model ?? "检测中...")}
                        </span>
                      </div>
                    </div>

                    <div className="bg-white/5 rounded-lg p-4">
                      <div className="text-xs text-white/40 mb-2">推荐预设参数</div>
                      <pre className="text-xs text-white/60 font-mono whitespace-pre-wrap">
                        {JSON.stringify((wizardData?.data as Record<string, unknown>)?.presets ?? {}, null, 2)}
                      </pre>
                    </div>

                    {Array.isArray((wizardData?.data as Record<string, unknown>)?.recommendations) && (
                      <div className="bg-violet-500/10 rounded-lg p-4 border border-violet-500/20">
                        <div className="text-xs text-violet-400 mb-2">建议</div>
                        <ul className="space-y-1">
                          {((wizardData?.data as Record<string, unknown>)?.recommendations as string[]).map(
                            (rec, i) => (
                              <li key={i} className="text-xs text-white/60 flex items-start gap-2">
                                <ChevronRight size={12} className="text-violet-400 mt-0.5 flex-shrink-0" />
                                {rec}
                              </li>
                            )
                          )}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* Step 2 content */}
                {currentStep === 2 && (
                  <div className="space-y-6">
                    <div className="bg-white/5 rounded-lg p-4">
                      <div className="text-xs text-white/40 mb-3">是否使用闪光灯？</div>
                      <div className="flex gap-3">
                        <button
                          onClick={() => setUseFlash(true)}
                          className={`px-6 py-3 rounded-lg text-sm transition-all ${
                            useFlash
                              ? "bg-violet-500 text-white shadow-lg shadow-violet-500/30"
                              : "bg-white/10 text-white/40 hover:bg-white/20"
                          }`}
                        >
                          <Sun size={14} className="inline mr-1" />
                          使用闪光灯
                        </button>
                        <button
                          onClick={() => setUseFlash(false)}
                          className={`px-6 py-3 rounded-lg text-sm transition-all ${
                            !useFlash
                              ? "bg-violet-500 text-white shadow-lg shadow-violet-500/30"
                              : "bg-white/10 text-white/40 hover:bg-white/20"
                          }`}
                        >
                          不使用
                        </button>
                      </div>
                    </div>

                    {useFlash && (
                      <div className="bg-violet-500/10 rounded-lg p-4 border border-violet-500/20">
                        <div className="text-xs text-violet-400 mb-2">闪光灯使用建议</div>
                        <ul className="space-y-1">
                          <li className="text-xs text-white/60">快门速度不超过1/200s（同步速度限制）</li>
                          <li className="text-xs text-white/60">ISO建议设置为400-800</li>
                          <li className="text-xs text-white/60">推荐起始功率：1/2</li>
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* Step 3 content */}
                {currentStep === 3 && (
                  <div className="space-y-4">
                    {testPhotoSrc ? (
                      <div className="bg-white/5 rounded-lg p-4">
                        <img
                          src={testPhotoSrc}
                          alt="测试照片"
                          className="w-full max-h-64 object-contain rounded-lg"
                        />
                      </div>
                    ) : (
                      <div className="bg-white/5 rounded-lg p-8 flex flex-col items-center justify-center gap-3">
                        <Image size={48} className="text-white/20" />
                        <span className="text-sm text-white/40">
                          {wizardData?.data
                            ? "分析结果已生成"
                            : "Webcam模式下请先在拍照界面拍摄测试照片"}
                        </span>
                      </div>
                    )}

                    {analysis && (
                      <div className="space-y-3">
                        <div className="bg-white/5 rounded-lg p-4">
                          <div className="text-xs text-white/40 mb-2">曝光分析</div>
                          <div className="flex items-center gap-4">
                            <div>
                              <div className="text-2xl font-bold text-white">
                                {((analysis.brightness as number) * 100).toFixed(0)}%
                              </div>
                              <div className="text-[10px] text-white/30">亮度</div>
                            </div>
                            <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                              <motion.div
                                className={`h-full rounded-full ${
                                  analysis.is_overexposed
                                    ? "bg-yellow-500"
                                    : analysis.is_underexposed
                                      ? "bg-red-500"
                                      : "bg-emerald-500"
                                }`}
                                initial={{ width: 0 }}
                                animate={{ width: `${(analysis.brightness as number) * 100}%` }}
                                transition={{ duration: 0.5 }}
                              />
                            </div>
                          </div>
                        </div>

                        {Array.isArray(analysis.recommendations) && (
                          <div className="bg-violet-500/10 rounded-lg p-4 border border-violet-500/20">
                            <div className="text-xs text-violet-400 mb-2">优化建议</div>
                            <ul className="space-y-1">
                              {(analysis.recommendations as string[]).map((rec, i) => (
                                <li key={i} className="text-xs text-white/60 flex items-start gap-2">
                                  <ChevronRight size={12} className="text-violet-400 mt-0.5 flex-shrink-0" />
                                  {rec}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {Boolean(analysis.suggested_iso || analysis.suggested_shutter) && (
                          <div className="bg-white/5 rounded-lg p-4">
                            <div className="text-xs text-white/40 mb-2">建议参数</div>
                            <div className="flex gap-4 text-sm text-white font-mono">
                              {Boolean(analysis.suggested_iso) && <div>ISO {String(analysis.suggested_iso)}</div>}
                              {Boolean(analysis.suggested_shutter) && <div>快门 {String(analysis.suggested_shutter)}</div>}
                              {Boolean(analysis.suggested_aperture) && <div>光圈 {String(analysis.suggested_aperture)}</div>}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Step 4 content */}
                {currentStep === 4 && (
                  <div className="space-y-6">
                    <div className="bg-white/5 rounded-lg p-4">
                      <div className="text-xs text-white/40 mb-4">闪光灯功率</div>
                      <div className="grid grid-cols-5 gap-2">
                        {FLASH_POWERS.map(power => (
                          <button
                            key={power}
                            onClick={() => setFlashPower(power)}
                            className={`py-3 rounded-lg text-sm transition-all ${
                              flashPower === power
                                ? "bg-violet-500 text-white shadow-lg shadow-violet-500/30"
                                : "bg-white/10 text-white/50 hover:bg-white/20"
                            }`}
                          >
                            {power}
                          </button>
                        ))}
                      </div>
                      <div className="mt-4 h-2 bg-white/10 rounded-full overflow-hidden">
                        <motion.div
                          className="h-full bg-violet-500 rounded-full"
                          animate={{
                            width: `${
                              flashPower === "1/1"
                                ? 100
                                : flashPower === "1/2"
                                  ? 50
                                  : flashPower === "1/4"
                                    ? 25
                                    : flashPower === "1/8"
                                      ? 12.5
                                      : 6.25
                            }%`
                          }}
                          transition={{ duration: 0.3 }}
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* Step 5 content */}
                {currentStep === 5 && (
                  <div className="space-y-4">
                    <div className="bg-emerald-500/10 rounded-lg p-6 border border-emerald-500/20 text-center">
                      <CheckCircle2 size={48} className="text-emerald-400 mx-auto mb-3" />
                      <div className="text-lg font-semibold text-white mb-1">设置完成</div>
                      <div className="text-sm text-white/50">相机参数已配置完成，可以开始拍照</div>
                    </div>

                    {finalSettings && (
                      <div className="bg-white/5 rounded-lg p-4">
                        <div className="text-xs text-white/40 mb-2">最终设置</div>
                        <pre className="text-xs text-white/60 font-mono whitespace-pre-wrap">
                          {JSON.stringify(finalSettings, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </GlassCard>
            )}
          </motion.div>
        </AnimatePresence>

        {/* Navigation buttons */}
        <div className="flex items-center justify-between mt-6">
          <button
            onClick={goPrev}
            className="flex items-center gap-1 px-4 py-2 rounded-lg text-sm text-white/50 hover:text-white/80 hover:bg-white/5 transition-colors"
          >
            <ArrowLeft size={14} />
            {currentStep === 1 ? "返回" : "上一步"}
          </button>

          <div className="text-xs text-white/30">
            {currentStep} / 5
          </div>

          <GlowBtn onClick={goNext} variant="primary" disabled={loading}>
            {currentStep === 5 ? "完成" : "下一步"}
            <ArrowRight size={14} />
          </GlowBtn>
        </div>
      </div>
    </main>
  );
}
