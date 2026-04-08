import os
import threading
import urllib.request
import json
import re
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QListWidget, QListWidgetItem, QScrollArea, QFrame, QGridLayout, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize, QThread
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPainterPath, QImage
from dotenv import load_dotenv
from supabase import create_client, Client

# [CẬP NHẬT] Hàm bóc tách dữ liệu ngầm từ chuỗi Quote
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

class ImageDownloader(QThread):
    image_downloaded = pyqtSignal(str, QImage)
    def __init__(self, url_list):
        super().__init__()
        self.url_list = url_list
    def run(self):
        for url in self.url_list:
            if not url or not url.strip(): continue
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    image = QImage()
                    image.loadFromData(response.read())
                    self.image_downloaded.emit(url, image)
            except: pass

def make_circular_avatar(pixmap, size=120):
    if pixmap.isNull(): return pixmap
    out = QPixmap(size, size)
    out.fill(Qt.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.Antialiasing)
    scaled = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)
    painter.drawPixmap(-(scaled.width() - size) // 2, -(scaled.height() - size) // 2, scaled)
    painter.end()
    return out

class ClickableAvatar(QLabel):
    clicked = pyqtSignal()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.clicked.emit()

class ApplicationsUI(QWidget):
    approve_signal = pyqtSignal(str, object)
    reject_signal = pyqtSignal(str, object)
    go_to_chat_signal = pyqtSignal(str, str) 
    request_upload_image_signal = pyqtSignal(str, str, str) 
    sync_draft_signal = pyqtSignal(str, object)
    total_pending_updated = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #F3F4F6;")
        load_dotenv()
        url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        self.supabase: Client = create_client(url, key) if url and key else None

        self.pending_apps = []
        self.current_app = None
        self.pixmap_cache = {}
        self.current_images = []

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(15)

        self.setup_left_list()
        self.setup_right_details()
        self.load_data()
        
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.load_data)
        self.auto_refresh_timer.start(3000)

    def setup_left_list(self):
        self.list_panel = QFrame()
        self.list_panel.setFixedWidth(300)
        self.list_panel.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #E5E7EB;")
        list_layout = QVBoxLayout(self.list_panel)

        self.app_list = QListWidget()
        # Ẩn thanh cuộn dọc list bên trái
        self.app_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.app_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.app_list.setStyleSheet("""
            QListWidget { border: none; background: transparent; outline: none; }
            QListWidget::item { padding: 12px; border-bottom: 1px solid #F3F4F6; font-size: 13px; font-weight: bold; color: #374151; }
            QListWidget::item:selected { background-color: #EFF6FF; border-left: 3px solid #3B82F6; color: #1E3A8A; }
        """)
        self.app_list.itemClicked.connect(self.on_item_clicked)
        list_layout.addWidget(self.app_list)

        self.layout.addWidget(self.list_panel)

    def setup_right_details(self):
        self.detail_area = QScrollArea()
        self.detail_area.setWidgetResizable(True)
        # [CẬP NHẬT] Ẩn thanh cuộn, cho phép cuộn bằng chuột
        self.detail_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.detail_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.detail_area.setStyleSheet("border: none; background: transparent;")
        
        self.detail_container = QWidget()
        self.detail_layout = QHBoxLayout(self.detail_container)
        self.detail_layout.setAlignment(Qt.AlignTop)

        self.profile_widget = QWidget()
        profile_layout = QHBoxLayout(self.profile_widget)
        profile_layout.setContentsMargins(0,0,0,0)
        profile_layout.setSpacing(15)

        col_left = QVBoxLayout()
        col_left.setSpacing(15)
        
        card_avatar = QFrame()
        card_avatar.setFixedWidth(280)
        card_avatar.setStyleSheet("QFrame { background-color: white; border: 1px solid #E5E7EB; border-radius: 8px; }")
        lay_avatar = QVBoxLayout(card_avatar)
        
        lbl_av_title = QLabel("Ảnh đại diện")
        lbl_av_title.setStyleSheet("color: #1E3A8A; font-weight: bold; font-size: 14px; border: none;")
        lay_avatar.addWidget(lbl_av_title)
        
        self.lbl_avatar_img = QLabel()
        self.lbl_avatar_img.setFixedSize(120, 120)
        self.lbl_avatar_img.setStyleSheet("background-color: #F3F4F6; border-radius: 60px; border: none;")
        self.lbl_avatar_img.setAlignment(Qt.AlignCenter)
        lay_avatar.addWidget(self.lbl_avatar_img, alignment=Qt.AlignCenter)
        
        self.lbl_display_name = QLabel("Tên Ứng Viên")
        self.lbl_display_name.setAlignment(Qt.AlignCenter)
        self.lbl_display_name.setStyleSheet("font-size: 16px; font-weight: bold; border: none; margin-top: 10px;")
        lay_avatar.addWidget(self.lbl_display_name)
        
        id_layout = QHBoxLayout()
        lbl_id_title = QLabel("Tên đăng nhập:")
        lbl_id_title.setStyleSheet("color: #6B7280; font-size: 12px; border: none;")
        self.lbl_user_id = QLabel("")
        self.lbl_user_id.setStyleSheet("color: #111827; font-size: 12px; font-weight: bold; border: none;")
        id_layout.addWidget(lbl_id_title)
        id_layout.addStretch()
        id_layout.addWidget(self.lbl_user_id)
        lay_avatar.addLayout(id_layout)
        col_left.addWidget(card_avatar)
        
        self.btn_contact = QPushButton("Liên hệ nhắn tin")
        self.btn_contact.setCursor(Qt.PointingHandCursor)
        self.btn_contact.setStyleSheet("background-color: #F3F4F6; color: #1E3A8A; font-weight: bold; padding: 12px; border-radius: 8px; border: 1px solid #D1D5DB;")
        self.btn_contact.clicked.connect(self.contact_user)
        col_left.addWidget(self.btn_contact)
        col_left.addStretch()
        profile_layout.addLayout(col_left)

        col_right = QVBoxLayout()
        col_right.setSpacing(15)

        card_quote = QFrame()
        card_quote.setStyleSheet("QFrame { background-color: white; border: 1px solid #E5E7EB; border-radius: 8px; }")
        lay_quote = QVBoxLayout(card_quote)
        lbl_quote_title = QLabel("Quote")
        lbl_quote_title.setStyleSheet("color: #1E3A8A; font-weight: bold; font-size: 14px; border: none; margin-bottom: 5px;")
        lay_quote.addWidget(lbl_quote_title)
        
        self.lbl_val_quote = QLabel()
        self.lbl_val_quote.setWordWrap(True)
        self.lbl_val_quote.setStyleSheet("color: #374151; font-size: 13px; font-style: normal; border: none;")
        lay_quote.addWidget(self.lbl_val_quote)
        col_right.addWidget(card_quote)

        card_info = QFrame()
        card_info.setStyleSheet("QFrame { background-color: white; border: 1px solid #E5E7EB; border-radius: 8px; }")
        lay_info = QVBoxLayout(card_info)
        lbl_info_title = QLabel("Thông tin cá nhân")
        lbl_info_title.setStyleSheet("color: #1E3A8A; font-weight: bold; font-size: 14px; border: none; margin-bottom: 10px;")
        lay_info.addWidget(lbl_info_title)

        grid_info = QGridLayout()
        grid_info.setVerticalSpacing(15)
        lbl_style = "color: #4B5563; font-size: 13px; font-weight: bold; border: none;"
        val_style = "color: #111827; font-size: 14px; font-weight: bold; border: none;"

        self.lbl_val_hoten = QLabel(); self.lbl_val_hoten.setStyleSheet(val_style)
        self.lbl_val_mnv = QLabel(); self.lbl_val_mnv.setStyleSheet(val_style)
        self.lbl_val_role = QLabel(); self.lbl_val_role.setStyleSheet(val_style)
        
        # Các label cho Tuổi, Giới tính tách riêng
        self.lbl_val_tuoi = QLabel(); self.lbl_val_tuoi.setStyleSheet(val_style)
        self.lbl_val_gt = QLabel(); self.lbl_val_gt.setStyleSheet(val_style)
        self.lbl_val_noio = QLabel(); self.lbl_val_noio.setStyleSheet(val_style)
        self.lbl_val_dichvu = QLabel(); self.lbl_val_dichvu.setStyleSheet(val_style)
        self.lbl_val_game = QLabel(); self.lbl_val_game.setStyleSheet(val_style)
        self.lbl_val_giacam = QLabel(); self.lbl_val_giacam.setStyleSheet(val_style)
        
        # 4 label chức danh
        self.lbl_val_cd_ts = QLabel(); self.lbl_val_cd_ts.setStyleSheet(val_style)
        self.lbl_val_cd_hh = QLabel(); self.lbl_val_cd_hh.setStyleSheet(val_style)
        self.lbl_val_cd_g = QLabel(); self.lbl_val_cd_g.setStyleSheet(val_style)
        self.lbl_val_cd_tr = QLabel(); self.lbl_val_cd_tr.setStyleSheet(val_style)

        grid_info.addWidget(QLabel("Họ và tên", styleSheet=lbl_style), 0, 0); grid_info.addWidget(self.lbl_val_hoten, 0, 1)
        grid_info.addWidget(QLabel("Mã NV", styleSheet=lbl_style), 1, 0); grid_info.addWidget(self.lbl_val_mnv, 1, 1)
        grid_info.addWidget(QLabel("Vị trí", styleSheet=lbl_style), 2, 0); grid_info.addWidget(self.lbl_val_role, 2, 1)
        
        # Tách Tuổi và Giới Tính
        grid_info.addWidget(QLabel("Tuổi", styleSheet=lbl_style), 3, 0); grid_info.addWidget(self.lbl_val_tuoi, 3, 1)
        grid_info.addWidget(QLabel("Giới tính", styleSheet=lbl_style), 4, 0); grid_info.addWidget(self.lbl_val_gt, 4, 1)
        
        grid_info.addWidget(QLabel("Nơi ở", styleSheet=lbl_style), 5, 0); grid_info.addWidget(self.lbl_val_noio, 5, 1)
        grid_info.addWidget(QLabel("Dịch vụ", styleSheet=lbl_style), 6, 0); grid_info.addWidget(self.lbl_val_dichvu, 6, 1)
        grid_info.addWidget(QLabel("Game", styleSheet=lbl_style), 7, 0); grid_info.addWidget(self.lbl_val_game, 7, 1)
        grid_info.addWidget(QLabel("Giá Cam", styleSheet=lbl_style), 8, 0); grid_info.addWidget(self.lbl_val_giacam, 8, 1)
        
        # 4 Chức danh
        grid_info.addWidget(QLabel("CD Tâm Sự", styleSheet=lbl_style), 9, 0); grid_info.addWidget(self.lbl_val_cd_ts, 9, 1)
        grid_info.addWidget(QLabel("CD Hát Hò", styleSheet=lbl_style), 10, 0); grid_info.addWidget(self.lbl_val_cd_hh, 10, 1)
        grid_info.addWidget(QLabel("CD Game", styleSheet=lbl_style), 11, 0); grid_info.addWidget(self.lbl_val_cd_g, 11, 1)
        grid_info.addWidget(QLabel("CD Tarot", styleSheet=lbl_style), 12, 0); grid_info.addWidget(self.lbl_val_cd_tr, 12, 1)
        
        lay_info.addLayout(grid_info)
        col_right.addWidget(card_info)

        # 4 phần hiển thị ảnh riêng biệt mượt mà
        self.gallery_frames = {}
        self.gallery_layouts = {}
        
        for cat_id, cat_name in [('tamsu', 'Tâm Sự'), ('hatho', 'Hát Hò'), ('game', 'Game'), ('tarot', 'Tarot')]:
            frame = QFrame()
            frame.setStyleSheet("QFrame { background-color: white; border: 1px solid #E5E7EB; border-radius: 8px; }")
            flay = QVBoxLayout(frame)
            flay.addWidget(QLabel(f"Thư viện: {cat_name}", styleSheet="color: #1E3A8A; font-weight: bold; font-size: 14px; border: none; margin-bottom: 2px;"))
            
            scroll = QScrollArea()
            scroll.setFixedHeight(160)
            scroll.setWidgetResizable(True)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setStyleSheet("QScrollArea { border: none; background: #F9FAFB; border-radius: 6px; }")
            
            def make_wheel_event(s):
                def wheel_event(event):
                    s.horizontalScrollBar().setValue(s.horizontalScrollBar().value() - event.angleDelta().y())
                    event.accept() 
                return wheel_event
            scroll.wheelEvent = make_wheel_event(scroll)
            
            container = QWidget()
            container.setStyleSheet("background: transparent;")
            lay = QHBoxLayout(container)
            lay.setAlignment(Qt.AlignLeft)
            scroll.setWidget(container)
            flay.addWidget(scroll)
            
            self.gallery_layouts[cat_id] = lay
            self.gallery_frames[cat_id] = frame
            col_right.addWidget(frame)

        action_layout = QHBoxLayout()
        action_layout.addStretch()

        self.btn_reject = QPushButton("Từ chối")
        self.btn_reject.setCursor(Qt.PointingHandCursor)
        self.btn_reject.setStyleSheet("background-color: #FEE2E2; color: #EF4444; font-weight: bold; padding: 10px 20px; border-radius: 6px; font-size: 13px; border: none;")
        self.btn_reject.clicked.connect(self.reject_app)
        action_layout.addWidget(self.btn_reject)

        self.btn_approve = QPushButton("Duyệt hồ sơ")
        self.btn_approve.setCursor(Qt.PointingHandCursor)
        self.btn_approve.setStyleSheet("background-color: #10B981; color: white; font-weight: bold; padding: 10px 25px; border-radius: 6px; font-size: 13px; border: none;")
        self.btn_approve.clicked.connect(self.approve_app)
        action_layout.addWidget(self.btn_approve)

        col_right.addLayout(action_layout)
        profile_layout.addLayout(col_right, stretch=1)
        self.profile_widget.hide()
        self.detail_layout.addWidget(self.profile_widget)

        self.detail_area.setWidget(self.detail_container)
        self.layout.addWidget(self.detail_area, stretch=1)

    def load_data(self):
        if not self.supabase: return
        threading.Thread(target=self._fetch_data, daemon=True).start()

    def _fetch_data(self):
        try:
            res = self.supabase.table('application').select('*').eq('status', 'pending').execute()
            
            for app in res.data:
                ext = extract_quote_data(app.get('quote', ''))
                app['quote'] = ext['quote']
                app['mnv'] = ext['mnv']
                app['chuc_danh_ts'] = ext['t_ts']
                app['chuc_danh_hh'] = ext['t_hh']
                app['chuc_danh_g'] = ext['t_g']
                app['chuc_danh_tr'] = ext['t_tr']
                app['hidden_fields'] = ext['hidden']
                    
            self.pending_apps = res.data
            QTimer.singleShot(0, self.update_ui_list)
        except: pass

    def update_ui_list(self):
        new_ids = [app['user_id'] for app in self.pending_apps]
        
        for i in range(self.app_list.count() - 1, -1, -1):
            if self.app_list.item(i).data(Qt.UserRole)['user_id'] not in new_ids:
                self.app_list.takeItem(i)
                
        for app in self.pending_apps:
            uid = app['user_id']
            role = "Công chúa" if app.get('role') == 'princess' else "Hoàng tử"
            display_text = f"{app.get('ho_ten', 'Unknown')} - {role}"
            
            existing_item = None
            for i in range(self.app_list.count()):
                if self.app_list.item(i).data(Qt.UserRole)['user_id'] == uid:
                    existing_item = self.app_list.item(i)
                    break
                    
            if existing_item:
                existing_item.setText(display_text)
                existing_item.setData(Qt.UserRole, app)
            else:
                item = QListWidgetItem(display_text)
                item.setSizeHint(QSize(0, 50))
                item.setData(Qt.UserRole, app)
                self.app_list.addItem(item)
                
        self.total_pending_updated.emit(len(self.pending_apps))
        
        if self.app_list.count() == 0:
            self.profile_widget.hide()

    def on_item_clicked(self, item):
        self.current_app = item.data(Qt.UserRole).copy()
        self.show_details()

    def show_details(self):
        if not self.current_app: return
        app = self.current_app
        self.profile_widget.show()
        
        self.lbl_display_name.setText(app.get('ho_ten', ''))
        self.lbl_user_id.setText(str(app.get('user_id', '')))
        
        self.lbl_val_quote.setText(app.get("quote", ""))
        self.lbl_val_mnv.setText(app.get("mnv", ""))
        
        # Tách chuỗi tuổi và giới tính
        tuoi_gt = app.get('tuoi', '')
        if '-' in tuoi_gt:
            p = tuoi_gt.split('-', 1)
            tuoi, gt = p[0].strip(), p[1].strip()
        else:
            tuoi, gt = tuoi_gt, "Chưa cập nhật"
            
        self.lbl_val_tuoi.setText(tuoi)
        self.lbl_val_gt.setText(gt)
        
        self.lbl_val_hoten.setText(app.get('ho_ten', ''))
        self.lbl_val_noio.setText(app.get('noi_o', ''))
        self.lbl_val_dichvu.setText(app.get('dich_vu', ''))
        self.lbl_val_game.setText(app.get('game', ''))
        self.lbl_val_giacam.setText(app.get('gia_cam', ''))
        self.lbl_val_role.setText("Công chúa" if app.get('role') == 'princess' else "Hoàng tử")
        
        self.lbl_val_cd_ts.setText(app.get('chuc_danh_ts', ''))
        self.lbl_val_cd_hh.setText(app.get('chuc_danh_hh', ''))
        self.lbl_val_cd_g.setText(app.get('chuc_danh_g', ''))
        self.lbl_val_cd_tr.setText(app.get('chuc_danh_tr', ''))
        
        try:
            parsed_imgs = json.loads(app.get('images', '[]'))
            if not isinstance(parsed_imgs, list): parsed_imgs = []
            self.current_images = parsed_imgs
        except:
            avatar_url = app.get('avatar', '')
            self.current_images = [{'url': u.strip(), 'type': 'general'} for u in app.get('images', '').split(',') if u.strip() and u.strip() != avatar_url]

        self.lbl_avatar_img.setPixmap(QPixmap())
        self.lbl_avatar_img.setText("Loading...")
        
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

    def on_image_loaded(self, url, image):
        pixmap = QPixmap.fromImage(image)
        self.pixmap_cache[url] = pixmap
        if self.current_app and url == self.current_app.get('avatar'):
            self.lbl_avatar_img.setPixmap(make_circular_avatar(pixmap, 120))
        self.render_gallery()

    def render_gallery(self):
        # Clear all layouts
        for lay in self.gallery_layouts.values():
            while lay.count() > 0:
                child = lay.takeAt(0)
                if child.widget(): child.widget().deleteLater()
                
        for frame in self.gallery_frames.values():
            frame.hide()
            
        for i, img_obj in enumerate(self.current_images):
            url = img_obj['url']
            cat = img_obj.get('type', 'general')
            if cat == 'general': cat = 'tamsu'
            if cat not in self.gallery_layouts: cat = 'tamsu'
            
            self.gallery_frames[cat].show()
            
            container = QFrame()
            container.setFixedSize(140, 140)
            container.setStyleSheet("background: white; border: 1px solid #D1D5DB; border-radius: 6px;")
            lay = QVBoxLayout(container); lay.setContentsMargins(0,0,0,0)
            
            img_lbl = QLabel("Đang tải...")
            img_lbl.setAlignment(Qt.AlignCenter)
            if url in self.pixmap_cache and not self.pixmap_cache[url].isNull():
                img_lbl.setPixmap(self.pixmap_cache[url].scaled(140, 140, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
            lay.addWidget(img_lbl)
            
            self.gallery_layouts[cat].addWidget(container)

    def receive_uploaded_image(self, url, img_type, user_id):
        pass

    def contact_user(self):
        if self.current_app: self.go_to_chat_signal.emit(str(self.current_app['user_id']), self.current_app.get('ho_ten', 'Unknown'))

    def approve_app(self):
        if self.current_app:
            self.approve_signal.emit(str(self.current_app['user_id']), self.current_app)
            self.profile_widget.hide()
            # Xóa khỏi danh sách UI ngay lập tức để không bị nháy
            row = self.app_list.currentRow()
            self.app_list.takeItem(row)
            self.current_app = None
            self.total_pending_updated.emit(self.app_list.count())

    def reject_app(self):
        if self.current_app:
            self.reject_signal.emit(str(self.current_app['user_id']), self.current_app)
            self._remove_from_list()

    def _remove_from_list(self):
        row = self.app_list.currentRow()
        self.app_list.takeItem(row)
        self.profile_widget.hide()
        self.current_app = None
        self.total_pending_updated.emit(self.app_list.count())