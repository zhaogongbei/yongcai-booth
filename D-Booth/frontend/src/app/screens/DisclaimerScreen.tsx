import React, { useState, useEffect } from "react";
import { motion } from "motion/react";
import { Check, X, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { request } from "@/lib/api";
import { Button } from "@/app/components/ui/button";
import { useSettings } from "@/app/stores/useSettings";
import { useCaptureFlow } from "@/app/stores/useCaptureFlow";

interface DisclaimerConfig {
  enabled: boolean;
  title: string;
  text: string;
  require_signature: boolean;
}

export function DisclaimerScreen({ onComplete, navigate }: { onComplete?: () => void; navigate?: (screen: any) => void }) {
  const { currentEvent } = useSettings();
  const { currentSessionId } = useCaptureFlow();
  const [loading, setLoading] = useState(true);
  const [disclaimer, setDisclaimer] = useState<DisclaimerConfig | null>(null);
  const [agreed, setAgreed] = useState(false);

  useEffect(() => {
    if (!currentEvent?.id) return;

    const loadDisclaimer = async () => {
      try {
        const response = await request<DisclaimerConfig>(`/disclaimers/event/${currentEvent.id}`);
        if (!response.enabled) {
          toast.info("当前活动没有启用免责声明");
          if (onComplete) onComplete();
          return;
        }

        setDisclaimer(response);
      } catch (error) {
        console.error("加载免责声明失败:", error);
        toast.error("加载免责声明失败");
        if (onComplete) onComplete();
      } finally {
        setLoading(false);
      }
    };

    loadDisclaimer();
  }, [currentEvent?.id, onComplete]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="w-12 h-12 rounded-2xl bg-white/5 animate-pulse" />
      </div>
    );
  }

  if (!disclaimer) {
    return null;
  }

  const handleAgree = async () => {
    if (!agreed) {
      toast.error("请先阅读并同意免责声明");
      return;
    }

    if (!currentSessionId || !currentEvent?.id) {
      toast.error("会话不存在，请重试");
      return;
    }

    try {
      await request("/disclaimers/accept", {
        method: "POST",
        body: {
          event_id: currentEvent.id,
          session_id: currentSessionId,
        },
      });

      toast.success("已确认免责声明");
      if (disclaimer.require_signature) {
        navigate?.("signature");
      } else {
        if (onComplete) onComplete();
      }
    } catch (error) {
      console.error("提交失败:", error);
      toast.error("提交失败，请重试");
    }
  };

  const handleDisagree = () => {
    toast.error("您必须同意免责声明才能继续使用服务");
  };

  return (
    <div className="flex-1 flex flex-col p-8 md:p-12 overflow-hidden">
      <div className="max-w-4xl mx-auto w-full flex flex-col h-full gap-8">
        <div className="text-center space-y-4">
          <h1 className="text-3xl font-bold text-white">{disclaimer.title}</h1>
          <p className="text-white/60">请仔细阅读以下条款</p>
        </div>

        {/* 内容区域 */}
        <div className="flex-1 bg-white/5 rounded-xl p-6 border border-white/10 overflow-y-auto">
          <div className="text-white/80 text-lg leading-relaxed whitespace-pre-line">
            {disclaimer.text}
          </div>
        </div>

        {/* 同意选项 */}
        <div className="space-y-6">
          <label className="flex items-start gap-4 p-4 bg-white/5 rounded-xl cursor-pointer">
            <input
              type="checkbox"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
              className="w-6 h-6 mt-1 text-violet-500 border-white/30 bg-white/5 focus:ring-violet-500 rounded"
            />
            <div className="space-y-1">
              <p className="text-white font-medium">我已仔细阅读并完全理解以上所有条款</p>
              <p className="text-white/60 text-sm">我同意承担使用本服务所产生的所有责任和风险</p>
            </div>
          </label>

          <div className="flex gap-4">
            <Button
              variant="secondary"
              className="flex-1 gap-2"
              onClick={handleDisagree}
            >
              <X size={18} />
              不同意
            </Button>
            <Button
              variant="primary"
              className="flex-1 gap-2"
              onClick={handleAgree}
              disabled={!agreed}
            >
              <Check size={18} />
              我已阅读并同意
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
