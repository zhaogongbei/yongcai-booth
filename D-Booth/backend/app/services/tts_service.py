import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# 尝试导入edge-tts，处理可能的安装失败情况
try:
    import edge_tts

    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logger.warning("edge-tts 库未安装，TTS功能将不可用")

# 语音映射配置
VOICE_MAPPING = {
    "zh-CN": {"female": "zh-CN-XiaoxiaoNeural", "male": "zh-CN-YunxiNeural"},
    "en-US": {"female": "en-US-JennyNeural", "male": "en-US-GuyNeural"},
}

# TTS缓存，key为text+language+voice的哈希，value为音频bytes
_tts_cache: Dict[str, bytes] = {}

# 缓存目录配置
CACHE_DIR = Path("data/tts_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class TTSService:
    """TTS语音合成服务"""

    @staticmethod
    def _get_cache_key(text: str, language: str, voice: str) -> str:
        """生成缓存key"""
        key_str = f"{text}_{language}_{voice}"
        return hashlib.md5(key_str.encode("utf-8")).hexdigest()

    @staticmethod
    async def synthesize(text: str, language: str = "zh-CN", voice: str = "female") -> bytes:
        """
        合成语音
        :param text: 要合成的文本
        :param language: 语言，zh-CN/en-US
        :param voice: 语音类型，female/male
        :return: MP3音频字节
        """
        if not EDGE_TTS_AVAILABLE:
            logger.warning("edge-tts不可用，无法合成语音")
            return b""

        # 参数校验
        if not text.strip():
            return b""

        # 标准化参数
        language = language if language in VOICE_MAPPING else "zh-CN"
        voice = voice if voice in ["female", "male"] else "female"

        # 检查内存缓存
        cache_key = TTSService._get_cache_key(text, language, voice)
        if cache_key in _tts_cache:
            logger.debug(f"TTS命中内存缓存: {text[:20]}...")
            return _tts_cache[cache_key]

        # 检查文件缓存
        cache_file = CACHE_DIR / f"{cache_key}.mp3"
        if cache_file.exists():
            logger.debug(f"TTS命中文件缓存: {text[:20]}...")
            with open(cache_file, "rb") as f:
                audio_data = f.read()
                _tts_cache[cache_key] = audio_data
                return audio_data

        # 获取语音名称
        voice_name = VOICE_MAPPING[language][voice]

        try:
            logger.info(f"开始合成TTS: {text[:20]}..., 语音: {voice_name}")

            # 使用edge-tts合成
            audio_data = b""
            communicate = edge_tts.Communicate(text, voice_name)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]

            # 缓存结果
            _tts_cache[cache_key] = audio_data
            with open(cache_file, "wb") as f:
                f.write(audio_data)

            logger.info(f"TTS合成完成，大小: {len(audio_data)} bytes")
            return audio_data

        except Exception as e:
            logger.error(f"TTS合成失败: {str(e)}", exc_info=True)
            return b""
