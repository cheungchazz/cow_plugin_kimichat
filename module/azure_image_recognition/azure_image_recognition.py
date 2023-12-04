# coding=utf-8
"""
Author: chazzjimel
Email: chazzjimel@gmail.com
wechat：cheung-z-x

Description:

"""
import requests

from common.log import logger


def analyze_image(file_path, api_url, api_key):
    """
    使用Azure计算机视觉API分析图像并提取标题、密集标题、标签和文本。
    """
    headers = {
        "Content-Type": "image/*",
        "Ocp-Apim-Subscription-Key": api_key,
    }
    params = {
        'api-version': '2023-04-01-preview',
        'features': 'caption,denseCaptions,tags,read',
    }
    try:
        with open(file_path, 'rb') as img_file:
            response = requests.post(api_url, headers=headers, params=params, data=img_file)
        response.raise_for_status()

        analysis_result = response.json()
        logger.debug(f"响应内容: {analysis_result}")

        caption = analysis_result.get('captionResult', {}).get('text', '')
        dense_captions = [item['text'] for item in analysis_result.get('denseCaptionsResult', {}).get('values', [])]
        tags = [tag['name'] for tag in analysis_result.get('tagsResult', {}).get('values', [])]
        read_content = analysis_result.get('readResult', {}).get('content', '')

        return {
            "caption": caption,
            "dense_captions": dense_captions,
            "tags": tags,
            "read_content": read_content
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"AZURE接口图像分析出错: {e}")
        return None
    except IOError as e:
        logger.error(f"文件操作出错: {e}")
        return None




