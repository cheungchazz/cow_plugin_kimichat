# coding=utf-8
"""
Author: chazzjimel
Email: chazzjimel@gmail.com
wechat：cheung-z-x

Description:

"""

image_character_prompt = """

你现在的角色是：视觉分析内容总结助手\n
你现在的任务是：将视觉分析的参数，汇总成自然语言描述，全程以图片为主题。以下是详细要求：\n

"""


image_recognition_prompt = """



大纲要求：\n
请以“#内容摘要”为标题总结并对相关的知识点进行拓展和解读并输出，然后以“#关键信息”为标题列出关键信息，最后以“#图片标签”为标题输出Tag，每个标题块需要换行。\n

返回格式要求：\n
# 内容摘要\n
[在这里插入内容摘要，不少于150字。]\n

# 关键信息\n
[在这里列出关键信息，以数字编号和信息的归类开头。每条不超过20个字。]\n

# 图片标签\n
[将tagsResult翻译成中文添加"#"排列在这里，中间使用空格分开。]\n

其他要求：返回的内容可以适当插入与图片相关的emoji表情。\n

"""

