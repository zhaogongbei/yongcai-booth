import React, { useState, useEffect } from "react";
import { motion } from "motion/react";
import { Plus, Trash2, GripVertical, Save, ChevronDown, ChevronUp, ToggleLeft } from "lucide-react";
import { toast } from "sonner";
import { request } from "@/lib/api";
import { Button } from "@/app/components/ui/button";
import { GLASS_SELECT_OPTION_CLASS_NAME, getGlassSelectClassName } from "@/app/components/glassSelect";
import { useSettings } from "@/app/stores/useSettings";

interface SurveyQuestion {
  id: string;
  type: "text_short" | "text_long" | "multiple_choice" | "rating";
  text: string;
  required: boolean;
  options: string[];
  order: number;
}

interface SurveyConfigResponse {
  enabled: boolean;
  title: string;
  questions: SurveyQuestion[];
}

interface DisclaimerConfigResponse {
  enabled: boolean;
  title: string;
  text: string;
  require_signature: boolean;
}

export function SurveyConfigScreen({ navigate }: { navigate?: (screen: any) => void }) {
  const { currentEvent } = useSettings();
  const [surveyEnabled, setSurveyEnabled] = useState(false);
  const [surveyTitle, setSurveyTitle] = useState("问卷调查");
  const [questions, setQuestions] = useState<SurveyQuestion[]>([]);
  const [disclaimerEnabled, setDisclaimerEnabled] = useState(false);
  const [disclaimerTitle, setDisclaimerTitle] = useState("免责声明");
  const [disclaimerText, setDisclaimerText] = useState("");
  const [requireSignature, setRequireSignature] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const questionTypes = [
    { value: "text_short", label: "简短回答" },
    { value: "text_long", label: "长篇回答" },
    { value: "multiple_choice", label: "单项选择" },
    { value: "rating", label: "星级评分" },
  ];

  useEffect(() => {
    if (!currentEvent?.id) return;

    const loadConfig = async () => {
      try {
        // 加载调查配置
        const surveyRes = await request<SurveyConfigResponse>(`/surveys/event/${currentEvent.id}`);
        setSurveyEnabled(surveyRes.enabled);
        setSurveyTitle(surveyRes.title);
        setQuestions(surveyRes.questions || []);

        // 加载免责声明配置
        const disclaimerRes = await request<DisclaimerConfigResponse>(`/disclaimers/event/${currentEvent.id}`);
        setDisclaimerEnabled(disclaimerRes.enabled);
        setDisclaimerTitle(disclaimerRes.title);
        setDisclaimerText(disclaimerRes.text);
        setRequireSignature(disclaimerRes.require_signature);
      } catch (error) {
        console.error("加载配置失败:", error);
        toast.error("加载配置失败");
      } finally {
        setLoading(false);
      }
    };

    loadConfig();
  }, [currentEvent?.id]);

  // 添加新问题
  const addQuestion = () => {
    const newQuestion: SurveyQuestion = {
      id: `q_${Date.now()}`,
      type: "text_short",
      text: "",
      required: true,
      options: [],
      order: questions.length,
    };
    setQuestions([...questions, newQuestion]);
  };

  // 删除问题
  const removeQuestion = (index: number) => {
    const newQuestions = questions.filter((_, i) => i !== index);
    setQuestions(newQuestions.map((q, i) => ({ ...q, order: i })));
  };

  // 更新问题
  const updateQuestion = (index: number, field: keyof SurveyQuestion, value: any) => {
    const newQuestions = [...questions];
    newQuestions[index] = { ...newQuestions[index], [field]: value };
    setQuestions(newQuestions);
  };

  // 上移问题
  const moveQuestionUp = (index: number) => {
    if (index === 0) return;
    const newQuestions = [...questions];
    [newQuestions[index], newQuestions[index - 1]] = [newQuestions[index - 1], newQuestions[index]];
    setQuestions(newQuestions.map((q, i) => ({ ...q, order: i })));
  };

  // 下移问题
  const moveQuestionDown = (index: number) => {
    if (index === questions.length - 1) return;
    const newQuestions = [...questions];
    [newQuestions[index], newQuestions[index + 1]] = [newQuestions[index + 1], newQuestions[index]];
    setQuestions(newQuestions.map((q, i) => ({ ...q, order: i })));
  };

  // 保存配置
  const saveConfig = async () => {
    if (!currentEvent?.id) {
      toast.error("请先选择活动");
      return;
    }

    setSaving(true);
    try {
      // 保存调查配置
      await request(`/surveys/event/${currentEvent.id}`, {
        method: "PUT",
        body: {
          enabled: surveyEnabled,
          title: surveyTitle,
          questions,
        },
      });

      // 保存免责声明配置
      await request(`/disclaimers/event/${currentEvent.id}`, {
        method: "PUT",
        body: {
          enabled: disclaimerEnabled,
          title: disclaimerTitle,
          text: disclaimerText,
          require_signature: requireSignature,
        },
      });

      toast.success("配置保存成功");
    } catch (error) {
      console.error("保存配置失败:", error);
      toast.error("保存失败，请重试");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="w-12 h-12 rounded-2xl bg-white/5 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col p-6 gap-6 overflow-hidden">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">来宾互动配置</h1>
          <p className="text-white/60 mt-1">配置调查问卷和免责声明</p>
        </div>
        <Button variant="primary" onClick={saveConfig} disabled={saving} className="gap-2">
          <Save size={18} />
          {saving ? "保存中..." : "保存配置"}
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto pr-2 -mr-2 space-y-8">
        {/* 调查问卷配置 */}
        <section className="bg-white/5 rounded-xl p-6 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-white">调查问卷</h2>
            <button
              onClick={() => setSurveyEnabled(!surveyEnabled)}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                surveyEnabled ? "bg-violet-500" : "bg-white/20"
              }`}
            >
              <motion.div
                className="absolute top-1 left-1 w-4 h-4 bg-white rounded-full"
                animate={{ x: surveyEnabled ? 24 : 0 }}
                transition={{ type: "spring", stiffness: 500, damping: 30 }}
              />
            </button>
          </div>

          {surveyEnabled && (
            <div className="space-y-6">
              <div>
                <label className="text-white/70 text-sm block mb-2">问卷标题</label>
                <input
                  type="text"
                  value={surveyTitle}
                  onChange={(e) => setSurveyTitle(e.target.value)}
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:border-violet-500 transition-colors"
                />
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-white font-medium">问题列表</h3>
                  <Button variant="secondary" size="sm" onClick={addQuestion} className="gap-2">
                    <Plus size={16} />
                    添加问题
                  </Button>
                </div>

                {questions.length === 0 ? (
                  <p className="text-white/40 py-8 text-center">暂无问题，点击上方按钮添加</p>
                ) : (
                  questions.map((question, index) => (
                    <div key={question.id} className="bg-white/5 rounded-lg p-4 space-y-4 border border-white/10">
                      <div className="flex items-center gap-3">
                        <GripVertical size={20} className="text-white/40" />
                        <span className="text-white/70 font-medium min-w-[24px]">{index + 1}.</span>
                        <input
                          type="text"
                          value={question.text}
                          onChange={(e) => updateQuestion(index, "text", e.target.value)}
                          placeholder="输入问题描述"
                          className="flex-1 px-3 py-2 bg-transparent border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:border-violet-500 transition-colors"
                        />
                        <select
                          value={question.type}
                          onChange={(e) => updateQuestion(index, "type", e.target.value)}
                          className={getGlassSelectClassName("rounded-lg px-3 py-2 text-sm")}
                        >
                          {questionTypes.map((type) => (
                            <option key={type.value} value={type.value} className={GLASS_SELECT_OPTION_CLASS_NAME}>
                              {type.label}
                            </option>
                          ))}
                        </select>
                        <label className="flex items-center gap-2 px-2">
                          <input
                            type="checkbox"
                            checked={question.required}
                            onChange={(e) => updateQuestion(index, "required", e.target.checked)}
                            className="w-4 h-4 rounded border-white/30 bg-white/5 text-violet-500 focus:ring-violet-500"
                          />
                          <span className="text-white/70 text-sm">必填</span>
                        </label>
                        <button
                          onClick={() => moveQuestionUp(index)}
                          disabled={index === 0}
                          className="p-2 text-white/40 hover:text-white disabled:opacity-30"
                        >
                          <ChevronUp size={18} />
                        </button>
                        <button
                          onClick={() => moveQuestionDown(index)}
                          disabled={index === questions.length - 1}
                          className="p-2 text-white/40 hover:text-white disabled:opacity-30"
                        >
                          <ChevronDown size={18} />
                        </button>
                        <button
                          onClick={() => removeQuestion(index)}
                          className="p-2 text-red-400 hover:text-red-300"
                        >
                          <Trash2 size={18} />
                        </button>
                      </div>

                      {question.type === "multiple_choice" && (
                        <div className="pl-12 space-y-2">
                          <div className="text-white/60 text-sm mb-2">选项</div>
                          {question.options.map((option, optIndex) => (
                            <div key={optIndex} className="flex items-center gap-2">
                              <input
                                type="text"
                                value={option}
                                onChange={(e) => {
                                  const newOptions = [...question.options];
                                  newOptions[optIndex] = e.target.value;
                                  updateQuestion(index, "options", newOptions);
                                }}
                                className="flex-1 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:border-violet-500 transition-colors"
                                placeholder={`选项 ${optIndex + 1}`}
                              />
                              <button
                                onClick={() => {
                                  const newOptions = question.options.filter((_, i) => i !== optIndex);
                                  updateQuestion(index, "options", newOptions);
                                }}
                                className="p-2 text-red-400 hover:text-red-300"
                              >
                                <Trash2 size={16} />
                              </button>
                            </div>
                          ))}
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => {
                              const newOptions = [...question.options, ""];
                              updateQuestion(index, "options", newOptions);
                            }}
                            className="mt-2"
                          >
                            <Plus size={14} />
                            添加选项
                          </Button>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </section>

        {/* 免责声明配置 */}
        <section className="bg-white/5 rounded-xl p-6 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-white">免责声明</h2>
            <button
              onClick={() => setDisclaimerEnabled(!disclaimerEnabled)}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                disclaimerEnabled ? "bg-violet-500" : "bg-white/20"
              }`}
            >
              <motion.div
                className="absolute top-1 left-1 w-4 h-4 bg-white rounded-full"
                animate={{ x: disclaimerEnabled ? 24 : 0 }}
                transition={{ type: "spring", stiffness: 500, damping: 30 }}
              />
            </button>
          </div>

          {disclaimerEnabled && (
            <div className="space-y-6">
              <div>
                <label className="text-white/70 text-sm block mb-2">标题</label>
                <input
                  type="text"
                  value={disclaimerTitle}
                  onChange={(e) => setDisclaimerTitle(e.target.value)}
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:border-violet-500 transition-colors"
                />
              </div>

              <div>
                <label className="text-white/70 text-sm block mb-2">内容</label>
                <textarea
                  value={disclaimerText}
                  onChange={(e) => setDisclaimerText(e.target.value)}
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:border-violet-500 transition-colors min-h-[200px] resize-none"
                  placeholder="输入免责声明内容..."
                />
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="require_signature"
                  checked={requireSignature}
                  onChange={(e) => setRequireSignature(e.target.checked)}
                  className="w-4 h-4 rounded border-white/30 bg-white/5 text-violet-500 focus:ring-violet-500"
                />
                <label htmlFor="require_signature" className="text-white/70">
                  需要用户签名确认
                </label>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
