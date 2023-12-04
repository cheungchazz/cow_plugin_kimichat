# coding=utf-8
"""
Author: chazzjimel
Email: chazzjimel@gmail.com
wechat：cheung-z-x

Description:

"""

import requests

from common.log import logger
from .token_manager import ensure_access_token, tokens


class FileUploader:
    def __init__(self):
        self.pre_sign_url_api = "https://kimi.moonshot.cn/api/pre-sign-url"
        self.file_upload_api = "https://kimi.moonshot.cn/api/file"
        self.parse_process_api = "https://kimi.moonshot.cn/api/file/parse_process"

    @ensure_access_token
    def get_presigned_url(self, file_name):
        auth_token = tokens['access_token']
        headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        }
        payload = {
            "action": "file",
            "name": file_name
        }
        response = requests.post(self.pre_sign_url_api, headers=headers, json=payload)
        if response.status_code == 200:
            logger.debug("[KimiChat] 获取预签名URL成功")
            return response.json()
        else:
            raise Exception("[KimiChat] 获取预签名URL失败")

    def upload_file(self, presigned_url, file_path):
        with open(file_path, 'rb') as file:
            response = requests.put(presigned_url, data=file)
            if response.status_code != 200:
                raise Exception("[KimiChat] 文件上传失败")

    @ensure_access_token
    def notify_file_upload(self, file_info):
        auth_token = tokens['access_token']
        headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        }
        response = requests.post(self.file_upload_api, headers=headers, json=file_info)
        if response.status_code == 200:
            response_data = response.json()
            logger.debug("[KimiChat] 通知文件上传成功")
            return response_data.get("id")
        else:
            raise Exception("[KimiChat] 通知文件上传失败")

    @ensure_access_token
    def parse_process(self, ids):
        auth_token = tokens['access_token']
        headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        }
        payload = {
            "ids": [ids]
        }
        response = requests.post(self.parse_process_api, headers=headers, json=payload)
        if response.status_code == 200:
            logger.debug("[KimiChat] 解析文件上传进程成功")
        else:
            raise Exception("[KimiChat] 解析文件上传进程失败")

    def upload(self, file_name, file_path):
        try:
            presigned_info = self.get_presigned_url(file_name)
            presigned_url = presigned_info['url']
            object_name = presigned_info['object_name']

            self.upload_file(presigned_url, file_path)

            file_info = {
                "type": "file",
                "name": file_name,
                "object_name": object_name
            }
            file_id = self.notify_file_upload(file_info)
            self.parse_process(file_id)
            logger.debug(f"[KimiChat] 上传文件ID：{file_id}")
            return file_id
        except Exception as e:
            logger.error("[KimiChat] " + str(e))
            return None
