import { useState, useEffect } from "react";
import { QrCode, Mail, Plus, Camera, Copy, MessageCircle, Send, Wifi } from "lucide-react";
import { motion } from "motion/react";
import QRCodeLib from "qrcode";
import { GlassCard } from "../components/GlassCard";
import { GLASS_SELECT_OPTION_CLASS_NAME, getGlassSelectClassName } from "../components/glassSelect";
import { GlowBtn } from "../components/GlowBtn";
import { useCaptureFlow } from "../stores/useCaptureFlow";
import { showToast } from "../stores/useToast";
import { createShare, sendShareEmail, sendShareSMS, getShareSettings, type ShareSettings } from "../lib/api";
import type { Screen } from "../types";

interface SharingScreenProps {
  navigate?: (s: Screen) => void;
}

export function SharingScreen({ navigate }: SharingScreenProps) {
  const [shareLink, setShareLink] = useState("");
  const [qrCodeDataUrl, setQrCodeDataUrl] = useState("");
  const [copied, setCopied] = useState(false);
  const [creating, setCreating] = useState(false);
  const [showEmailDialog, setShowEmailDialog] = useState(false);
  const [showPhoneDialog, setShowPhoneDialog] = useState(false);
  const [showWifiDialog, setShowWifiDialog] = useState(false);
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [countryCode, setCountryCode] = useState("+86");
  const [sending, setSending] = useState(false);
  const [settings, setSettings] = useState<ShareSettings | null>(null);
  const [wifiQrCode, setWifiQrCode] = useState("");

  const { selectedPhoto, authToken, eventId } = useCaptureFlow();
  const photoUrl = selectedPhoto?.url;
  const shareUnavailableReason = !selectedPhoto
    ? "请先完成拍照"
    : !authToken
      ? "请从真实活动进入拍照后再分享"
      : !selectedPhoto.serverPhotoId
        ? (selectedPhoto.uploadError ? "照片上传失败，无法分享" : "照片正在上传，完成后可分享")
        : null;

  // Generate QR code when share link changes
  useEffect(() => {
    if (!shareLink) {
      setQrCodeDataUrl("");
      return;
    }

    QRCodeLib.toDataURL(shareLink, {
      width: 300,
      margin: 2,
      color: {
        dark: "#8b5cf6",  // 紫色，匹配主题
        light: "#ffffff"
      },
      errorCorrectionLevel: "M"
    })
      .then(setQrCodeDataUrl)
      .catch((err) => {
        console.error("QR code generation failed:", err);
        showToast.error("二维码生成失败");
      });
  }, [shareLink]);

  // 加载分享配置
  useEffect(() => {
    if (!eventId || !authToken) return;
    getShareSettings(eventId, authToken)
      .then(setSettings)
      .catch(err => console.error("Failed to load share settings:", err));
  }, [eventId, authToken]);

  // 生成WiFi二维码
  useEffect(() => {
    if (!settings?.wifi.ssid) return;
    const wifiString = `WIFI:S:${settings.wifi.ssid};T:${settings.wifi.encryption};P:${settings.wifi.password};;`;
    QRCodeLib.toDataURL(wifiString, {
      width: 300,
      margin: 2,
      color: { dark: "#10b981", light: "#ffffff" },
      errorCorrectionLevel: "M"
    })
      .then(setWifiQrCode)
      .catch(err => console.error("WiFi QR generation failed:", err));
  }, [settings?.wifi]);

  const shareMethods = [
    { icon: QrCode, label: "二维码下载", color: "from-violet-600 to-violet-800", channel: "qr" },
    { icon: Mail, label: "邮件发送", color: "from-orange-600 to-orange-800", channel: "email", action: () => setShowEmailDialog(true) },
    { icon: MessageCircle, label: "短信发送", color: "from-blue-500 to-blue-700", channel: "sms", action: () => setShowPhoneDialog(true) },
    { icon: Send, label: "WhatsApp", color: "from-green-500 to-green-700", channel: "whatsapp", action: () => handleWhatsAppShare() },
    { icon: Wifi, label: "WiFi连接", color: "from-cyan-500 to-cyan-700", channel: "wifi", action: () => setShowWifiDialog(true) },
  ];

  // 真实创建分享短链（后端 POST /shares）
  const handleCreateLink = async () => {
    const photoId = selectedPhoto?.serverPhotoId;
    if (shareUnavailableReason || !photoId || !authToken) {
      showToast.error(shareUnavailableReason || "无法创建分享链接");
      return;
    }
    setCreating(true);
    try {
      const share = await createShare({ photoId, channel: "link", token: authToken });
      setShareLink(share.full_url);
      setCopied(false);
      showToast.success("分享链接已创建，有效期 7 天");
    } catch (err) {
      showToast.error(err instanceof Error ? err.message : "创建分享失败");
    } finally {
      setCreating(false);
    }
  };

  // 真实分享到某渠道（后端 POST /shares，记录 channel）
  const handleShare = async (channel: string, action?: () => void) => {
    if (action) {
      action();
      return;
    }

    const photoId = selectedPhoto?.serverPhotoId;
    if (shareUnavailableReason || !photoId || !authToken) {
      showToast.error(shareUnavailableReason || "无法分享照片");
      return;
    }
    try {
      await createShare({ photoId, channel, token: authToken });
      showToast.success(`已通过${channel}分享`);
    } catch (err) {
      showToast.error(err instanceof Error ? err.message : "分享失败");
    }
  };

  // 发送邮件
  const handleSendEmail = async () => {
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      showToast.error("请输入有效的邮箱地址");
      return;
    }
    if (!shareLink) {
      showToast.error("请先创建分享链接");
      return;
    }

    setSending(true);
    try {
      if (shareUnavailableReason || !selectedPhoto?.serverPhotoId || !authToken || !eventId || !photoUrl) {
        showToast.error(shareUnavailableReason || "无法发送邮件");
        return;
      }

      await sendShareEmail({
        toEmail: email,
        eventId: eventId!,
        photoUrls: [photoUrl],
        shareUrl: shareLink,
        token: authToken
      });

      showToast.success("邮件已发送");
      setShowEmailDialog(false);
      setEmail("");
    } catch (err) {
      showToast.error(err instanceof Error ? err.message : "邮件发送失败");
    } finally {
      setSending(false);
    }
  };

  // 发送短信
  const handleSendSMS = async () => {
    if (!phone || phone.length < 8) {
      showToast.error("请输入有效的手机号");
      return;
    }
    if (!shareLink) {
      showToast.error("请先创建分享链接");
      return;
    }

    setSending(true);
    try {
      if (shareUnavailableReason || !selectedPhoto?.serverPhotoId || !authToken || !eventId) {
        showToast.error(shareUnavailableReason || "无法发送短信");
        return;
      }

      await sendShareSMS({
        toPhone: phone,
        eventId: eventId!,
        shareUrl: shareLink,
        countryCode: countryCode,
        token: authToken
      });

      showToast.success("短信已发送");
      setShowPhoneDialog(false);
      setPhone("");
    } catch (err) {
      showToast.error(err instanceof Error ? err.message : "短信发送失败");
    } finally {
      setSending(false);
    }
  };

  // WhatsApp分享
  const handleWhatsAppShare = () => {
    if (!shareLink) {
      showToast.error("请先创建分享链接");
      return;
    }
    const message = encodeURIComponent(`你好！这是您的照片：${shareLink}`);
    window.open(`https://wa.me/?text=${message}`, "_blank");
    handleShare("whatsapp");
  };

  const handleCopy = async () => {
    if (!shareLink) return;
    try {
      await navigator.clipboard.writeText(shareLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback: do nothing
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden p-5 gap-5">
      {/* Left - photo + sharing */}
      <div className="flex-1 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">分享中心</h2>
            <p className="text-xs text-white/40 mt-0.5">
              {shareUnavailableReason ?? "基于当前已上传照片创建真实分享链接"}
            </p>
          </div>
          <GlowBtn size="sm" variant="primary" onClick={handleCreateLink} disabled={creating}><Plus size={14} />{creating ? "创建中…" : "创建分享链接"}</GlowBtn>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* Photo preview */}
          <GlassCard className="p-4">
            <div className="text-xs text-white/40 mb-3">最新照片</div>
            {photoUrl ? (
              <>
                <div className="aspect-[3/4] rounded-xl overflow-hidden border border-white/10 mb-3">
                  <img src={photoUrl}
                    alt="latest photo" className="w-full h-full object-cover" loading="lazy" />
                </div>
                <div className="text-xs text-white/60">photo_{selectedPhoto?.id}.jpg</div>
                <div className="text-[10px] text-white/30 mt-0.5">
                  拍摄时间：{selectedPhoto ? new Date(selectedPhoto.timestamp).toLocaleString() : ""}
                </div>
                <div className="text-[10px] text-white/30">滤镜：{selectedPhoto?.filter ?? "-"}</div>
              </>
            ) : (
              <div className="flex aspect-[3/4] flex-col items-center justify-center rounded-xl border border-white/10 text-center">
                <Camera size={28} className="text-white/25" />
                <div className="mt-3 text-xs text-white/45">还没有可分享照片</div>
                <GlowBtn className="mt-4" size="sm" variant="primary" onClick={() => navigate?.("camera")}>
                  <Camera size={13} />返回拍照
                </GlowBtn>
              </div>
            )}
          </GlassCard>

          {/* QR Code */}
          <GlassCard className="p-4 flex flex-col items-center justify-center">
            <div className="text-xs text-white/40 mb-4">扫码下载照片</div>
            {qrCodeDataUrl ? (
              <div className="w-40 h-40 bg-white rounded-2xl p-2 mb-4 relative">
                <img
                  src={qrCodeDataUrl}
                  alt="QR Code"
                  className="w-full h-full"
                />
              </div>
            ) : (
              <div className="w-40 h-40 bg-white/5 rounded-2xl mb-4 flex items-center justify-center border border-white/10">
                <div className="text-center">
                  <QrCode size={32} className="text-white/30 mx-auto mb-2" />
                  <div className="text-xs text-white/30">
                    {shareLink ? "生成中..." : "创建链接后显示"}
                  </div>
                </div>
              </div>
            )}
            <div className="text-xs text-white/60 text-center">扫描二维码下载照片</div>
            <div className="text-[10px] text-white/30 mt-1">有效期 24 小时</div>
          </GlassCard>
        </div>

        {/* Share methods */}
        <GlassCard className="p-4">
          <div className="text-xs text-white/40 mb-3">快速分享</div>
          <div className="grid grid-cols-4 gap-3">
            {shareMethods.map(m => (
              <motion.button key={m.label} whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                onClick={() => handleShare(m.channel, m.action)}
                className={`flex flex-col items-center gap-2 px-2 py-3 rounded-xl bg-gradient-to-br ${m.color} disabled:opacity-45`}
                disabled={m.channel !== "wifi" && Boolean(shareUnavailableReason)}
              >
                <m.icon size={22} className="text-white" />
                <span className="text-xs text-white/80">{m.label}</span>
              </motion.button>
            ))}
          </div>
        </GlassCard>

        {/* Share link */}
        <GlassCard className="p-4">
          <div className="text-xs text-white/40 mb-2">分享链接</div>
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white/50 font-mono truncate">
              {shareLink}
            </div>
            <GlowBtn size="sm" variant="outline" onClick={handleCopy}><Copy size={13} />{copied ? "已复制" : "复制"}</GlowBtn>
          </div>
        </GlassCard>
      </div>

      {/* Right - stats + mobile preview */}
      <div className="w-64 space-y-4">
        {/* Mobile preview */}
        <GlassCard className="p-4">
          <div className="text-xs text-white/40 mb-3">手机预览</div>
          <div className="mx-auto w-36 relative">
            <div className="bg-gray-900 rounded-3xl border border-gray-700 p-2 shadow-2xl">
              <div className="bg-white rounded-2xl overflow-hidden aspect-[9/16]">
                {photoUrl ? (
                  <img src={photoUrl}
                    alt="mobile preview" className="w-full h-full object-cover" loading="lazy" />
                ) : (
                  <div className="flex h-full items-center justify-center text-[10px] text-gray-400">暂无照片</div>
                )}
              </div>
            </div>
            {eventId && (
              <div className="mt-2 bg-gradient-to-r from-violet-600 to-pink-600 text-white text-center rounded-xl py-2 text-xs font-bold">
                当前活动
              </div>
            )}
            <div className="mt-1.5 bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 text-center rounded-xl py-2 text-xs">
              {shareLink ? "下载照片" : "等待分享链接"}
            </div>
          </div>
        </GlassCard>

        {/* Current status */}
        <GlassCard className="p-4 space-y-3">
          <div className="text-xs text-white/60 font-semibold">当前分享状态</div>
          {[
            { label: "当前照片", value: selectedPhoto?.serverPhotoId ? "已上传" : selectedPhoto ? "等待上传" : "无" },
            { label: "分享链接", value: shareLink ? "已创建" : "未创建" },
            { label: "邮件/短信", value: shareLink ? "可发送" : "需先创建链接" },
          ].map(s => (
            <div key={s.label} className="flex items-center justify-between">
              <span className="text-xs text-white/40">{s.label}</span>
              <span className="text-xs font-medium text-white">{s.value}</span>
            </div>
          ))}
        </GlassCard>
      </div>

      {/* Email Dialog */}
      {showEmailDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setShowEmailDialog(false)}>
          <div className="bg-gray-900 rounded-2xl p-6 w-full max-w-md border border-white/10" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-white mb-4">邮件分享</h3>
            <input
              type="email"
              placeholder="请输入邮箱地址"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm outline-none focus:border-violet-500 mb-4"
            />
            <div className="flex gap-3 justify-end">
              <GlowBtn size="sm" variant="outline" onClick={() => setShowEmailDialog(false)}>取消</GlowBtn>
              <GlowBtn size="sm" variant="primary" onClick={handleSendEmail} disabled={sending}>
                {sending ? "发送中..." : "发送邮件"}
              </GlowBtn>
            </div>
          </div>
        </div>
      )}

      {/* Phone Dialog */}
      {showPhoneDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setShowPhoneDialog(false)}>
          <div className="bg-gray-900 rounded-2xl p-6 w-full max-w-md border border-white/10" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-white mb-4">短信分享</h3>
            <div className="flex gap-2 mb-4">
              <select
                value={countryCode}
                onChange={e => setCountryCode(e.target.value)}
                className={getGlassSelectClassName("rounded-xl px-3 py-3 text-sm")}
              >
                <option value="+86" className={GLASS_SELECT_OPTION_CLASS_NAME}>+86 中国</option>
                <option value="+1" className={GLASS_SELECT_OPTION_CLASS_NAME}>+1 美国</option>
                <option value="+44" className={GLASS_SELECT_OPTION_CLASS_NAME}>+44 英国</option>
                <option value="+81" className={GLASS_SELECT_OPTION_CLASS_NAME}>+81 日本</option>
                <option value="+82" className={GLASS_SELECT_OPTION_CLASS_NAME}>+82 韩国</option>
                <option value="+852" className={GLASS_SELECT_OPTION_CLASS_NAME}>+852 香港</option>
              </select>
              <input
                type="tel"
                placeholder="请输入手机号"
                value={phone}
                onChange={e => setPhone(e.target.value.replace(/\D/g, ''))}
                maxLength={15}
                className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm outline-none focus:border-violet-500"
              />
            </div>
            <div className="flex gap-3 justify-end">
              <GlowBtn size="sm" variant="outline" onClick={() => setShowPhoneDialog(false)}>取消</GlowBtn>
              <GlowBtn size="sm" variant="primary" onClick={handleSendSMS} disabled={sending}>
                {sending ? "发送中..." : "发送短信"}
              </GlowBtn>
            </div>
          </div>
        </div>
      )}

      {/* WiFi Dialog */}
      {showWifiDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setShowWifiDialog(false)}>
          <div className="bg-gray-900 rounded-2xl p-6 w-full max-w-md border border-white/10" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-white mb-4">WiFi 连接</h3>
            {settings?.wifi.ssid ? (
              <div className="text-center space-y-4">
                <div className="text-sm text-white/60">
                  <div className="mb-1">SSID: <span className="text-white font-bold">{settings.wifi.ssid}</span></div>
                  <div>密码: <span className="text-white font-bold">{settings.wifi.password}</span></div>
                  <div className="text-[10px] text-white/30 mt-1">加密: {settings.wifi.encryption}</div>
                </div>
                {wifiQrCode && (
                  <div className="w-40 h-40 mx-auto bg-white rounded-2xl p-2">
                    <img src={wifiQrCode} alt="WiFi QR Code" className="w-full h-full" />
                  </div>
                )}
                <p className="text-xs text-white/40">扫描二维码连接WiFi</p>
              </div>
            ) : (
              <div className="text-center py-8">
                <Wifi size={40} className="text-white/20 mx-auto mb-3" />
                <p className="text-sm text-white/40">未配置WiFi信息</p>
                <p className="text-xs text-white/25 mt-1">请在设置中配置WiFi信息</p>
              </div>
            )}
            <div className="mt-4 flex justify-end">
              <GlowBtn size="sm" variant="outline" onClick={() => setShowWifiDialog(false)}>关闭</GlowBtn>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
