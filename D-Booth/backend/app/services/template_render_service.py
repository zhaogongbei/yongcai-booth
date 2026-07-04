import io
from datetime import datetime
from typing import Any, Dict, List, Optional

import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageOps


class TemplateRenderService:
    @staticmethod
    def _open_photo(photo_bytes: bytes) -> Image.Image:
        photo = Image.open(io.BytesIO(photo_bytes))
        return ImageOps.exif_transpose(photo).convert("RGB")

    @staticmethod
    def _fit_photo(photo: Image.Image, width: int, height: int, crop_mode: str) -> Image.Image:
        width = max(1, width)
        height = max(1, height)
        if crop_mode == "stretch":
            return photo.resize((width, height), Image.Resampling.LANCZOS)

        photo_aspect = photo.width / photo.height
        target_aspect = width / height

        if crop_mode == "fit":
            fitted = Image.new("RGB", (width, height), "#f3f4f6")
            if photo_aspect > target_aspect:
                new_width = width
                new_height = int(new_width / photo_aspect)
            else:
                new_height = height
                new_width = int(new_height * photo_aspect)
            resized = photo.resize((max(1, new_width), max(1, new_height)), Image.Resampling.LANCZOS)
            fitted.paste(resized, ((width - resized.width) // 2, (height - resized.height) // 2))
            return fitted

        if photo_aspect > target_aspect:
            new_height = height
            new_width = int(new_height * photo_aspect)
        else:
            new_width = width
            new_height = int(new_width / photo_aspect)

        resized = photo.resize((max(1, new_width), max(1, new_height)), Image.Resampling.LANCZOS)
        left = max(0, (resized.width - width) // 2)
        top = max(0, (resized.height - height) // 2)
        return resized.crop((left, top, left + width, top + height))

    @staticmethod
    def _draw_frontend_text(draw: ImageDraw.ImageDraw, layer: Dict[str, Any]) -> None:
        props = layer.get("props") or {}
        text = props.get("content", "")
        text = text.replace("{date}", datetime.now().strftime("%Y-%m-%d"))
        text = text.replace("{time}", datetime.now().strftime("%H:%M:%S"))
        text = text.replace("{datetime}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        font_size = int(props.get("fontSize") or 24)
        try:
            font = ImageFont.truetype(props.get("fontFamily") or "arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

        x = int(layer.get("x", 0))
        y = int(layer.get("y", 0))
        width = int(layer.get("width", 100))
        height = int(layer.get("height", 40))
        color = props.get("color", "#000000")
        align = props.get("textAlign", "center")

        bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=4)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        if align == "left":
            text_x = x
        elif align == "right":
            text_x = x + width - text_width
        else:
            text_x = x + (width - text_width) / 2
        text_y = y + (height - text_height) / 2
        draw.multiline_text((text_x, text_y), text, font=font, fill=color, align=align, spacing=4)

    @staticmethod
    def _render_frontend_layout(template: Dict[str, Any], photos: List[bytes], dpi: int) -> bytes:
        paper_size = template.get("paperSize") or {}
        resolution = int(template.get("resolution") or dpi)
        canvas_width = int(float(paper_size.get("width", 101.6)) * resolution / 25.4)
        canvas_height = int(float(paper_size.get("height", 152.4)) * resolution / 25.4)

        background = template.get("background") or {}
        background_value = background.get("value") if background.get("type") == "color" else "#FFFFFF"
        image = Image.new("RGB", (max(1, canvas_width), max(1, canvas_height)), background_value)
        draw = ImageDraw.Draw(image)

        elements = sorted(template.get("elements") or [], key=lambda item: item.get("zIndex", 0))
        for layer in elements:
            if not layer.get("visible", True):
                continue

            layer_type = layer.get("type")
            x = int(layer.get("x", 0))
            y = int(layer.get("y", 0))
            width = int(layer.get("width", 100))
            height = int(layer.get("height", 100))
            props = layer.get("props") or {}

            try:
                if layer_type == "photo" and photos:
                    photo_number = max(1, int(props.get("photoNumber") or 1))
                    photo_bytes = photos[photo_number - 1] if len(photos) >= photo_number else photos[0]
                    photo = TemplateRenderService._open_photo(photo_bytes)
                    fitted = TemplateRenderService._fit_photo(photo, width, height, props.get("cropMode", "fill"))
                    image.paste(fitted, (x, y))
                elif layer_type == "text":
                    TemplateRenderService._draw_frontend_text(draw, layer)
                elif layer_type == "shape":
                    fill = props.get("fillColor", "#ffffff")
                    outline = props.get("strokeColor", "#000000")
                    stroke_width = int(props.get("strokeWidth") or 0)
                    box = [x, y, x + width, y + height]
                    if props.get("shapeType") == "ellipse":
                        draw.ellipse(box, fill=fill, outline=outline, width=stroke_width)
                    else:
                        draw.rectangle(box, fill=fill, outline=outline, width=stroke_width)
                elif layer_type == "qr_code":
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=10,
                        border=0,
                    )
                    qr.add_data(props.get("url", ""))
                    qr.make(fit=True)
                    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
                    qr_img = qr_img.resize((max(1, width), max(1, height)), Image.Resampling.NEAREST)
                    image.paste(qr_img, (x, y))
                elif layer_type in {"date", "datetime"}:
                    date_layer = {
                        **layer,
                        "props": {
                            "content": datetime.now().strftime("%Y-%m-%d"),
                            "fontSize": min(width, height, 48),
                            "color": "#111827",
                            "textAlign": "center",
                        },
                    }
                    TemplateRenderService._draw_frontend_text(draw, date_layer)
                elif layer_type == "image":
                    draw.rectangle([x, y, x + width, y + height], fill="#f3f4f6", outline="#d1d5db")
                    draw.text((x + width / 2, y + height / 2), "素材需替换", fill="#6b7280", anchor="mm")
            except Exception as e:
                print(f"Error rendering frontend template layer: {e}")

        output = io.BytesIO()
        image.save(output, format="JPEG", quality=95, dpi=(resolution, resolution))
        return output.getvalue()

    @staticmethod
    def render_template_to_image(
        template: Dict[str, Any], photos: List[bytes], dpi: int = 300
    ) -> bytes:
        """
        渲染模板为可打印图像
        :param template: 模板定义
        :param photos: 照片列表
        :param dpi: 输出DPI
        :return: JPEG图像字节
        """
        if "paperSize" in template and isinstance(template.get("elements"), list):
            return TemplateRenderService._render_frontend_layout(template, photos, dpi)

        # 获取模板配置
        paper_width = template.get("paper_width", 4 * dpi)  # 默认4x6英寸
        paper_height = template.get("paper_height", 6 * dpi)
        background_color = template.get("background_color", "#FFFFFF")
        orientation = template.get("orientation", "portrait")

        # 创建画布
        if orientation == "landscape":
            paper_width, paper_height = paper_height, paper_width

        image = Image.new("RGB", (int(paper_width), int(paper_height)), background_color)
        draw = ImageDraw.Draw(image)

        # 渲染图层
        layers = template.get("layers", [])
        photo_index = 0

        for layer in layers:
            layer_type = layer.get("type")

            if layer_type == "photo" and photo_index < len(photos):
                # 渲染照片图层
                try:
                    photo = Image.open(io.BytesIO(photos[photo_index]))
                    photo = ImageOps.exif_transpose(photo)  # 处理EXIF旋转

                    x = int(layer.get("x", 0) * dpi / 25.4)  # 转换mm为像素
                    y = int(layer.get("y", 0) * dpi / 25.4)
                    width = int(layer.get("width", 100) * dpi / 25.4)
                    height = int(layer.get("height", 150) * dpi / 25.4)

                    # 缩放裁剪
                    photo_aspect = photo.width / photo.height
                    target_aspect = width / height

                    if photo_aspect > target_aspect:
                        new_height = height
                        new_width = int(new_height * photo_aspect)
                    else:
                        new_width = width
                        new_height = int(new_width / photo_aspect)

                    photo = photo.resize((new_width, new_height), Image.Resampling.LANCZOS)

                    # 裁剪到目标尺寸
                    left = (new_width - width) // 2
                    top = (new_height - height) // 2
                    right = left + width
                    bottom = top + height
                    photo = photo.crop((left, top, right, bottom))

                    image.paste(photo, (x, y))
                    photo_index += 1
                except Exception as e:
                    print(f"Error rendering photo layer: {e}")

            elif layer_type == "text":
                # 渲染文本图层
                try:
                    text = layer.get("content", "")
                    # 变量替换
                    text = text.replace("{date}", datetime.now().strftime("%Y-%m-%d"))
                    text = text.replace("{time}", datetime.now().strftime("%H:%M:%S"))
                    text = text.replace("{datetime}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

                    x = int(layer.get("x", 0) * dpi / 25.4)
                    y = int(layer.get("y", 0) * dpi / 25.4)
                    font_size = int(layer.get("font_size", 12) * dpi / 72)  # 转换pt为像素
                    font_color = layer.get("color", "#000000")
                    font_family = layer.get("font_family", "arial.ttf")

                    try:
                        font = ImageFont.truetype(font_family, font_size)
                    except:
                        font = ImageFont.load_default(font_size)

                    draw.text((x, y), text, font=font, fill=font_color)
                except Exception as e:
                    print(f"Error rendering text layer: {e}")

            elif layer_type == "shape":
                # 渲染形状图层
                try:
                    shape_type = layer.get("shape_type", "rectangle")
                    x = int(layer.get("x", 0) * dpi / 25.4)
                    y = int(layer.get("y", 0) * dpi / 25.4)
                    width = int(layer.get("width", 100) * dpi / 25.4)
                    height = int(layer.get("height", 100) * dpi / 25.4)
                    fill_color = layer.get("fill_color", None)
                    stroke_color = layer.get("stroke_color", "#000000")
                    stroke_width = int(layer.get("stroke_width", 1) * dpi / 25.4)

                    if shape_type == "rectangle":
                        draw.rectangle(
                            [x, y, x + width, y + height],
                            fill=fill_color,
                            outline=stroke_color,
                            width=stroke_width,
                        )
                    elif shape_type == "ellipse":
                        draw.ellipse(
                            [x, y, x + width, y + height],
                            fill=fill_color,
                            outline=stroke_color,
                            width=stroke_width,
                        )
                    elif shape_type == "line":
                        draw.line(
                            [x, y, x + width, y + height], fill=stroke_color, width=stroke_width
                        )
                except Exception as e:
                    print(f"Error rendering shape layer: {e}")

            elif layer_type == "qrcode":
                # 渲染二维码图层
                try:
                    content = layer.get("content", "")
                    x = int(layer.get("x", 0) * dpi / 25.4)
                    y = int(layer.get("y", 0) * dpi / 25.4)
                    size = int(layer.get("size", 50) * dpi / 25.4)

                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=10,
                        border=0,
                    )
                    qr.add_data(content)
                    qr.make(fit=True)

                    qr_img = qr.make_image(fill_color="black", back_color="white")
                    qr_img = qr_img.resize((size, size), Image.Resampling.NEAREST)

                    image.paste(qr_img, (x, y))
                except Exception as e:
                    print(f"Error rendering QR code layer: {e}")

        # 保存为JPEG
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=95, dpi=(dpi, dpi))
        return output.getvalue()

    @staticmethod
    def generate_test_page(dpi: int = 300) -> bytes:
        """生成测试页"""
        template = {
            "paper_width": 101.6,  # 4英寸
            "paper_height": 152.4,  # 6英寸
            "layers": [
                {
                    "type": "text",
                    "content": "=== 打印机校准测试页 ===",
                    "x": 10,
                    "y": 10,
                    "font_size": 16,
                    "color": "#000000",
                },
                {
                    "type": "text",
                    "content": f'打印时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                    "x": 10,
                    "y": 30,
                    "font_size": 12,
                    "color": "#000000",
                },
                # 四个角落的对齐标记
                {
                    "type": "shape",
                    "shape_type": "rectangle",
                    "x": 5,
                    "y": 5,
                    "width": 10,
                    "height": 10,
                    "fill_color": "#000000",
                },
                {
                    "type": "shape",
                    "shape_type": "rectangle",
                    "x": 86.6,  # 101.6 - 10 -5
                    "y": 5,
                    "width": 10,
                    "height": 10,
                    "fill_color": "#000000",
                },
                {
                    "type": "shape",
                    "shape_type": "rectangle",
                    "x": 5,
                    "y": 137.4,  # 152.4 -10 -5
                    "width": 10,
                    "height": 10,
                    "fill_color": "#000000",
                },
                {
                    "type": "shape",
                    "shape_type": "rectangle",
                    "x": 86.6,
                    "y": 137.4,
                    "width": 10,
                    "height": 10,
                    "fill_color": "#000000",
                },
                # 中心十字
                {
                    "type": "shape",
                    "shape_type": "line",
                    "x": 50.8,
                    "y": 40,
                    "width": 0,
                    "height": 72.4,
                    "stroke_color": "#000000",
                    "stroke_width": 1,
                },
                {
                    "type": "shape",
                    "shape_type": "line",
                    "x": 10,
                    "y": 76.2,
                    "width": 81.6,
                    "height": 0,
                    "stroke_color": "#000000",
                    "stroke_width": 1,
                },
            ],
        }

        return TemplateRenderService.render_template_to_image(template, [], dpi=dpi)
