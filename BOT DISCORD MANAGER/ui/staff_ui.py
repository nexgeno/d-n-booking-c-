import os
import threading
import json
import re
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QListWidget, QListWidgetItem, QScrollArea, QFrame, QLineEdit, 
                             QComboBox, QTextEdit, QGridLayout, QSizePolicy, QFileDialog, QApplication, QDialog, QInputDialog)
from PyQt5.QtCore import Qt, QSize, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPainterPath, QImage
from dotenv import load_dotenv
from supabase import create_client, Client
from ui.applications_ui import ImageDownloader, make_circular_avatar, ClickableAvatar

# [CẬP NHẬT] Hàm bóc tách và đóng gói dữ liệu ngầm (MNV, TITLE, HIDDEN)
def extract_quote_data(raw_quote):
    if not isinstance(raw_quote, str): raw_quote = ""
    mnv_m = re.search(r'\|MNV:(.*?)(?=\||$)', raw_quote)
    hid_m = re.search(r'\|HIDDEN:(.*?)(?=\||$)', raw_quote)
    t_ts = re.search(r'\|T_TS:(.*?)(?=\||$)', raw_quote)
    t_hh = re.search(r'\|T_HH:(.*?)(?=\||$)', raw_quote)
    t_g = re.search(r'\|T_G:(.*?)(?=\||$)', raw_quote)
    t_tr = re.search(r'\|T_TR:(.*?)(?=\||$)', raw_quote)
    
    c_quote = re.sub(r'\|(MNV|HIDDEN|T_TS|T_HH|T_G|T_TR):.*?(?=\||$)', '', raw_quote).strip()
    return {
        'quote': c_quote,
        'mnv': mnv_m.group(1).strip() if mnv_m else '',
        'hidden': hid_m.group(1).strip() if hid_m else '',
        't_ts': t_ts.group(1).strip().upper() if t_ts else '',
        't_hh': t_hh.group(1).strip().upper() if t_hh else '',
        't_g': t_g.group(1).strip().upper() if t_g else '',
        't_tr': t_tr.group(1).strip().upper() if t_tr else ''
    }

def pack_quote_data(quote, mnv, hidden, t_ts, t_hh, t_g, t_tr):
    res = quote.strip()
    if t_ts: res += f" |T_TS:{t_ts.upper()}"
    if t_hh: res += f" |T_HH:{t_hh.upper()}"
    if t_g: res += f" |T_G:{t_g.upper()}"
    if t_tr: res += f" |T_TR:{t_tr.upper()}"
    if hidden: res += f" |HIDDEN:{hidden}"
    if mnv: res += f" |MNV:{mnv}"
    return res

class StaffCardWidget(QFrame):
    def __init__(self, data, avatar_pixmap=None):
        super().__init__()
        self.setFixedSize(200, 200)
        self.setStyleSheet("""
            StaffCardWidget {
                background-color: white; 
                border: 1px solid #E5E7EB; 
                border-radius: 12px;
            }
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 20, 10, 20)
        self.layout.setSpacing(8)
        
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(90, 90)
        self.lbl_avatar.setStyleSheet("border: none; background: transparent;")
        self.lbl_avatar.setAlignment(Qt.AlignCenter)
        if avatar_pixmap and not avatar_pixmap.isNull():
            self.lbl_avatar.setPixmap(make_circular_avatar(avatar_pixmap, 90))
        else:
            self.lbl_avatar.setStyleSheet("border: none; border-radius: 45px; background-color: #F3F4F6;")
        
        av_lay = QHBoxLayout()
        av_lay.addWidget(self.lbl_avatar, alignment=Qt.AlignCenter)
        av_lay.setContentsMargins(0, 0, 0, 10)
        self.layout.addLayout(av_lay)
        
        name = data.get('ho_ten', 'Unknown').upper()
        mnv = data.get('mnv', '')
        lbl_name = QLabel(f"{name} - {mnv}")
        lbl_name.setAlignment(Qt.AlignCenter)
        lbl_name.setStyleSheet("color: #111827; font-weight: bold; font-size: 15px; border: none; background: transparent;")
        self.layout.addWidget(lbl_name)

        role = data.get('role', '')
        # Ưu tiên lấy chức danh Tâm Sự để hiển thị ngoài Thẻ, nếu không có thì fallback về Role
        chuc_danh = data.get('chuc_danh_ts', '').upper()
        if chuc_danh:
            role_display = chuc_danh
        else:
            role_display = "CÔNG CHÚA" if role == 'princess' else ("HOÀNG TỬ" if role == 'prince' else role.upper())
            
        lbl_role = QLabel(role_display)
        lbl_role.setAlignment(Qt.AlignCenter)
        
        female_titles = ['CÔNG CHÚA', 'HELENA', 'AERIS', 'NYX', 'PRINCESS']
        is_female = any(t in role_display for t in female_titles)
        color = '#EC4899' if is_female else '#3B82F6'
        
        lbl_role.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 13px; border: none; background: transparent;")
        self.layout.addWidget(lbl_role)
        
        self.layout.addStretch()

class StaffUI(QWidget):
    request_upload_image_signal = pyqtSignal(str, str, str, str)
    sync_profile_signal = pyqtSignal(str, object)
    go_to_chat_signal = pyqtSignal(str, str)
    delete_staff_signal = pyqtSignal(str, object)

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #F3F4F6;")
        url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        self.supabase = create_client(url, key) if url and key else None

        self.staff_list = []
        self.current_app = None
        self.pixmap_cache = {}
        self.current_images = []
        self.hidden_fields = []

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(15)

        self.setup_main_grid()
        self.setup_popup_details()
        self.load_data()

        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.load_data)
        self.auto_refresh_timer.start(3000)

    def setup_main_grid(self):
        self.grid_panel = QFrame()
        self.grid_panel.setStyleSheet("background-color: transparent; border: none;")
        lay = QVBoxLayout(self.grid_panel)
        lay.setContentsMargins(0,0,0,0)
        
        self.list_widget = QListWidget()
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setMovement(QListWidget.Static)
        self.list_widget.setSpacing(15)
        self.list_widget.setStyleSheet("""
            QListWidget { background: transparent; border: none; outline: none; } 
            QListWidget::item { background: transparent; border: none; outline: none; }
            QListWidget::item:selected { background: transparent; border: none; outline: none; }
            QListWidget::item:focus { border: none; outline: none; }
        """)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        
        # Bọc list widget vào ScrollArea tàng hình để cuộn mượt
        scroll_main = QScrollArea()
        scroll_main.setWidgetResizable(True)
        scroll_main.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_main.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_main.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        def make_wheel_event_list(s):
            def wheel_event(event):
                s.verticalScrollBar().setValue(s.verticalScrollBar().value() - event.angleDelta().y())
                event.accept() 
            return wheel_event
        scroll_main.wheelEvent = make_wheel_event_list(scroll_main)
        scroll_main.setWidget(self.list_widget)
        
        lay.addWidget(scroll_main)
        self.layout.addWidget(self.grid_panel, stretch=1)

    def setup_popup_details(self):
        self.detail_dialog = QDialog(self)
        self.detail_dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.detail_dialog.setStyleSheet("""
            QDialog {
                background-color: #F9FAFB;
                border-radius: 12px;
            }
        """)
        
        dialog_layout = QVBoxLayout(self.detail_dialog)
        dialog_layout.setContentsMargins(20, 20, 20, 20)
        dialog_layout.setSpacing(15)
        
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        btn_close_x = QPushButton("✕")
        btn_close_x.setFixedSize(32, 32)
        btn_close_x.setCursor(Qt.PointingHandCursor)
        btn_close_x.setStyleSheet("background: #FEE2E2; color: #EF4444; border-radius: 16px; font-weight: bold; font-size: 14px; border: none;")
        btn_close_x.clicked.connect(self.cancel_edits)
        top_bar.addWidget(btn_close_x)
        dialog_layout.addLayout(top_bar)
        
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        
        col_left = QVBoxLayout()
        col_left.setSpacing(15)
        
        card_avatar = QFrame()
        card_avatar.setFixedWidth(260)
        card_avatar.setStyleSheet("QFrame { background-color: white; border: 1px solid #E5E7EB; border-radius: 8px; }")
        lay_avatar = QVBoxLayout(card_avatar)
        
        lbl_av_title = QLabel("Ảnh đại diện")
        lbl_av_title.setStyleSheet("color: #1E3A8A; font-weight: bold; font-size: 14px; border: none;")
        lay_avatar.addWidget(lbl_av_title)
        
        self.lbl_avatar_img = ClickableAvatar()
        self.lbl_avatar_img.setCursor(Qt.PointingHandCursor)
        self.lbl_avatar_img.setFixedSize(120, 120)
        self.lbl_avatar_img.setStyleSheet("background-color: #F3F4F6; border-radius: 60px; border: none;")
        self.lbl_avatar_img.clicked.connect(self.change_avatar_local)
        lay_avatar.addWidget(self.lbl_avatar_img, alignment=Qt.AlignCenter)
        
        self.lbl_display_name = QLabel("Tên Nhân Viên")
        self.lbl_display_name.setAlignment(Qt.AlignCenter)
        self.lbl_display_name.setStyleSheet("font-size: 16px; font-weight: bold; border: none; margin-top: 10px;")
        lay_avatar.addWidget(self.lbl_display_name)
        
        id_layout = QHBoxLayout()
        lbl_id_title = QLabel("Tên đăng nhập:")
        lbl_id_title.setStyleSheet("color: #6B7280; font-size: 12px; border: none;")
        self.lbl_display_id = QLabel("")
        self.lbl_display_id.setStyleSheet("color: #111827; font-size: 12px; font-weight: bold; border: none;")
        id_layout.addWidget(lbl_id_title)
        id_layout.addStretch()
        id_layout.addWidget(self.lbl_display_id)
        lay_avatar.addLayout(id_layout)
        col_left.addWidget(card_avatar)
        
        self.btn_contact = QPushButton("Liên hệ")
        self.btn_contact.setCursor(Qt.PointingHandCursor)
        self.btn_contact.setStyleSheet("background-color: #F3F4F6; color: #1E3A8A; font-weight: bold; padding: 12px; border-radius: 8px; border: 1px solid #D1D5DB;")
        self.btn_contact.clicked.connect(self.contact_user)
        col_left.addWidget(self.btn_contact)
        col_left.addStretch()
        content_layout.addLayout(col_left)

        # [CẬP NHẬT] Gói Cột phải vào ScrollArea tàng hình để không bị đè méo Layout
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        def make_wheel_event_vert(s):
            def wheel_event(event):
                s.verticalScrollBar().setValue(s.verticalScrollBar().value() - event.angleDelta().y())
                event.accept() 
            return wheel_event
        right_scroll.wheelEvent = make_wheel_event_vert(right_scroll)
        
        right_container = QWidget()
        right_container.setStyleSheet("background: transparent;")
        col_right = QVBoxLayout(right_container)
        col_right.setSpacing(15)
        
        card_info = QFrame()
        card_info.setStyleSheet("QFrame { background-color: white; border: 1px solid #E5E7EB; border-radius: 8px; }")
        grid_info = QGridLayout(card_info)
        grid_info.setVerticalSpacing(15)
        
        lbl_style = "color: #4B5563; font-size: 13px; font-weight: bold; border: none;"
        input_style = "QLineEdit { border: none; border-bottom: 1px solid #D1D5DB; padding: 8px 5px; font-size: 13px; background: transparent; min-height: 30px; }"
        combo_style = """
            QComboBox { border: none; border-bottom: 1px solid #D1D5DB; padding: 8px 5px; font-size: 13px; background: transparent; min-height: 30px; }
            QComboBox QAbstractItemView { background-color: white; color: #111827; selection-background-color: #DBEAFE; selection-color: #1E3A8A; border: 1px solid #E5E7EB; border-radius: 4px; outline: none; }
        """
        btn_eye_style = "QPushButton { font-size: 12px; border: none; }"
        val_style = "color: #111827; font-size: 14px; font-weight: bold; border: none;"
        
        self.edit_hoten = QLineEdit(); self.edit_hoten.setStyleSheet(input_style); self.edit_hoten.textChanged.connect(self.check_changes)
        self.lbl_val_mnv = QLabel(); self.lbl_val_mnv.setStyleSheet(val_style)
        self.edit_role = QComboBox(); self.edit_role.setStyleSheet(combo_style); self.edit_role.addItems(["Công chúa", "Hoàng tử"]); self.edit_role.currentIndexChanged.connect(self.check_changes)
        
        # [CẬP NHẬT] Tách Tuổi và Giới Tính
        self.edit_tuoi = QLineEdit(); self.edit_tuoi.setStyleSheet(input_style); self.edit_tuoi.textChanged.connect(self.check_changes)
        self.edit_gt = QLineEdit(); self.edit_gt.setStyleSheet(input_style); self.edit_gt.textChanged.connect(self.check_changes)
        
        self.edit_noio = QLineEdit(); self.edit_noio.setStyleSheet(input_style); self.edit_noio.textChanged.connect(self.check_changes)
        self.edit_dichvu = QLineEdit(); self.edit_dichvu.setStyleSheet(input_style); self.edit_dichvu.textChanged.connect(self.check_changes)
        self.edit_game = QLineEdit(); self.edit_game.setStyleSheet(input_style); self.edit_game.textChanged.connect(self.check_changes)
        self.edit_giacam = QLineEdit(); self.edit_giacam.setStyleSheet(input_style); self.edit_giacam.textChanged.connect(self.check_changes)
        self.edit_quote = QTextEdit(); self.edit_quote.setFixedHeight(65); self.edit_quote.setStyleSheet("QTextEdit { border: 1px solid #D1D5DB; border-radius: 4px; padding: 8px; font-size: 13px; }"); self.edit_quote.textChanged.connect(self.check_changes)

        # 4 Chức danh In hoa
        self.edit_cd_ts = QLineEdit(); self.edit_cd_ts.setStyleSheet(input_style); self.edit_cd_ts.textChanged.connect(self.check_changes)
        self.edit_cd_hh = QLineEdit(); self.edit_cd_hh.setStyleSheet(input_style); self.edit_cd_hh.textChanged.connect(self.check_changes)
        self.edit_cd_g = QLineEdit(); self.edit_cd_g.setStyleSheet(input_style); self.edit_cd_g.textChanged.connect(self.check_changes)
        self.edit_cd_tr = QLineEdit(); self.edit_cd_tr.setStyleSheet(input_style); self.edit_cd_tr.textChanged.connect(self.check_changes)

        self.btn_hide_hoten = QPushButton(); self.btn_hide_hoten.setCursor(Qt.PointingHandCursor); self.btn_hide_hoten.setStyleSheet(btn_eye_style); self.btn_hide_hoten.clicked.connect(lambda: self.toggle_field('ho_ten', self.btn_hide_hoten))
        self.btn_hide_role = QPushButton(); self.btn_hide_role.setCursor(Qt.PointingHandCursor); self.btn_hide_role.setStyleSheet(btn_eye_style); self.btn_hide_role.clicked.connect(lambda: self.toggle_field('role', self.btn_hide_role))
        self.btn_hide_tuoi = QPushButton(); self.btn_hide_tuoi.setCursor(Qt.PointingHandCursor); self.btn_hide_tuoi.setStyleSheet(btn_eye_style); self.btn_hide_tuoi.clicked.connect(lambda: self.toggle_field('tuoi', self.btn_hide_tuoi))
        self.btn_hide_noio = QPushButton(); self.btn_hide_noio.setCursor(Qt.PointingHandCursor); self.btn_hide_noio.setStyleSheet(btn_eye_style); self.btn_hide_noio.clicked.connect(lambda: self.toggle_field('noi_o', self.btn_hide_noio))
        self.btn_hide_dichvu = QPushButton(); self.btn_hide_dichvu.setCursor(Qt.PointingHandCursor); self.btn_hide_dichvu.setStyleSheet(btn_eye_style); self.btn_hide_dichvu.clicked.connect(lambda: self.toggle_field('dich_vu', self.btn_hide_dichvu))
        self.btn_hide_game = QPushButton(); self.btn_hide_game.setCursor(Qt.PointingHandCursor); self.btn_hide_game.setStyleSheet(btn_eye_style); self.btn_hide_game.clicked.connect(lambda: self.toggle_field('game', self.btn_hide_game))
        self.btn_hide_giacam = QPushButton(); self.btn_hide_giacam.setCursor(Qt.PointingHandCursor); self.btn_hide_giacam.setStyleSheet(btn_eye_style); self.btn_hide_giacam.clicked.connect(lambda: self.toggle_field('gia_cam', self.btn_hide_giacam))
        self.btn_hide_quote = QPushButton(); self.btn_hide_quote.setCursor(Qt.PointingHandCursor); self.btn_hide_quote.setStyleSheet(btn_eye_style); self.btn_hide_quote.clicked.connect(lambda: self.toggle_field('quote', self.btn_hide_quote))
        
        # Ẩn hiện 4 chức danh
        self.btn_hide_cd_ts = QPushButton(); self.btn_hide_cd_ts.setCursor(Qt.PointingHandCursor); self.btn_hide_cd_ts.setStyleSheet(btn_eye_style); self.btn_hide_cd_ts.clicked.connect(lambda: self.toggle_field('cd_ts', self.btn_hide_cd_ts))
        self.btn_hide_cd_hh = QPushButton(); self.btn_hide_cd_hh.setCursor(Qt.PointingHandCursor); self.btn_hide_cd_hh.setStyleSheet(btn_eye_style); self.btn_hide_cd_hh.clicked.connect(lambda: self.toggle_field('cd_hh', self.btn_hide_cd_hh))
        self.btn_hide_cd_g = QPushButton(); self.btn_hide_cd_g.setCursor(Qt.PointingHandCursor); self.btn_hide_cd_g.setStyleSheet(btn_eye_style); self.btn_hide_cd_g.clicked.connect(lambda: self.toggle_field('cd_g', self.btn_hide_cd_g))
        self.btn_hide_cd_tr = QPushButton(); self.btn_hide_cd_tr.setCursor(Qt.PointingHandCursor); self.btn_hide_cd_tr.setStyleSheet(btn_eye_style); self.btn_hide_cd_tr.clicked.connect(lambda: self.toggle_field('cd_tr', self.btn_hide_cd_tr))

        def make_lbl(txt):
            l = QLabel(txt); l.setStyleSheet(lbl_style); return l

        grid_info.addWidget(make_lbl("Họ và tên"), 0, 0); grid_info.addWidget(self.edit_hoten, 0, 1); grid_info.addWidget(self.btn_hide_hoten, 0, 2)
        grid_info.addWidget(make_lbl("Mã NV"), 1, 0); grid_info.addWidget(self.lbl_val_mnv, 1, 1) 
        grid_info.addWidget(make_lbl("Vị trí"), 2, 0); grid_info.addWidget(self.edit_role, 2, 1); grid_info.addWidget(self.btn_hide_role, 2, 2)
        grid_info.addWidget(make_lbl("Tuổi"), 3, 0); grid_info.addWidget(self.edit_tuoi, 3, 1); grid_info.addWidget(self.btn_hide_tuoi, 3, 2)
        grid_info.addWidget(make_lbl("Giới tính"), 4, 0); grid_info.addWidget(self.edit_gt, 4, 1)
        grid_info.addWidget(make_lbl("Nơi ở"), 5, 0); grid_info.addWidget(self.edit_noio, 5, 1); grid_info.addWidget(self.btn_hide_noio, 5, 2)
        grid_info.addWidget(make_lbl("Dịch vụ"), 6, 0); grid_info.addWidget(self.edit_dichvu, 6, 1); grid_info.addWidget(self.btn_hide_dichvu, 6, 2)
        grid_info.addWidget(make_lbl("Game"), 7, 0); grid_info.addWidget(self.edit_game, 7, 1); grid_info.addWidget(self.btn_hide_game, 7, 2)
        grid_info.addWidget(make_lbl("Giá Cam"), 8, 0); grid_info.addWidget(self.edit_giacam, 8, 1); grid_info.addWidget(self.btn_hide_giacam, 8, 2)
        grid_info.addWidget(make_lbl("Quote"), 9, 0); grid_info.addWidget(self.edit_quote, 9, 1); grid_info.addWidget(self.btn_hide_quote, 9, 2)
        grid_info.addWidget(make_lbl("CD Tâm Sự"), 10, 0); grid_info.addWidget(self.edit_cd_ts, 10, 1); grid_info.addWidget(self.btn_hide_cd_ts, 10, 2)
        grid_info.addWidget(make_lbl("CD Hát Hò"), 11, 0); grid_info.addWidget(self.edit_cd_hh, 11, 1); grid_info.addWidget(self.btn_hide_cd_hh, 11, 2)
        grid_info.addWidget(make_lbl("CD Game"), 12, 0); grid_info.addWidget(self.edit_cd_g, 12, 1); grid_info.addWidget(self.btn_hide_cd_g, 12, 2)
        grid_info.addWidget(make_lbl("CD Tarot"), 13, 0); grid_info.addWidget(self.edit_cd_tr, 13, 1); grid_info.addWidget(self.btn_hide_cd_tr, 13, 2)

        col_right.addWidget(card_info)
        
        # [CẬP NHẬT] 4 Khung Thư viện Ảnh mượt mà, khóa trượt trang
        self.gallery_frames = {}
        self.gallery_layouts = {}
        
        for cat_id, cat_name in [('tamsu', 'Tâm Sự'), ('hatho', 'Hát Hò'), ('game', 'Game'), ('tarot', 'Tarot')]:
            frame = QFrame()
            frame.setStyleSheet("QFrame { background-color: white; border: 1px solid #E5E7EB; border-radius: 8px; }")
            flay = QVBoxLayout(frame)
            lbl_title = QLabel(f"Thư viện: {cat_name}")
            lbl_title.setStyleSheet("color: #1E3A8A; font-weight: bold; font-size: 14px; border: none; margin-bottom: 2px;")
            flay.addWidget(lbl_title)
            
            scroll = QScrollArea()
            scroll.setFixedHeight(160)
            scroll.setWidgetResizable(True)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
            
            def make_wheel_event_horiz(s):
                def wheel_event(event):
                    s.horizontalScrollBar().setValue(s.horizontalScrollBar().value() - event.angleDelta().y())
                    event.accept() 
                return wheel_event
            scroll.wheelEvent = make_wheel_event_horiz(scroll)
            
            container = QWidget()
            container.setStyleSheet("background: transparent;")
            lay = QHBoxLayout(container)
            lay.setAlignment(Qt.AlignLeft)
            scroll.setWidget(container)
            flay.addWidget(scroll)
            
            self.gallery_layouts[cat_id] = lay
            self.gallery_frames[cat_id] = frame
            col_right.addWidget(frame)

        col_right.addStretch()
        right_scroll.setWidget(right_container)
        content_layout.addWidget(right_scroll, stretch=1)
        
        action_layout = QHBoxLayout()
        self.lbl_status_noti = QLabel("")
        self.lbl_status_noti.setStyleSheet("color: #10B981; font-weight: bold; font-size: 13px;")
        action_layout.addWidget(self.lbl_status_noti)
        action_layout.addStretch()

        self.btn_delete = QPushButton("Xóa")
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setStyleSheet("background: #FEE2E2; color: #EF4444; padding: 10px 25px; border-radius: 6px; font-weight: bold; font-size: 13px; border: none;")
        self.btn_delete.clicked.connect(self.delete_staff)
        action_layout.addWidget(self.btn_delete)
        
        self.btn_save = QPushButton("Lưu thay đổi")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet("background: #3B82F6; color: white; padding: 10px 25px; border-radius: 6px; font-weight: bold; font-size: 13px; border: none;")
        self.btn_save.clicked.connect(self.save_edits)
        action_layout.addWidget(self.btn_save)

        dialog_layout.addLayout(content_layout)
        dialog_layout.addLayout(action_layout)

    def load_data(self):
        if not self.supabase: return
        threading.Thread(target=self._fetch_data, daemon=True).start()

    def _fetch_data(self):
        try:
            res = self.supabase.table('application').select('*').eq('status', '').execute()
            
            for app in res.data:
                ext = extract_quote_data(app.get('quote', ''))
                app['quote'] = ext['quote']
                app['mnv'] = ext['mnv']
                app['chuc_danh_ts'] = ext['t_ts']
                app['chuc_danh_hh'] = ext['t_hh']
                app['chuc_danh_g'] = ext['t_g']
                app['chuc_danh_tr'] = ext['t_tr']
                app['hidden_fields'] = ext['hidden']
                    
            self.staff_list = sorted(res.data, key=lambda x: x.get('display_id', '00'))
            QTimer.singleShot(0, self.update_ui_list)
        except: pass

    def update_ui_list(self):
        new_ids = [app['user_id'] for app in self.staff_list]
        for i in range(self.list_widget.count() - 1, -1, -1):
            if self.list_widget.item(i).data(Qt.UserRole)['user_id'] not in new_ids:
                self.list_widget.takeItem(i)
                
        for app in self.staff_list:
            uid = app['user_id']
            existing_item = None
            for i in range(self.list_widget.count()):
                if self.list_widget.item(i).data(Qt.UserRole)['user_id'] == uid:
                    existing_item = self.list_widget.item(i)
                    break
                    
            if existing_item:
                old_data = existing_item.data(Qt.UserRole)
                if old_data != app:
                    existing_item.setData(Qt.UserRole, app)
                    pix = self.pixmap_cache.get(app.get('avatar'))
                    widget = StaffCardWidget(app, pix)
                    self.list_widget.setItemWidget(existing_item, widget)
            else:
                item = QListWidgetItem()
                item.setSizeHint(QSize(210, 210))
                item.setData(Qt.UserRole, app)
                pix = self.pixmap_cache.get(app.get('avatar'))
                widget = StaffCardWidget(app, pix)
                self.list_widget.addItem(item)
                self.list_widget.setItemWidget(item, widget)
                
                urls_to_dl = [app.get('avatar')] if app.get('avatar') and app.get('avatar') not in self.pixmap_cache else []
                if urls_to_dl:
                    if not hasattr(self, 'dls'): self.dls = []
                    dl = ImageDownloader(urls_to_dl)
                    dl.image_downloaded.connect(self.on_list_image_loaded)
                    self.dls.append(dl)
                    dl.start()

    def on_list_image_loaded(self, url, image):
        pixmap = QPixmap.fromImage(image)
        self.pixmap_cache[url] = pixmap
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            app = item.data(Qt.UserRole)
            if app.get('avatar') == url:
                widget = StaffCardWidget(app, pixmap)
                self.list_widget.setItemWidget(item, widget)
                if self.current_app and self.current_app['user_id'] == app['user_id']:
                    self.lbl_avatar_img.setPixmap(make_circular_avatar(pixmap, 120))

    def on_item_clicked(self, item):
        self.current_app = item.data(Qt.UserRole).copy()
        self.show_details()

    def block_signals_all(self, block):
        self.edit_hoten.blockSignals(block)
        self.edit_role.blockSignals(block)
        self.edit_tuoi.blockSignals(block); self.edit_gt.blockSignals(block)
        self.edit_noio.blockSignals(block); self.edit_dichvu.blockSignals(block)
        self.edit_game.blockSignals(block); self.edit_giacam.blockSignals(block)
        self.edit_quote.blockSignals(block)
        self.edit_cd_ts.blockSignals(block); self.edit_cd_hh.blockSignals(block)
        self.edit_cd_g.blockSignals(block); self.edit_cd_tr.blockSignals(block)

    def toggle_field(self, field_name, btn):
        if field_name in self.hidden_fields:
            self.hidden_fields.remove(field_name)
            btn.setText("Hiện")
            btn.setStyleSheet("background: #D1FAE5; color: #065F46; font-weight: bold; border-radius: 4px; padding: 4px 8px; border: none;")
        else:
            self.hidden_fields.append(field_name)
            btn.setText("Ẩn")
            btn.setStyleSheet("background: #FEE2E2; color: #991B1B; font-weight: bold; border-radius: 4px; padding: 4px 8px; border: none;")
        self.check_changes()

    def update_toggle_buttons(self):
        toggles = [
            ('ho_ten', self.btn_hide_hoten), ('role', self.btn_hide_role),
            ('tuoi', self.btn_hide_tuoi), ('noi_o', self.btn_hide_noio), 
            ('dich_vu', self.btn_hide_dichvu), ('game', self.btn_hide_game), 
            ('gia_cam', self.btn_hide_giacam), ('quote', self.btn_hide_quote),
            ('cd_ts', self.btn_hide_cd_ts), ('cd_hh', self.btn_hide_cd_hh),
            ('cd_g', self.btn_hide_cd_g), ('cd_tr', self.btn_hide_cd_tr)
        ]
        for field, btn in toggles:
            if field in self.hidden_fields:
                btn.setText("Ẩn")
                btn.setStyleSheet("background: #FEE2E2; color: #991B1B; font-weight: bold; border-radius: 4px; padding: 4px 8px; border: none;")
            else:
                btn.setText("Hiện")
                btn.setStyleSheet("background: #D1FAE5; color: #065F46; font-weight: bold; border-radius: 4px; padding: 4px 8px; border: none;")

    def show_details(self):
        if not self.current_app: return
        app = self.current_app
        self.lbl_status_noti.setText("")
        self.lbl_display_name.setText(app.get('ho_ten', ''))
        self.lbl_display_id.setText(str(app.get('user_id', '')))
        
        self.hidden_fields = [f.strip() for f in app.get('hidden_fields', '').split(',') if f.strip()]
        self.update_toggle_buttons()
        
        self.block_signals_all(True)
        self.lbl_val_mnv.setText(app.get('mnv', ''))
        self.edit_hoten.setText(app.get('ho_ten', ''))
        
        tuoi_gt = app.get('tuoi', '')
        if '-' in tuoi_gt:
            p = tuoi_gt.split('-', 1)
            tuoi, gt = p[0].strip(), p[1].strip()
        else:
            tuoi, gt = tuoi_gt, ""
        self.edit_tuoi.setText(tuoi)
        self.edit_gt.setText(gt)
        
        self.edit_noio.setText(app.get('noi_o', ''))
        self.edit_dichvu.setText(app.get('dich_vu', ''))
        self.edit_game.setText(app.get('game', ''))
        self.edit_giacam.setText(app.get('gia_cam', ''))
        self.edit_quote.setText(app.get('quote', ''))
        
        self.edit_cd_ts.setText(app.get('chuc_danh_ts', ''))
        self.edit_cd_hh.setText(app.get('chuc_danh_hh', ''))
        self.edit_cd_g.setText(app.get('chuc_danh_g', ''))
        self.edit_cd_tr.setText(app.get('chuc_danh_tr', ''))
        
        role_val = app.get('role', '')
        if role_val == 'princess': role_idx = 0
        elif role_val == 'prince': role_idx = 1
        else: role_idx = 0
        self.edit_role.setCurrentIndex(role_idx)
        
        self.block_signals_all(False)
        
        try:
            parsed_imgs = json.loads(app.get('images', '[]'))
            if not isinstance(parsed_imgs, list): parsed_imgs = []
            self.current_images = parsed_imgs
        except:
            self.current_images = [{'url': u.strip(), 'type': 'general'} for u in app.get('images', '').split(',') if u.strip()]

        self.check_changes() 

        self.lbl_avatar_img.setPixmap(QPixmap())
        self.lbl_avatar_img.setText("...")
        
        urls = [app.get('avatar')] if app.get('avatar') else []
        urls.extend([img['url'] for img in self.current_images])
        urls_to_dl = [u for u in urls if u not in self.pixmap_cache]
        
        if urls_to_dl:
            if not hasattr(self, 'dls'): self.dls = []
            dl = ImageDownloader(urls_to_dl)
            dl.image_downloaded.connect(self.on_image_loaded)
            self.dls.append(dl)
            dl.start()
            
        if app.get('avatar') in self.pixmap_cache:
            self.lbl_avatar_img.setPixmap(make_circular_avatar(self.pixmap_cache[app.get('avatar')], 120))
            
        self.render_gallery()
        
        geom = self.geometry()
        global_pos = self.mapToGlobal(self.rect().topLeft())
        self.detail_dialog.setFixedSize(geom.width(), geom.height())
        self.detail_dialog.move(global_pos)
        self.detail_dialog.exec_()

    def on_image_loaded(self, url, image):
        pixmap = QPixmap.fromImage(image)
        self.pixmap_cache[url] = pixmap
        if self.current_app and url == self.current_app.get('avatar'):
            self.lbl_avatar_img.setPixmap(make_circular_avatar(pixmap, 120))
        self.render_gallery()

    def render_gallery(self):
        for lay in self.gallery_layouts.values():
            while lay.count() > 0:
                child = lay.takeAt(0)
                if child.widget(): child.widget().deleteLater()
                
        for frame in self.gallery_frames.values():
            frame.show()
            
        for i, img_obj in enumerate(self.current_images):
            url = img_obj['url']
            cat = img_obj.get('type', 'general')
            if cat == 'general': cat = 'tamsu'
            if cat not in self.gallery_layouts: cat = 'tamsu'
            
            container = QFrame()
            container.setFixedSize(140, 140)
            container.setStyleSheet("background: white; border: 1px solid #D1D5DB; border-radius: 6px;")
            lay = QVBoxLayout(container); lay.setContentsMargins(0,0,0,0)
            
            img_lbl = QLabel()
            img_lbl.setAlignment(Qt.AlignCenter)
            if url in self.pixmap_cache and not self.pixmap_cache[url].isNull():
                img_lbl.setPixmap(self.pixmap_cache[url].scaled(140, 140, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
            else:
                img_lbl.setText("Đang tải...")
                img_lbl.setStyleSheet("color: #6B7280; font-size: 12px; border: none;")
            lay.addWidget(img_lbl)
            
            btn_close = QPushButton("X", container)
            btn_close.setFixedSize(24, 24)
            btn_close.setStyleSheet("background: rgba(255, 255, 255, 0.9); color: #EF4444; font-weight: bold; border-radius: 12px; border: 1px solid #EF4444;")
            btn_close.setCursor(Qt.PointingHandCursor)
            btn_close.move(112, 4)
            btn_close.clicked.connect(lambda checked, idx=i: self.remove_image(idx))
            self.gallery_layouts[cat].addWidget(container)
            
        for cat_id, lay in self.gallery_layouts.items():
            btn_add = QPushButton("+")
            btn_add.setFixedSize(140, 140)
            btn_add.setStyleSheet("background: #F9FAFB; border: 2px dashed #D1D5DB; border-radius: 6px; font-size: 36px; color: #9CA3AF;")
            btn_add.setCursor(Qt.PointingHandCursor)
            btn_add.clicked.connect(lambda checked, c=cat_id: self.add_image_local_by_cat(c))
            lay.addWidget(btn_add)

        self.check_changes()

    def remove_image(self, idx):
        if 0 <= idx < len(self.current_images):
            self.current_images.pop(idx)
            self.render_gallery()
            self.check_changes()

    def change_avatar_local(self):
        if not self.current_app: return
        file_name, _ = QFileDialog.getOpenFileName(self.detail_dialog, "Chọn ảnh đại diện", "", "Image Files (*.png *.jpg *.jpeg *.webp)")
        if file_name:
            self.lbl_status_noti.setText("Đang đẩy ảnh lên...")
            QApplication.processEvents() 
            old_url = self.current_app.get('avatar', '')
            self.request_upload_image_signal.emit(file_name, "avatar", str(self.current_app['user_id']), old_url)

    def add_image_local_by_cat(self, cat_id):
        if not self.current_app: return
        self.pending_img_type = cat_id
        file_name, _ = QFileDialog.getOpenFileName(self.detail_dialog, "Chọn ảnh", "", "Image Files (*.png *.jpg *.jpeg *.webp)")
        if file_name:
            self.lbl_status_noti.setText("Đang đẩy ảnh lên...")
            QApplication.processEvents() 
            self.request_upload_image_signal.emit(file_name, f"gallery_{self.pending_img_type}", str(self.current_app['user_id']), "")

    def receive_uploaded_image(self, url, img_type, user_id):
        if not self.current_app or str(self.current_app['user_id']) != str(user_id): return
        self.lbl_status_noti.setText("Tải ảnh xong!")
        
        if img_type == "avatar":
            self.current_app['avatar'] = url
            dl = ImageDownloader([url]); dl.image_downloaded.connect(self.on_image_loaded)
            if not hasattr(self, 'dls'): self.dls = []
            self.dls.append(dl); dl.start()
            self.check_changes()
        elif img_type.startswith("gallery_"):
            cat = img_type.replace("gallery_", "")
            self.current_images.append({'url': url, 'type': cat})
            dl = ImageDownloader([url]); dl.image_downloaded.connect(self.on_image_loaded)
            if not hasattr(self, 'dls'): self.dls = []
            self.dls.append(dl); dl.start()
            self.render_gallery()
            self.check_changes()

    def check_changes(self):
        if not self.current_app: return
        
        role_val = 'princess' if self.edit_role.currentIndex() == 0 else 'prince'
        
        # Tạo lại chuỗi Tuổi - Giới tính
        tuoi_edit = self.edit_tuoi.text().strip()
        gt_edit = self.edit_gt.text().strip()
        tuoi_gt_val = f"{tuoi_edit} - {gt_edit}" if gt_edit else tuoi_edit
        
        try: old_imgs = json.loads(self.current_app.get('images', '[]'))
        except: old_imgs = []
        
        changed = (
            self.edit_hoten.text().strip() != self.current_app.get('ho_ten', '') or
            self.edit_cd_ts.text().strip().upper() != self.current_app.get('chuc_danh_ts', '') or
            self.edit_cd_hh.text().strip().upper() != self.current_app.get('chuc_danh_hh', '') or
            self.edit_cd_g.text().strip().upper() != self.current_app.get('chuc_danh_g', '') or
            self.edit_cd_tr.text().strip().upper() != self.current_app.get('chuc_danh_tr', '') or
            tuoi_gt_val != self.current_app.get('tuoi', '') or
            self.edit_noio.text().strip() != self.current_app.get('noi_o', '') or
            self.edit_dichvu.text().strip() != self.current_app.get('dich_vu', '') or
            self.edit_game.text().strip() != self.current_app.get('game', '') or
            self.edit_giacam.text().strip() != self.current_app.get('gia_cam', '') or
            self.edit_quote.toPlainText().strip() != self.current_app.get('quote', '') or
            role_val != self.current_app.get('role', '') or
            ",".join(self.hidden_fields) != self.current_app.get('hidden_fields', '') or
            json.dumps(self.current_images) != json.dumps(old_imgs)
        )
        if changed: self.btn_save.show()
        else: self.btn_save.hide()

    def cancel_edits(self):
        self.detail_dialog.reject()
        self.current_app = None

    def save_edits(self):
        if not self.current_app: return
        
        self.lbl_status_noti.setText("Đang lưu...")
        self.btn_save.hide()
        QApplication.processEvents()
        
        app = self.current_app
        app['ho_ten'] = self.edit_hoten.text().strip()
        app['role'] = 'princess' if self.edit_role.currentIndex() == 0 else 'prince'
        
        tuoi_edit = self.edit_tuoi.text().strip()
        gt_edit = self.edit_gt.text().strip()
        app['tuoi'] = f"{tuoi_edit} - {gt_edit}" if gt_edit else tuoi_edit
        
        app['noi_o'] = self.edit_noio.text().strip()
        app['dich_vu'] = self.edit_dichvu.text().strip()
        app['game'] = self.edit_game.text().strip()
        app['gia_cam'] = self.edit_giacam.text().strip()
        
        raw_quote = self.edit_quote.toPlainText().strip()
        mnv = self.lbl_val_mnv.text()
        t_ts = self.edit_cd_ts.text().strip().upper()
        t_hh = self.edit_cd_hh.text().strip().upper()
        t_g = self.edit_cd_g.text().strip().upper()
        t_tr = self.edit_cd_tr.text().strip().upper()
        hidden = ",".join(self.hidden_fields)
        
        # Đóng gói tất cả vào chuỗi Quote
        app['quote'] = pack_quote_data(raw_quote, mnv, hidden, t_ts, t_hh, t_g, t_tr)
        
        app['chuc_danh_ts'] = t_ts
        app['chuc_danh_hh'] = t_hh
        app['chuc_danh_g'] = t_g
        app['chuc_danh_tr'] = t_tr
        app['mnv'] = mnv
        app['hidden_fields'] = hidden
        app['images'] = json.dumps(self.current_images)
        
        self.lbl_display_name.setText(app['ho_ten'])
        self.sync_profile_signal.emit(str(app['user_id']), app)
        
        # [CẬP NHẬT] Không gọi reject() để giữ nguyên màn hình cho user chỉnh sửa tiếp
        # self.detail_dialog.reject() 

    def on_update_success(self):
        self.lbl_status_noti.setText("Đã lưu và đồng bộ thành công!")
        QTimer.singleShot(3000, lambda: self.lbl_status_noti.setText(""))
        self.check_changes()
        
    def delete_staff(self):
        if not self.current_app: return
        self.delete_staff_signal.emit(str(self.current_app['user_id']), self.current_app)
        
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item and item.data(Qt.UserRole)['user_id'] == self.current_app['user_id']:
                self.list_widget.takeItem(i)
                break
        self.current_app = None
        self.detail_dialog.accept()

    def contact_user(self):
        if self.current_app: 
            self.detail_dialog.accept()
            self.go_to_chat_signal.emit(str(self.current_app['user_id']), self.current_app.get('ho_ten', 'Unknown'))