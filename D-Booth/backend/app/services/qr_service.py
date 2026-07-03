import base64
import io
import urllib.parse

import qrcode

from app.core.config import settings


class QRService:
    """二维码服务：WiFi QR、WhatsApp等"""

    @staticmethod
    def generate_wifi_qr(ssid: str, password: str, encryption: str = "WPA2") -> str:
        """
        生成WiFi连接二维码
        返回base64编码的PNG图片
        """
        wifi_string = f"WIFI:S:{ssid};T:{encryption};P:{password};;"
        return QRService._generate_qr_base64(wifi_string)

    @staticmethod
    def generate_whatsapp_url(phone_number: str, message: str = "") -> str:
        """生成WhatsApp分享链接"""
        cleaned_number = phone_number.replace("+", "").replace(" ", "").replace("-", "")
        url = f"https://wa.me/{cleaned_number}"
        if message:
            url += f"?text={urllib.parse.quote(message)}"
        return url

    @staticmethod
    def generate_share_qr(share_url: str) -> str:
        """生成分享链接的二维码"""
        return QRService._generate_qr_base64(share_url)

    @staticmethod
    def _generate_qr_base64(data: str) -> str:
        """生成二维码并返回base64编码的图片字符串"""
        qr = qrcode.QRCode(
            version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode('utf-8')}"


qr_service = QRService()
