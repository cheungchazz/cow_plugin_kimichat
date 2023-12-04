# coding=utf-8
"""
Author: chazzjimel
Email: chazzjimel@gmail.com
wechat：cheung-z-x

Description:

"""

import requests
import json

from common.log import logger
from .token_manager import ensure_access_token, tokens

# 常量定义，用于HTTP请求头
HEADERS = {
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh-HK;q=0.9,zh;q=0.8',
    'Content-Type': 'application/json; charset=UTF-8',
    'Origin': 'https://kimi.moonshot.cn',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 '
                  'Safari/537.36'
}


# 创建新会话的函数
@ensure_access_token
def create_new_chat_session():
    """
    发送POST请求以创建新的聊天会话。
    :return: 如果请求成功，返回会话ID；如果失败，返回None。
    """
    # 从全局tokens变量中获取access_token
    auth_token = tokens['access_token']

    # 复制请求头并添加Authorization字段
    headers = HEADERS.copy()
    headers['Authorization'] = f'Bearer {auth_token}'

    # 定义请求的载荷
    payload = {
        "name": "未命名会话",
        "is_example": False
    }

    # 发送POST请求
    response = requests.post('https://kimi.moonshot.cn/api/chat', json=payload, headers=headers)

    # 检查响应状态码并处理响应
    if response.status_code == 200:
        logger.debug("[KimiChat] 新建会话ID操作成功！")
        return response.json().get('id')  # 返回会话ID
    else:
        logger.error(f"[KimiChat] 新建会话ID失败，状态码：{response.status_code}")
        return None


# 实现流式请求聊天数据的函数
@ensure_access_token
def stream_chat_responses(chat_id, query, refs_list=None, use_search=True, new_chat=False):
    """
    以流的方式发送POST请求并处理响应以获取聊天数据。
    :param chat_id: 会话ID
    :param query: 用户的查询内容。
    :param refs_list: 服务器文件对象ID列表，默认空
    :param use_search: 是否使用搜索
    :param new_chat: 用于识别是否首次对话
    :return: 返回处理后的完整响应文本。
    """
    # 从全局tokens变量中获取access_token
    auth_token = tokens['access_token']

    if refs_list is None:
        refs_list = []

    # 复制请求头并添加Authorization字段
    headers = HEADERS.copy()
    headers['Authorization'] = f'Bearer {auth_token}'

    # 拼接url
    api_url = f"https://kimi.moonshot.cn/api/chat/{chat_id}/completion/stream"

    # 定义请求的载荷
    payload = {
        "messages": [{"role": "user", "content": query}],
        "refs": refs_list,
        "use_search": use_search
    }

    full_response_text = ""
    logger.info(f"[KimiChat] 正在请求对话")
    # 以流的方式发起POST请求
    with requests.post(api_url, json=payload, headers=headers, stream=True) as response:
        try:
            # 迭代处理每行响应数据
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')

                    # 检查行是否包含有效的数据
                    if decoded_line.startswith('data: '):
                        json_str = decoded_line.split('data: ', 1)[1]
                        try:
                            json_obj = json.loads(json_str)
                            if 'text' in json_obj:
                                full_response_text += json_obj['text']
                        except json.JSONDecodeError:
                            logger.error(f"[KimiChat] 解析JSON时出错: {json_str}")

                    # 检查数据流是否结束
                    if '"event":"all_done"' in decoded_line:
                        break
        except requests.exceptions.ChunkedEncodingError as e:
            logger.error(f"[KimiChat] ChunkedEncodingError: {e}")

    if new_chat:
        first_space_index = full_response_text.find(" ")
        trimmed_text = full_response_text[first_space_index + 1:]
    else:
        trimmed_text = full_response_text
    logger.debug(f"[KimiChat] 响应内容：{trimmed_text}")
    return trimmed_text

