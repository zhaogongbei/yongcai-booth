import React, { useRef, useState, useEffect } from "react";
import { motion } from "motion/react";
import { Check, X, RefreshCcw, PenTool, Save, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import { request } from "@/lib/api";
import { Button } from "@/app/components/ui/button";
import { useCaptureFlow } from "@/app/stores/useCaptureFlow";

export function SignatureScreen({ onComplete, navigate }: { onComplete?: () => void; navigate?: (screen: any) => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [strokeColor, setStrokeColor] = useState("#000000");
  const [strokeWidth, setStrokeWidth] = useState(2);
  const [hasDrawn, setHasDrawn] = useState(false);
  const { sessionId: currentSessionId } = useCaptureFlow();

  const colors = [
    { value: "#000000", label: "黑色" },
    { value: "#0066cc", label: "蓝色" },
    { value: "#cc0000", label: "红色" },
  ];

  const widths = [
    { value: 2, label: "细", size: "w-3 h-3" },
    { value: 4, label: "中", size: "w-5 h-5" },
    { value: 6, label: "粗", size: "w-7 h-7" },
  ];

  // 初始化canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // 设置canvas尺寸
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;

    // 背景白色
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.lineCap = "round";
    ctx.lineJoin = "round";
  }, []);

  // 开始绘制
  const startDrawing = (e: React.MouseEvent | React.TouchEvent) => {
    setIsDrawing(true);
    setHasDrawn(true);
    draw(e);
  };

  // 结束绘制
  const stopDrawing = () => {
    setIsDrawing(false);
  };

  // 绘制
  const draw = (e: React.MouseEvent | React.TouchEvent) => {
    if (!isDrawing) return;

    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    let clientX, clientY;
    if ("touches" in e) {
      clientX = e.touches[0].clientX;
      clientY = e.touches[0].clientY;
    } else {
      clientX = e.clientX;
      clientY = e.clientY;
    }

    const rect = canvas.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;

    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = strokeWidth;

    if (isDrawing) {
      ctx.lineTo(x, y);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(x, y);
    }
  };

  // 清除画布
  const clearCanvas = () => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    setHasDrawn(false);
  };

  // 保存签名
  const saveSignature = async () => {
    if (!hasDrawn) {
      toast.error("请先绘制签名");
      return;
    }

    if (!currentSessionId) {
      toast.error("会话不存在，请重试");
      return;
    }

    try {
      const canvas = canvasRef.current;
      if (!canvas) return;

      // 转换为PNG
      const blob = await new Promise<Blob | null>((resolve) => {
        canvas.toBlob(resolve, "image/png");
      });

      if (!blob) {
        throw new Error("生成签名图片失败");
      }

      // 创建FormData
      const formData = new FormData();
      formData.append("signature_file", blob, "signature.png");

      const response = await request(`/signatures?session_id=${currentSessionId}`, {
        method: "POST",
        body: formData,
        // 移除Content-Type，让浏览器自动设置multipart/form-data边界
        headers: {},
      });

      toast.success("签名保存成功");
      if (onComplete) onComplete();
      if (navigate) navigate("camera");
    } catch (error) {
      console.error("保存签名失败:", error);
      toast.error("保存签名失败，请重试");
    }
  };

  return (
    <div className="flex-1 flex flex-col p-6 gap-6 overflow-hidden">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">签名采集</h1>
          <p className="text-white/60 mt-1">请在下方区域绘制您的签名</p>
        </div>
      </div>

      <div className="flex-1 flex flex-col md:flex-row gap-6 overflow-hidden">
        {/* 左侧: 画布 */}
        <div className="flex-1 flex flex-col gap-4">
          <div
            className="relative flex-1 bg-white rounded-xl overflow-hidden border-2 border-white/10 shadow-lg"
            style={{ touchAction: "none" }}
          >
            <canvas
              ref={canvasRef}
              className="w-full h-full cursor-crosshair"
              onMouseDown={startDrawing}
              onMouseMove={draw}
              onMouseUp={stopDrawing}
              onMouseLeave={stopDrawing}
              onTouchStart={startDrawing}
              onTouchMove={draw}
              onTouchEnd={stopDrawing}
            />
            {!hasDrawn && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="flex flex-col items-center gap-2">
                  <PenTool size={48} className="text-gray-300" />
                  <p className="text-gray-400 text-lg">请在此处签名</p>
                </div>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between">
            <Button
              variant="secondary"
              onClick={clearCanvas}
              className="gap-2"
            >
              <RefreshCcw size={18} />
              清除
            </Button>

            <Button
              variant="primary"
              onClick={saveSignature}
              disabled={!hasDrawn}
              className="gap-2"
            >
              <Save size={18} />
              确认签名
            </Button>
          </div>
        </div>

        {/* 右侧: 工具栏 */}
        <div className="w-full md:w-64 bg-white/5 rounded-xl p-6 flex flex-col gap-8">
          <div className="space-y-4">
            <h3 className="text-white font-semibold">笔触颜色</h3>
            <div className="flex gap-3">
              {colors.map((color) => (
                <button
                  key={color.value}
                  onClick={() => setStrokeColor(color.value)}
                  className={`w-10 h-10 rounded-full border-2 transition-all ${
                    strokeColor === color.value
                      ? "border-white scale-110 shadow-lg"
                      : "border-transparent hover:border-white/50"
                  }`}
                  style={{ backgroundColor: color.value }}
                  aria-label={color.label}
                />
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-white font-semibold">笔触粗细</h3>
            <div className="flex gap-3">
              {widths.map((width) => (
                <button
                  key={width.value}
                  onClick={() => setStrokeWidth(width.value)}
                  className={`w-12 h-12 rounded-lg border-2 flex items-center justify-center transition-all ${
                    strokeWidth === width.value
                      ? "border-violet-500 bg-violet-500/20 scale-110"
                      : "border-white/10 bg-white/5 hover:border-white/30"
                  }`}
                  aria-label={width.label}
                >
                  <div
                    className={`rounded-full bg-white ${width.size}`}
                  />
                </button>
              ))}
            </div>
          </div>

          <div className="pt-6 border-t border-white/10">
            <Button
              variant="secondary"
              className="w-full gap-2"
              onClick={() => navigate?.("camera")}
            >
              <X size={18} />
              取消
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}