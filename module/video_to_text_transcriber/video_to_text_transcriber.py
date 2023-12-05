# coding=utf-8
"""
Author: chazzjimel
Email: chazzjimel@gmail.com
wechat：cheung-z-x

Description:

"""

import os
import subprocess
from pydub import AudioSegment
import openai
from opencc import OpenCC


def transcribe_audio(file_path, api_url, api_key):
    """
    将给定文件中的音频内容转录为文本。

    参数:
        file_path (str): 需要转录的音频或视频文件的路径。
        api_url (str): OpenAI API的基础URL。
        api_key (str): 访问OpenAI API的API密钥。

    返回:
        str: 音频内容的转录文本。

    该函数支持.mp4、.webm、.weba、.m4a和.wav格式的音频文件。
    它提取音频（如果需要），将其分割成可管理的段落，并使用OpenAI的音频转录服务将音频转换为文本。
    然后使用OpenCC将文本从繁体转换为简体中文。
    """

    openai.api_key = api_key
    openai.api_base = api_url
    cc = OpenCC('t2s')

    def voice_to_text(voice_file):
        """
        使用OpenAI的音频转录服务将语音文件转换为文本。

        参数:
            voice_file (str): 语音文件的路径。

        返回:
            str: 语音文件的转录文本。
        """
        with open(voice_file, "rb") as file:
            result = openai.Audio.transcribe("whisper-1", file)
        text = result["text"]
        return cc.convert(text)

    def extract_audio(mp4_file, output_file):
        """
        从视频文件中提取音频。

        参数:
            mp4_file (str): 视频文件的路径。
            output_file (str): 输出音频文件的路径。

        该函数使用ffmpeg命令行工具从视频文件中提取音频。
        """
        command = ["ffmpeg", "-i", mp4_file, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", output_file]
        subprocess.run(command, check=True)

    def split_and_transcribe(voice_file, segment_length_ms=120000):
        """
        将音频文件分割并进行转录。

        参数:
            voice_file (str): 音频文件的路径。
            segment_length_ms (int): 分割音频的段落长度（毫秒）。

        返回:
            str: 转录后的完整文本。

        该函数将音频分割为设定长度的段落，并对每个段落进行转录。
        """
        audio = AudioSegment.from_file(voice_file)
        full_text = ""
        for i in range(0, len(audio), segment_length_ms):
            segment = audio[i:i + segment_length_ms]
            temp_file = f"temp_{i}.wav"
            segment.export(temp_file, format="wav")
            text = voice_to_text(temp_file)
            full_text += text + " "
            os.remove(temp_file)
        return full_text

    text = None
    if file_path.endswith(('.mp4', '.webm', '.weba', '.m4a')):
        audio_file = file_path.rsplit('.', 1)[0] + '.wav'
        extract_audio(file_path, audio_file)
        text = split_and_transcribe(audio_file)
    elif file_path.endswith('.wav'):
        text = split_and_transcribe(file_path)

    return text
