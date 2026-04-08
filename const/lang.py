# const/lang.py
import os

TEXTS = {
    'vi': {
        'OVERVIEW': 'TỔNG QUAN', 'DASHBOARD': 'Dashboard',
        'MANAGEMENT': 'QUẢN LÝ', 'INBOX': 'Hộp thư', 'AUTOREP': 'Trả lời tự động',
        'STAFF_MENU': 'Nhân viên', 'APPLICATIONS': 'Đơn xin việc',
        'SALES': 'BÁN HÀNG', 'CUSTOMERS': 'Khách hàng', 'ORDERS': 'Đơn hàng', 'REPORTS': 'Báo cáo',
        'SYSTEM': 'HỆ THỐNG', 'SETTINGS': 'Cài đặt',
        'MEMBERS': 'Thành viên', 'ADMIN': 'Admin', 'CHANNELS': 'Kênh', 'STAFF': 'Nhân viên',
        'COMPARED_YESTERDAY': '↑ +{}% so với hôm qua',
        'INTERACTIONS_1M': 'Tương tác 1 tháng', 'ROLE_STATS': 'Thống kê Roles',
        'RECENT_ACTIVITY': 'Hoạt động gần đây', 'SEARCH_ID': 'Nhập ID để tìm kiếm...',
        'ALL_ROLES': 'Tất cả Roles',
        'COL_CHANNEL_NAME': 'TÊN KÊNH', 'COL_ID': 'ID', 'COL_MEMBER_COUNT': 'SỐ THÀNH VIÊN',
        'COL_DISPLAY_NAME': 'TÊN HIỂN THỊ', 'COL_USER_NAME': 'USER NAME', 'COL_ROLES': 'ROLES', 'COL_ACTIVITY': 'HOẠT ĐỘNG',
        'PRINCESS': 'CÔNG CHÚA', 'PRINCE': 'HOÀNG TỬ', 'BTN_MSG': '💬 Nhắn tin',
        'EMPTY': '(Trống)',
        'SEARCH_CONVO': 'Tìm kiếm hội thoại...', 'ALL': 'Tất cả', 'UNREAD': 'Chưa đọc',
        'CURR_MSG': 'Tin nhắn hiện tại', 'ENTER_MSG': 'Nhập tin nhắn...',
        'START_CONVO': 'Bắt đầu trò chuyện...', 'PICTURE': '[Hình ảnh]', 'IMG_ERR': '[Hình ảnh lỗi]', 'REVOKE': 'Thu hồi tin nhắn',
        'SENT': 'Đã gửi', 'READ': 'Đã đọc', 'RECEIVED': 'Đã nhận', 'AUTO_REPLY_TAG': '⚡ Trả lời tự động',
        'YOU': 'Bạn: {}',
        'ADD_KW': 'THÊM TỪ KHÓA MỚI', 'KW_TRIGGER': 'Từ khóa kích hoạt:', 'KW_PLACEHOLDER': 'Nhập từ khóa...',
        'BOT_REPLY': 'Nội dung Bot sẽ trả lời:', 'REPLY_PLACEHOLDER': 'Nhập nội dung trả lời tự động...',
        'SAVE_KW': 'Lưu Từ Khóa', 'SAVING': 'Đang lưu...', 'AUTO_SCRIPTS': 'Danh sách Kịch bản Tự động',
        'COL_KW': 'TỪ KHÓA', 'COL_REPLY': 'NỘI DUNG TRẢ LỜI', 'DEL_SCRIPT': 'Xóa',
        'ERR_SYS': '\n--- LỖI HỆ THỐNG ---',
        'SYNC_INIT': '-> Đang khởi tạo Giao Diện và kết nối Database Supabase...',
        'SYNC_OK': '\n[OK] Dữ liệu đã sẵn sàng! Đang bật giao diện...',
        'BOT_READY': 'Bot {} đã sẵn sàng!',
        'SYNC_DL_AVATAR': 'Đang tải Avatar khách hàng {}...',
        'SYNC_UP_MSG': 'Đang cập nhật tin nhắn mới...',
        'SYNC_DONE': 'Đồng bộ hoàn tất!',
        'Q1': 'Chào em, bên chị có thể giúp gì?', 'Q2': 'Cho chị địa chỉ giao hàng ạ', 'Q3': 'Thanh toán CK/COD', 'Q4': 'Đã xác nhận đơn hàng', 'Q5': 'Đơn đang giao, 1-2 ngày tới ạ'
    },
    'en': {
        'OVERVIEW': 'OVERVIEW', 'DASHBOARD': 'Dashboard',
        'MANAGEMENT': 'MANAGEMENT', 'INBOX': 'Inbox', 'AUTOREP': 'Auto-Reply',
        'STAFF_MENU': 'Staff', 'APPLICATIONS': 'Applications',
        'SALES': 'SALES', 'CUSTOMERS': 'Customers', 'ORDERS': 'Orders', 'REPORTS': 'Reports',
        'SYSTEM': 'SYSTEM', 'SETTINGS': 'Settings',
        'MEMBERS': 'Members', 'ADMIN': 'Admin', 'CHANNELS': 'Channels', 'STAFF': 'Staff',
        'COMPARED_YESTERDAY': '↑ +{}% from yesterday',
        'INTERACTIONS_1M': '1 Month Interactions', 'ROLE_STATS': 'Roles Statistics',
        'RECENT_ACTIVITY': 'Recent Activity', 'SEARCH_ID': 'Enter ID to search...',
        'ALL_ROLES': 'All Roles',
        'COL_CHANNEL_NAME': 'CHANNEL NAME', 'COL_ID': 'ID', 'COL_MEMBER_COUNT': 'MEMBERS',
        'COL_DISPLAY_NAME': 'DISPLAY NAME', 'COL_USER_NAME': 'USER NAME', 'COL_ROLES': 'ROLES', 'COL_ACTIVITY': 'ACTIVITY',
        'PRINCESS': 'PRINCESS', 'PRINCE': 'PRINCE', 'BTN_MSG': '💬 Send Message',
        'EMPTY': '(Empty)',
        'SEARCH_CONVO': 'Search conversation...', 'ALL': 'All', 'UNREAD': 'Unread',
        'CURR_MSG': 'Scroll to bottom', 'ENTER_MSG': 'Type a message...',
        'START_CONVO': 'Start conversation...', 'PICTURE': '[Image]', 'IMG_ERR': '[Image Error]', 'REVOKE': 'Recall message',
        'SENT': 'Sent', 'READ': 'Read', 'RECEIVED': 'Received', 'AUTO_REPLY_TAG': '⚡ Auto-Reply',
        'YOU': 'You: {}',
        'ADD_KW': 'ADD NEW KEYWORD', 'KW_TRIGGER': 'Trigger keyword:', 'KW_PLACEHOLDER': 'Enter keyword...',
        'BOT_REPLY': 'Bot response content:', 'REPLY_PLACEHOLDER': 'Enter auto response...',
        'SAVE_KW': 'Save Keyword', 'SAVING': 'Saving...', 'AUTO_SCRIPTS': 'Auto Scripts List',
        'COL_KW': 'KEYWORD', 'COL_REPLY': 'RESPONSE CONTENT', 'DEL_SCRIPT': 'Delete',
        'ERR_SYS': '\n--- SYSTEM ERROR ---',
        'SYNC_INIT': '-> Initializing UI and connecting to Supabase...',
        'SYNC_OK': '\n[OK] Data is ready! Starting interface...',
        'BOT_READY': 'Bot {} is ready!',
        'SYNC_DL_AVATAR': 'Downloading Avatar for customer {}...',
        'SYNC_UP_MSG': 'Updating new messages...',
        'SYNC_DONE': 'Sync completed!',
        'Q1': 'Hello, how can I help you?', 'Q2': 'Please provide your delivery address', 'Q3': 'Payment via Bank/COD', 'Q4': 'Order confirmed', 'Q5': 'Order is delivering, 1-2 days'
    }
}

def t(key, *args):
    lang = os.getenv("APP_LANG", "vi")
    text = TEXTS.get(lang, TEXTS['vi']).get(key, key)
    if args:
        try:
            return text.format(*args)
        except:
            pass
    return text