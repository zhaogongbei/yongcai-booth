import React, { useState, useEffect } from "react";
import { motion } from "motion/react";
import { Star, ChevronRight, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { request } from "@/lib/api";
import { Button } from "@/app/components/ui/button";
import { useSettings } from "@/app/stores/useSettings";
import { useCaptureFlow } from "@/app/stores/useCaptureFlow";

interface SurveyQuestion {
  id: string;
  type: "text_short" | "text_long" | "multiple_choice" | "rating";
  text: string;
  required: boolean;
  options: string[];
  order: number;
}

interface SurveyConfig {
  enabled: boolean;
  title: string;
  questions: SurveyQuestion[];
}

export function SurveyScreen({ onComplete, navigate }: { onComplete?: () => void; navigate?: (screen: any) => void }) {
  const { currentEvent } = useSettings();
  const { currentSessionId } = useCaptureFlow();
  const [loading, setLoading] = useState(true);
  const [questions, setQuestions] = useState<SurveyQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, string | number>>({});
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [surveyTitle, setSurveyTitle] = useState("");

  useEffect(() => {
    if (!currentEvent?.id) return;

    const loadSurvey = async () => {
      try {
        const response = await request<SurveyConfig>(`/surveys/event/${currentEvent.id}`);
        if (!response.enabled) {
          toast.info("当前活动没有启用问卷调查");
          if (onComplete) onComplete();
          return;
        }

        setSurveyTitle(response.title);
        setQuestions(response.questions || []);
      } catch (error) {
        console.error("加载调查失败:", error);
        toast.error("加载调查失败");
        if (onComplete) onComplete();
      } finally {
        setLoading(false);
      }
    };

    loadSurvey();
  }, [currentEvent?.id, onComplete]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="w-12 h-12 rounded-2xl bg-white/5 animate-pulse" />
      </div>
    );
  }

  if (questions.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 gap-4">
        <h2 className="text-2xl font-bold text-white">感谢参与</h2>
        <p className="text-white/60 text-center">当前活动没有设置调查问题</p>
        <Button variant="primary" onClick={() => onComplete?.()} className="mt-4">
          继续
        </Button>
      </div>
    );
  }

  const currentQuestion = questions[currentQuestionIndex];
  const isLastQuestion = currentQuestionIndex === questions.length - 1;

  // 验证当前问题
  const validateCurrent = () => {
    const answer = answers[currentQuestion.id];
    if (currentQuestion.required && (answer === undefined || answer === "")) {
      toast.error("此问题为必填项，请回答后继续");
      return false;
    }
    return true;
  };

  // 下一个问题
  const nextQuestion = () => {
    if (!validateCurrent()) return;

    if (isLastQuestion) {
      submitSurvey();
    } else {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    }
  };

  // 上一个问题
  const prevQuestion = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
    }
  };

  // 跳过问题
  const skipQuestion = () => {
    if (currentQuestion.required) {
      toast.error("此问题为必填项，无法跳过");
      return;
    }

    if (isLastQuestion) {
      submitSurvey();
    } else {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    }
  };

  // 提交调查
  const submitSurvey = async () => {
    if (!currentSessionId || !currentEvent?.id) {
      toast.error("会话不存在，请重试");
      return;
    }

    // 验证所有必填问题
    for (const question of questions) {
      if (question.required && (answers[question.id] === undefined || answers[question.id] === "")) {
        toast.error(`"${question.text}" 是必填项，请回答`);
        return;
      }
    }

    try {
      await request("/surveys/responses", {
        method: "POST",
        body: {
          event_id: currentEvent.id,
          session_id: currentSessionId,
          answers,
        },
      });

      toast.success("调查提交成功，感谢您的参与！");
      if (onComplete) onComplete();
    } catch (error) {
      console.error("提交调查失败:", error);
      toast.error("提交失败，请重试");
    }
  };

  // 渲染问题输入控件
  const renderQuestionInput = () => {
    switch (currentQuestion.type) {
      case "text_short":
        return (
          <input
            type="text"
            value={(answers[currentQuestion.id] as string) || ""}
            onChange={(e) => setAnswers({ ...answers, [currentQuestion.id]: e.target.value })}
            className="w-full px-6 py-4 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40 focus:outline-none focus:border-violet-500 transition-colors text-lg"
            placeholder="请输入您的回答..."
            autoFocus
          />
        );

      case "text_long":
        return (
          <textarea
            value={(answers[currentQuestion.id] as string) || ""}
            onChange={(e) => setAnswers({ ...answers, [currentQuestion.id]: e.target.value })}
            className="w-full px-6 py-4 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40 focus:outline-none focus:border-violet-500 transition-colors text-lg min-h-[150px] resize-none"
            placeholder="请输入您的回答..."
            autoFocus
          />
        );

      case "multiple_choice":
        return (
          <div className="space-y-3">
            {currentQuestion.options.map((option, index) => (
              <label
                key={index}
                className={`flex items-center p-4 rounded-xl border-2 cursor-pointer transition-all ${
                  answers[currentQuestion.id] === option
                    ? "border-violet-500 bg-violet-500/20"
                    : "border-white/10 bg-white/5 hover:border-white/30"
                }`}
              >
                <input
                  type="radio"
                  name={currentQuestion.id}
                  value={option}
                  checked={answers[currentQuestion.id] === option}
                  onChange={(e) => setAnswers({ ...answers, [currentQuestion.id]: e.target.value })}
                  className="w-5 h-5 text-violet-500 border-white/30 focus:ring-violet-500 mr-4"
                />
                <span className="text-white text-lg">{option}</span>
              </label>
            ))}
          </div>
        );

      case "rating":
        return (
          <div className="flex items-center justify-center gap-4 py-8">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                onClick={() => setAnswers({ ...answers, [currentQuestion.id]: star })}
                className="transition-transform hover:scale-110"
              >
                <Star
                  size={64}
                  className={`transition-colors ${
                    (answers[currentQuestion.id] as number) >= star
                      ? "text-yellow-400 fill-yellow-400"
                      : "text-white/20"
                  }`}
                />
              </button>
            ))}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="flex-1 flex flex-col p-8 md:p-12 overflow-hidden">
      <div className="max-w-3xl mx-auto w-full flex flex-col h-full gap-8">
        {/* 进度 */}
        <div className="space-y-3">
          <div className="flex items-center justify-between text-white/60 text-sm">
            <span>问题 {currentQuestionIndex + 1}/{questions.length}</span>
            <span>{Math.round(((currentQuestionIndex + 1) / questions.length) * 100)}% 完成</span>
          </div>
          <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-violet-500 to-purple-500"
              initial={{ width: 0 }}
              animate={{ width: `${((currentQuestionIndex + 1) / questions.length) * 100}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
        </div>

        {/* 问题内容 */}
        <motion.div
          key={currentQuestionIndex}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.3 }}
          className="flex-1 flex flex-col gap-6"
        >
          <div className="space-y-4">
            <div className="flex items-start gap-2">
              <h2 className="text-3xl font-bold text-white">{currentQuestion.text}</h2>
              {currentQuestion.required && (
                <AlertCircle size={20} className="text-red-400 mt-1" />
              )}
            </div>
            {!currentQuestion.required && (
              <p className="text-white/40 text-sm">可选</p>
            )}
          </div>

          <div className="flex-1">{renderQuestionInput()}</div>
        </motion.div>

        {/* 按钮 */}
        <div className="flex items-center justify-between pt-6 border-t border-white/10">
          <div>
            {currentQuestionIndex > 0 && (
              <Button variant="secondary" onClick={prevQuestion}>
                上一题
              </Button>
            )}
          </div>

          <div className="flex gap-4">
            {!currentQuestion.required && (
              <Button variant="secondary" onClick={skipQuestion}>
                跳过
              </Button>
            )}

            <Button variant="primary" onClick={nextQuestion} className="gap-2">
              {isLastQuestion ? "提交" : "下一题"}
              <ChevronRight size={18} />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
