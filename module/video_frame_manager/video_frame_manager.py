# coding=utf-8
"""
Author: chazzjimel
Email: chazzjimel@gmail.com
wechat：cheung-z-x

Description:

"""
import cv2
import os
import threading
import time


def extract_and_save_key_frames(video_path, frames_to_extract=None):
    """
    提取视频关键帧并保存为图片。

    参数:
    video_path: str
        视频文件的路径。
    frames_to_extract: int, optional
        指定要提取的关键帧数量。如果未指定，则根据视频长度自动确定。

    返回:
    list of str
        保存的关键帧图片的绝对路径列表。

    描述:
    如果指定了 frames_to_extract，函数将提取这么多帧作为关键帧。
    如果未指定 frames_to_extract，函数会根据视频的长度决定每隔多少帧提取一帧作为关键帧：
    如果视频时长小于或等于30秒，每秒提取一帧；
    如果视频时长超过30秒，则提取总帧数的1/30作为关键帧。
    提取的关键帧会被保存在当前代码所在目录，并在10分钟后被自动删除。
    """

    # 确定保存目录为当前代码目录
    save_dir = os.getcwd()

    # 打开视频文件
    cap = cv2.VideoCapture(video_path)

    # 获取视频帧率和总帧数
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    # 确定每间隔多少帧提取一帧
    if frames_to_extract:
        interval = total_frames / frames_to_extract
    elif duration <= 30:
        interval = fps  # 如果视频小于等于30秒，每秒提取一帧
    else:
        interval = total_frames / 30  # 如果视频超过30秒，提取总长度/30的帧

    key_frames_paths = []
    frame_index = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 每间隔指定帧数提取一帧
        if frame_index % int(interval) == 0:
            frame_path = os.path.join(save_dir, f"frame_{frame_index}.jpg")
            cv2.imwrite(frame_path, frame)
            key_frames_paths.append(os.path.abspath(frame_path))

        frame_index += 1

    cap.release()

    # 设置一个定时器，10分钟后删除图片
    delete_files_after_delay(key_frames_paths, 600)

    return key_frames_paths


def delete_files_after_delay(file_paths, delay):
    """
    延迟删除指定文件。

    参数:
    file_paths: list of str
        要删除的文件路径列表。
    delay: int
        延迟时间（秒）。

    描述:
    此函数将在指定的延迟时间后删除提供的文件列表中的所有文件。
    使用线程来实现延时操作，不会阻塞主程序的运行。
    """

    def delete_files():
        time.sleep(delay)
        for file_path in file_paths:
            if os.path.exists(file_path):
                os.remove(file_path)

    delete_thread = threading.Thread(target=delete_files)
    delete_thread.start()
