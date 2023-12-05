# coding=utf-8
"""
Author: chazzjimel
Email: chazzjimel@gmail.com
wechat：cheung-z-x

Description:

"""

import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from channel.chat_message import ChatMessage
from common.expired_dict import ExpiredDict
from plugins import *
from plugins.cow_plugin_kimichat.module.azure_image_recognition.azure_image_recognition import analyze_image
from plugins.cow_plugin_kimichat.module.kimi_api.kimi_token_manager import tokens, refresh_access_token
from plugins.cow_plugin_kimichat.module.kimi_api.kimi_api_models import create_new_chat_session, stream_chat_responses
from plugins.cow_plugin_kimichat.module.kimi_api.kimi_file_uploader import FileUploader
from plugins.cow_plugin_kimichat.module.video_frame_manager.video_frame_manager import extract_and_save_key_frames
from plugins.cow_plugin_kimichat.module.video_to_text_transcriber.video_to_text_transcriber import transcribe_audio
from plugins.cow_plugin_kimichat.prompts.image_recognition import image_recognition_prompt, image_character_prompt
from plugins.cow_plugin_kimichat.prompts.video_recognition import video_character_prompt, video_recognition_prompt


@plugins.register(
    name="KimiChat",
    desire_priority=1,
    hidden=True,
    desc="kimi模型对话",
    version="0.1",
    author="chazzjimel",
)
class KimiChat(Plugin):
    def __init__(self):
        super().__init__()
        self.chat_data = {}
        try:
            curdir = os.path.dirname(__file__)
            config_path = os.path.join(curdir, "config.json")
            logger.debug(f"[KimiChat] 加载配置文件{config_path}")
            with open(config_path, "r", encoding="utf-8") as f:
                conf = json.load(f)

            # 确保必需的配置项存在
            if not conf.get("refresh_token"):
                raise ValueError("配置文件中缺少 'refresh_token'")
            if not conf.get("azure_api_key"):
                raise ValueError("配置文件中缺少 'azure_api_key'")
            if not conf.get("openai_api_key"):
                raise ValueError("配置文件中缺少 'openai_api_key'")

            tokens['refresh_token'] = conf.get("refresh_token")
            if not tokens['access_token']:  # 初始化全局access_token
                refresh_access_token()

            self.params_cache = ExpiredDict(300)  # 创建过期字典，内容3分钟后失效
            self.keyword = conf.get("keyword", "")
            self.recognize_pictures_keyword = conf.get("recognize_pictures_keyword", "kimi识图")
            self.reset_keyword = conf.get("reset_keyword", "kimi重置会话")
            self.file_upload = conf.get("file_upload", False)
            self.group_context = conf.get("group_context", False)
            self.card_analysis = conf.get("card_analysis", False)
            self.video_analysis = conf.get("video_analysis", False)
            self.file_parsing_prompts = conf.get("file_parsing_prompts", "请帮我整理汇总文件的核心内容")
            self.azure_api_url = conf.get("azure_api_url")
            self.azure_api_key = conf.get("azure_api_key")
            self.kimi_reply_tips = conf.get("kimi_reply_tips", "")
            self.openai_api_url = conf.get("openai_api_url")
            self.openai_api_key = conf.get("openai_api_key")
            self.frames_to_extract = None
            self.current_context = None
            self.send_msg = create_channel_object()
            if "frames_to_extract" in conf:
                self.frames_to_extract = int(conf["frames_to_extract"])
            self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
            logger.info("[KimiChat] 初始化完成.")
        except FileNotFoundError:
            logger.warn("[KimiChat] 初始化失败, 没有获取到config.json配置文件。")
            raise
        except ValueError as e:
            logger.warn(f"[KimiChat] 初始化失败，错误: {e}")
            raise
        except Exception as e:
            logger.warn("[KimiChat] 初始化失败。" + str(e))
            raise

    def on_handle_context(self, e_context: EventContext):
        context_type = e_context["context"].type
        if context_type in [ContextType.VOICE, ContextType.IMAGE_CREATE, ContextType.JOIN_GROUP, ContextType.PATPAT]:
            return

        self.current_context = e_context
        msg: ChatMessage = e_context["context"]["msg"]
        content = e_context["context"].content.strip()

        user_id = msg.from_user_id
        receiver = e_context["context"].get("receiver")
        isgroup = e_context["context"].get("isgroup")

        logger.info(f"[KimiChat] content:{content}, user_id:{user_id}")

        # 根据不同的上下文类型调用相应的处理方法
        rely_content = self.dispatch_context(context_type, isgroup, user_id, receiver, content, msg)

        # 如果没有得到有效回复，则提供默认回复

        if rely_content == "队列无事件":
            logger.info(f"[KimiChat] 图片事件队列无ID。")
            return
        elif not rely_content:
            logger.info(f"[KimiChat] 未触发KimiChat。")
            return
        elif rely_content == "无响应":
            rely_content = "Kimi 现在有点累了，晚一点再来问问我吧！您也可以重置会话试试噢！"
            logger.warn(f"[KimiChat] 没有获取到回复内容，请检查日志！")

        # 创建回复并设置事件的行为
        reply = Reply()
        reply.type = ReplyType.TEXT
        if self.kimi_reply_tips:
            reply.content = self.kimi_reply_tips + "\n" + rely_content
        else:
            reply.content = rely_content
        e_context["reply"] = reply
        e_context.action = EventAction.BREAK_PASS

    def get_help_text(self, **kwargs):
        help_text = "kimi模型体验插件，支持联网、文件解析、图片解析、超长上下文。"
        return help_text

    def dispatch_context(self, context_type, isgroup, user_id, receiver, content, msg=None):
        """
        根据上下文类型和是否为群组消息来调度相应的处理方法。

        :param context_type: 上下文类型。
        :param isgroup: 是否是群组消息。
        :param user_id: 用户的ID。
        :param receiver: 接收者的ID（在群组中使用）。
        :param content: 用户提供的内容。
        :param msg: 消息对象（仅在文件上下文中使用）。
        :return: 处理后的回复内容。
        """
        target_id = receiver if isgroup and self.group_context else user_id

        handler_map = {
            (ContextType.SHARING, False): lambda: self._handle_sharing_context(user_id, content),
            (ContextType.TEXT, False): lambda: self._handle_text_context(user_id, content, user_id),
            (ContextType.FILE, False): lambda: self._handle_file_context(user_id, content, msg),
            (ContextType.SHARING, True): lambda: self._handle_sharing_context(target_id, content),
            (ContextType.TEXT, True): lambda: self._handle_text_context(target_id, content, user_id),
            (ContextType.FILE, True): lambda: self._handle_file_context(target_id, content, msg),
            (ContextType.IMAGE, False): lambda: self._handle_image_context(user_id, content, msg),
            (ContextType.IMAGE, True): lambda: self._handle_image_context(user_id, content, msg),
            (ContextType.VIDEO, False): lambda: self._handle_video_context(user_id, content, msg),
            (ContextType.VIDEO, True): lambda: self._handle_video_context(target_id, content, msg)
        }

        handler = handler_map.get((context_type, isgroup))
        if handler:
            return handler()
        else:
            logger.error(f"未知的上下文类型或组设置: {context_type}, {isgroup}")
            return None

    def _handle_sharing_context(self, user_id, content):
        """
        处理分享链接的情况。

        :param user_id: 用户的ID。
        :param content: 用户提供的内容。
        :return: 处理后的回复内容。
        """
        if self.card_analysis:
            logger.info(f"[KimiChat] 开始处理分享链接！")
            new_content = f"总结网站内容：{content}"
            chat_id = self._get_or_create_chat_id(user_id, True)
            rely_content = stream_chat_responses(chat_id, new_content, new_chat=True)
            self.chat_data[user_id] = {'chatid': chat_id, 'use_search': True}
            if not rely_content:
                return "无响应"
            else:
                return rely_content
        else:
            logger.info(f"[KimiChat] 没有开启分享链接解析功能，PASS！")
            return None

    def _handle_text_context(self, session, content, user_id):
        """
        处理文本对话的情况。

        :param user_id: 用户的ID。
        :param content: 用户提供的内容。
        :return: 处理后的回复内容。
        """
        logger.info(f"[KimiChat] 开始判断并处理文本对话！")
        keyword_prefix = self.keyword + " "  # 构建关键词前缀，包括一个空格
        recognize_pictures_prompt_prefix = self.recognize_pictures_keyword + "要求 "

        # 检查内容是否以关键词+空格开头
        if content.startswith(keyword_prefix):
            # 去除关键词和紧随其后的空格
            new_content = content[len(keyword_prefix):]
            # 使用新内容处理文本聊天
            return self._process_text_chat(session, new_content)
        elif content == self.recognize_pictures_keyword:
            self.params_cache[user_id] = {'prompt': ''}  # 触发了识图功能，创建过期字典保存user_id
            return f"请3分钟内发送图片内容整理要求给我,我将按您的要求进行整理，要求请以【{recognize_pictures_prompt_prefix}" \
                   f"+空格+要求】的格式发送，如果没有特殊要求，请直接发送需要识别的图片。"
        elif content.startswith(recognize_pictures_prompt_prefix):
            if user_id in self.params_cache:
                # 提取要求文本并更新params_cache
                prompt_text = content[len(recognize_pictures_prompt_prefix):]
                self.params_cache[user_id]['prompt'] = prompt_text  # 触发了识图自定义要求功能，创建过期字典保存user_id和prompt
                return "已收到识图要求，现在请发送图片。"
        elif self.reset_keyword in content:
            # 如果内容包含重置关键字，重置聊天数据
            return self._reset_chat_data(session)
        elif self.keyword == "":
            # 如果没有设定关键词，正常处理文本聊天
            return self._process_text_chat(session, content)

        # 如果内容不符合任何条件，返回None
        return None

    def _handle_file_context(self, user_id, content, msg):
        """
        处理文件上传的情况。

        :param user_id: 用户的ID。
        :param content: 用户提供的内容。
        :return: 处理后的回复内容。
        """
        logger.info(f"[KimiChat] 开始处理文件！")
        if not self.file_upload or not check_file_format(content):
            logger.info(f"[KimiChat] 未开启文件识别或文件格式不支持，PASS！")
            return None
        msg.prepare()
        self._send_msg(f"{self.kimi_reply_tips}\n☑正在给您解析文件并总结\n⏳整理内容需要点时间，请您耐心等待...")
        uploader = FileUploader()
        filename = os.path.basename(content)
        file_id = uploader.upload(filename, content)
        refs_list = [file_id]
        chat_id, new_chat = self._get_or_create_chat_id(user_id)
        rely_content = stream_chat_responses(chat_id, self.file_parsing_prompts, refs_list, new_chat)
        if not rely_content:
            return "无响应"
        else:
            return rely_content

    def _reset_chat_data(self, user_id):
        """
        重置聊天数据。

        :param user_id: 用户的ID。
        :return: 回复内容，指示会话已被重置。
        """
        if user_id in self.chat_data:
            del self.chat_data[user_id]
            logger.info(f"[KimiChat] 用户 {user_id} 的聊天数据已重置")
            return "会话已重置"
        else:
            logger.info(f"[KimiChat] 用户 {user_id} 的聊天数据不存在")
            return "会话不存在"

    def _process_text_chat(self, user_id, content):
        """
        处理文本聊天。

        :param user_id: 用户的ID。
        :param content: 用户提供的内容。
        :return: 处理后的回复内容。
        """
        chat_id, new_chat = self._get_or_create_chat_id(user_id)
        rely_content = stream_chat_responses(chat_id, content, use_search=self.chat_data[user_id]['use_search'],
                                             new_chat=new_chat)
        if not rely_content:
            return "无响应"
        else:
            return rely_content

    def _get_or_create_chat_id(self, user_id, sharing=False):
        """
        获取或创建新的聊天会话ID。

        :param user_id: 用户的ID。
        :param sharing: 是否是分享消息，此处分享消息为True会全部新建一个会话处理。
        :return: 聊天会话ID。
        """
        if user_id in self.chat_data and not sharing:
            return self.chat_data[user_id]['chatid'], False
        else:
            chat_id = create_new_chat_session()
            self.chat_data[user_id] = {'chatid': chat_id, 'use_search': True}
            return chat_id, True

    def _handle_image_context(self, user_id, content, msg):
        """
        处理图片上下文的情况。

        :param user_id: 用户的ID。
        :param content: 用户提供的内容（应是图片的路径）。
        :return: 处理后的回复内容。
        """
        # 检查用户ID是否存在于params_cache中
        if user_id in self.params_cache:
            logger.info(f"[KimiChat] 开始处理图片解析！")
            msg.prepare()
            # 提取prompt的值
            prompt = self.params_cache[user_id].get('prompt', '')
            self._send_msg(f"{self.kimi_reply_tips}\n☑正在识别图片内容\n⏳整理内容需要点时间，请您耐心等待...")
            # 判断prompt是否有内容
            if prompt:
                logger.info(f"[KimiChat] 使用用户提供的prompt！")
                image_information = analyze_image(content, self.azure_api_url, self.azure_api_key)
                prompts = image_character_prompt + prompt + f"\n图片内容如下：\n{image_information}"
                del self.params_cache[user_id]
                return self._process_text_chat(user_id, prompts)
            else:
                logger.info(f"[KimiChat] 使用默认的prompt！")
                image_information = analyze_image(content, self.azure_api_url, self.azure_api_key)
                prompts = image_character_prompt + image_recognition_prompt + f"\n图片内容如下：\n{image_information}"
                del self.params_cache[user_id]
                return self._process_text_chat(user_id, prompts)

        # 如果用户ID不在params_cache中，或者没有特定的处理逻辑，返回None或相应提示
        return "队列无事件"

    def _handle_video_context(self, user_id, content, msg):
        if self.video_analysis:
            logger.info(f"[KimiChat] 开始处理视频解读！")
            msg.prepare()
            key_frame_paths = extract_and_save_key_frames(content, self.frames_to_extract)
            self._send_msg(f"{self.kimi_reply_tips}\n☑正在识别视频内容\n⏳整理内容需要点时间，请您耐心等待...")
            # 存储所有分析结果的列表
            analyzed_results = []

            # 遍历关键帧路径，并对每个关键帧进行分析
            for frame_path in key_frame_paths:
                analysis_result = analyze_image(frame_path, self.azure_api_url, self.azure_api_key)
                analyzed_results.append(analysis_result)

            if analyzed_results:
                logger.debug(f"[KimiChat] 成功获取关键帧识别结果！")
                text = transcribe_audio(content, self.openai_api_url, self.openai_api_key)
                prompts = video_character_prompt + video_recognition_prompt + f"\n以下是按顺序抽取的视频帧的描述:" \
                                                                              f"\n{analyzed_results}\n" \
                                                                              f"\n以下是视频文件的音频转文本内容：\n{text}"
                return self._process_text_chat(user_id, prompts)
            else:
                logger.warn(f"[KimiChat] 未能获取关键帧识别结果，检查日志！")
                return "非常抱歉，解读视频出了点问题，您可以再试试，还是不行请通知我的主人修一修。"

        else:
            logger.info(f"[KimiChat] 没有开启视频解析功能，PASS！")
            return None

    def _send_msg(self, send_content):
        # 使用 self.current_context 中存储的 e_context
        reply = Reply()
        reply.type = ReplyType.TEXT
        context = self.current_context['context']
        msg = context.kwargs.get('msg')
        if context.kwargs.get('isgroup'):
            nickname = msg.actual_user_nickname  # 获取昵称
            reply.content = f"@{nickname}\n" + send_content
        else:
            reply.content = send_content
        self.send_msg.send(reply, context)


def check_file_format(file_path):
    _, file_extension = os.path.splitext(file_path)

    # 检查是否为指定的格式
    if file_extension.lower() in ['.dot', '.doc', '.docx', '.xls', ".xlsx", ".ppt", ".ppa", ".pptx", ".md", ".pdf",
                                  ".txt", ".csv"]:
        return True
    else:
        return False


def create_channel_object():
    # 从配置中获取频道类型
    channel_type = conf().get("channel_type")
    # 根据频道类型创建相应的频道对象
    if channel_type == 'wework':
        from channel.wework.wework_channel import WeworkChannel
        return WeworkChannel()
    elif channel_type == 'ntchat':
        from channel.wechatnt.ntchat_channel import NtchatChannel
        return NtchatChannel()
    elif channel_type == 'weworktop':
        from channel.weworktop.weworktop_channel import WeworkTopChannel
        return WeworkTopChannel()
    else:
        from channel.wechat.wechat_channel import WechatChannel
        return WechatChannel()
