import re
import cv2
import os
import streamlink
from time import sleep
from yt_dlp import YoutubeDL


def youtube_url_validation(url):
    """
    Check if cap_path is a URL of a YouTube video
    :param url: The checked string
    :return: is url a valid url
    """
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

    youtube_regex_match = re.match(youtube_regex, url)

    return youtube_regex_match is not None



def get_capture(cap_path):
    """
    Get OpenCV capture
    :param cap_path:
    :return:
    """

    # Check if cap_path is a URL of a YouTube video
    flag = youtube_url_validation(cap_path)
    
    if flag == True:
        return get_capture_from_url(cap_path, '1080p')

    return cv2.VideoCapture(cap_path)


def is_live(cap):
    """
    Returns True if the capture is live and False otherwise
    :param cap: An OpenCV capture
    :return: True if the capture is live and False otherwise
    """
    return int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) < 0



def get_url(youtube_url, res):
    """
    Gets a direct URL to the video.
    :param youtube_url: The url of the video.
    :param res: The resolution of the video.
    :return: a string of the direct URL of the youtube video.
    """

    # streams = streamlink.streams(youtube_url)
    # if res not in streams:
    #     return None
    # elif type(streams[res]) != streamlink.stream.ffmpegmux.MuxedStream:
    #     return streams[res].url
    # return streams[res].substreams[0].url

    ### Use yt-dlp library to get the video URL, instead of streamlink lib for better compatibility
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'format': 'bestvideo+bestaudio/best',
        'cookiefile': 'cookies.txt',
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        formats = info.get('formats', [])

        # Filter formats matching the requested resolution
        # format['format_note'] often contains resolution, or use 'height' attribute
        matching_formats = []
        for f in formats:
            if f.get('format_note') == res or (f.get('height') and f.get('height') == int(res.replace('p', ''))):
                matching_formats.append(f)

        if not matching_formats:
            return None

        # Try to find progressive (combined) format first
        for fmt in matching_formats:
            if fmt.get('acodec') != 'none' and fmt.get('vcodec') != 'none':
                return fmt.get('url')

        # If no combined stream, return video only stream URL (similar to substreams[0])
        for fmt in matching_formats:
            if fmt.get('vcodec') != 'none':
                return fmt.get('url')

        # If no video stream found, fallback None
        return None




def get_capture_from_url(youtube_url, res):
    """
    Get an OpenCV capture of a YouTube video.
    :param youtube_url: A url of the video
    :param res: The resolution of the video.
    :return: An OpenCV capture of the video.
    """
    for i in range(30):
        try:
            url = get_url(youtube_url, res)

            if url is None:
                continue

            cap = cv2.VideoCapture(url)

            if cap is not None:
                return cap
        except:
            pass

    return None