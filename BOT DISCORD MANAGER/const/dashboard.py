import discord
import re
from const.lang import t

def clean_text(text):
    if not text: return ""
    # Giữ lại chữ cái (Tiếng Việt), số, khoảng trắng và dấu câu. Xóa sạch Emoji để chống lỗi Font ô vuông
    cleaned = re.sub(r'[^\w\s\.,\-\/&|()\[\]]', '', str(text))
    return re.sub(r'\s+', ' ', cleaned).strip()

def get_dashboard_headers_member():
    return [t('COL_DISPLAY_NAME'), t('COL_USER_NAME'), t('COL_ID'), t('COL_ROLES'), t('COL_ACTIVITY')]

def get_dashboard_headers_channel():
    return [t('COL_CHANNEL_NAME'), t('COL_ID'), t('COL_MEMBER_COUNT')]

def format_member_data(member):
    roles = []
    for r in member.roles:
        if r.name != '@everyone':
            # Khử Emoji ở tên Role
            c_name = clean_text(r.name)
            if c_name: roles.append(c_name)
            else: roles.append(r.name)
            
    status_str = str(member.status)

    return {
        'name': clean_text(member.display_name) or member.display_name,
        'user': str(member),
        'id': str(member.id),
        'roles': ", ".join(roles) if roles else t('EMPTY'),
        'role_ids': [r.id for r in member.roles],
        'activity': status_str
    }