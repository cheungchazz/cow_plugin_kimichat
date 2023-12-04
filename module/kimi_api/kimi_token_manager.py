# coding=utf-8
"""
Author: chazzjimel
Email: chazzjimel@gmail.com
wechat：cheung-z-x

Description:

"""
import requests
import time

from common.log import logger


# 全局变量存储access_token和refresh_token
tokens = {
    "access_token": "",
    "refresh_token": "",
    "expires_at": 0  # access_token的过期时间
}

# 请求头定义
HEADERS = {
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh-HK;q=0.9,zh;q=0.8',
    'Content-Type': 'application/json; charset=UTF-8',
    'Origin': 'https://kimi.moonshot.cn',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
}


def refresh_access_token():
    """
    使用refresh_token刷新access_token，并更新全局tokens变量。
    """
    global tokens

    refresh_token = tokens['refresh_token']
    if not refresh_token:
        logger.error("[KimiChat] 缺少refresh_token，无法刷新access_token")
        return

    headers = HEADERS.copy()
    headers['Authorization'] = f'Bearer {refresh_token}'

    response = requests.get('https://kimi.moonshot.cn/api/auth/token/refresh', headers=headers)

    if response.status_code == 200:
        logger.debug("[KimiChat] access_token刷新成功！")
        response_data = response.json()
        tokens['access_token'] = response_data.get("access_token", "")
        tokens['refresh_token'] = response_data.get("refresh_token", "")
        tokens['expires_at'] = int(time.time()) + 599  # 假设access_token有效期是10分钟
    else:
        logger.error(f"[KimiChat] 刷新access_token失败，状态码：{response.status_code}")


def ensure_access_token(func):
    """
    装饰器，用于确保在调用函数前access_token是有效的。
    """

    def wrapper(*args, **kwargs):
        if time.time() >= tokens['expires_at']:
            refresh_access_token()
        return func(*args, **kwargs)

    return wrapper
