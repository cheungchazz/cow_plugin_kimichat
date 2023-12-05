## 插件说明：

[`国产模型kimi`](https://kimi.moonshot.cn/)插件，能力待挖掘，目前最优势的是超长上下文，先发个文件再问文件内容，很爽。

#### 【kimi】目前已支持（包括代码赋能的能力）：

- [x] 联网对话

- [x] 文件解析

  支持的文件格式：

  ```
  ['.dot', '.doc', '.docx', '.xls', ".xlsx", ".ppt", ".ppa", ".pptx", ".md", ".pdf", ".txt", ".csv"]
  ```

- [x] 图片解析（azure 赋能）

  使用azure识图api识别图片参数，再给kimi按要求执行，支持会话时自定义要求，老板要求加的。

- [x] 视频解析（azure+openai 赋能）

  使用azure识图api识别随机帧参数，使用openai将音频转录为文本，然后通通喂给kimi整理。

- [x] 查询天气

- [x] 查询股价

- [x] 查询新闻

- [x] 访问网址（经常不灵，不知道为什么）



## 插件使用：

安装依赖：

```
pip install opencv-python pydub opencc-python-reimplemented
```

安装FFmpeg：自行查找各平台安装方法



将`config.json.template`复制为`config.json`，并修改其中各参数的值。



**`refresh_token`的值怎么获取？**

【方法1】：登录进去首页或对话页面先挂他个十几分钟，然后F12开发者模式，网络选项，发个信息，找到名称“refresh”的连接，打开响应选项卡，复制“refresh_token”：后面的值就行了。

【方法2】：退出登录，重新扫码，在扫码前F12，然后找到wechat的连接，看响应也有，一样能用



**`azure_api_key`的key怎么获取？**

[`azure`](https://portal.azure.com/#home)创建计算机视觉服务，密钥和终结点对应url和key

### 其他参数说明：

```json
{
    "refresh_token": ""# 看上面
    "file_parsing_prompts": "请帮我整理汇总文件的核心内容"# 文件解析的首次提示词，设置通用点，全局参数
    "keyword": ""  # 关键词触发会话，留空就全部文本对话都会走插件，不为空则关键词+空格会触发插件
    "reset_keyword": "kimi重置会话" # 相当于网页开个新的窗口对话，没有写会话过期逻辑，懒
     "kimi_reply_tips": "[kimi]" # 插件回复内容前置提示词，方便区分
    "file_upload": true   # 文件解析开关，群聊私聊通通都是他，开就全开，关就全关
    "group_context": true # 群聊会话上下文管理，为true整个群用一个会话，包括文件、视频解析
    "azure_api_url": ""  # 识图api链接
    "azure_api_key": "" # 识图apikey
    "recognize_pictures_keyword":  # 关键词触发识图，留空默认"kimi识图"，不为空则关键词+空格会触发识图
    "card_analysis"：   	# 识别分享链接的开关
    "video_analysis"：  	# 识别视频的开关
    "openai_api_url"：	# 用于音频转录文本
    "openai_api_key"：	# 用于音频转录文本
    "frames_to_extract":	# 提取视频帧数的限制，整数型，值越大图帧越多，azure的费用越高
}
```



**常见问题（仅我自己测试的结果）：**

1. 一直返回Kimi 现在有点累了，晚一点再来问问我吧！您也可以重置会话试试噢！大概率是传的或者搜索的内容有点问题，重置会话不要重复传递上次的内容就能解决。
2. 发送文件后回复Kimi 现在有点累了，只有两种可能：敏感内容或者文件太大。



