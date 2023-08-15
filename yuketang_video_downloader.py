import configparser

import requests
import json

config = configparser.ConfigParser()
config.read('config.ini')

# credentials
university_id = config.get('credentials', 'university_id')
classroom_id = config.get('credentials', 'classroom_id')
sign = config.get('credentials', 'sign')
term = config.get('credentials', 'term')

# header
user_agent = config.get('header', 'user-agent')
cookie = config.get('header', 'cookie')
referer = config.get('header', 'referer')
xtbz = config.get('header', 'xtbz')

headers = {
    'user-agent': user_agent,
    'cookie': cookie,
    'referer': referer,
    'xtbz': xtbz
}

# urls
urls = config['urls']
base_url = urls.get('base_url')
user_url = urls.get('user_url').format(base_url=base_url, term=term, university_id=university_id)
chapter_url = urls.get('chapter_url').format(base_url=base_url, classroom_id=classroom_id, sign=sign, term=term,
                                             university_id=university_id)
video_url_pre = urls.get('video_url_pre').format(base_url=base_url, sign=sign, classroom_id=classroom_id)


def get_user_id(user_url):
    '''
    获取用户 ID
    :param user_url: 用户信息获取的 URL
    :return: 用户 ID
    '''
    response = requests.get(user_url, headers=headers)
    response.encoding = response.apparent_encoding
    data = json.loads(response.text)['data']
    user_info = data['user_info']
    user_id = user_info['user_id']
    return user_id


def get_course_id(chapter_url):
    '''
    获取课程 ID
    :param chapter_url: 章节数据的 URL
    :return: 课程 ID
    '''
    response = requests.get(chapter_url, headers=headers)
    response.encoding = response.apparent_encoding
    data = json.loads(response.text)['data']
    course_id = data['course_id']
    return course_id


def get_video_ids(chapter_url):
    '''
    获取视频 ID 集合
    :param chapter_url: 章节数据的 URL
    :return: 视频 ID 集合
    '''
    response = requests.get(chapter_url, headers=headers)
    response.encoding = response.apparent_encoding
    data = json.loads(response.text)['data']
    video_ids = [str(section_leaf['id'])
                 for chapter in data['course_chapter']
                 for section_leaf in chapter['section_leaf_list']
                 ]
    return video_ids


def get_video_urls(video_url_pre, video_ids):
    '''
    获取视频 URL 列表
    :param video_url_pre: 视频 URL 前缀
    :param video_ids: 视频 ID 列表
    :return: 视频 URL 列表
    '''
    video_urls = [f'{video_url_pre}{vid}' for vid in video_ids]
    return video_urls


user_id = get_user_id(user_url)  # 获取用户 ID

course_id = get_course_id(chapter_url)  # 获取课程 ID

video_ids = get_video_ids(chapter_url)  # 获取视频 ID 集合
video_urls = get_video_urls(video_url_pre, video_ids)  # 获取视频 URL列表

print(f'user id:{user_id}')
print(f'course id:{course_id}')
print(f'video ids:{video_ids}')
for i, video_url in enumerate(video_urls):
    print(f'video ids[{i + 1}]:{video_url}')
