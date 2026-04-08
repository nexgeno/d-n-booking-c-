import os
import threading
from dotenv import load_dotenv
from supabase import create_client, Client
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QLineEdit, QListWidget, QListWidgetItem, QScrollArea, QFrame, QMenu, QTextEdit, QSizePolicy, QGridLayout, QSpacerItem
from PyQt5.QtCore import pyqtSignal, Qt, QTimer, QSize
from PyQt5.QtGui import QPixmap, QImageReader, QPainter, QColor, QPainterPath, QIcon
from const.lang import t

# [CẬP NHẬT] Đổi thư mục thành images
IMAGE_DIR = os.path.join(os.getcwd(), "images")

def get_sort_id(msg_id_val):
    try: return int(msg_id_val)
    except: return 999999999999999999 

def create_avatar(name, size=40):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8", "#F06292", "#BA68C8", "#4DB6AC"]
    color = colors[len(name) % len(colors)] if name else "#CCCCCC"
    painter.setBrush(QColor(color))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(0, 0, size, size)
    painter.setPen(QColor("white"))
    font = painter.font()
    font.setPointSize(size // 3)
    font.setBold(True)
    painter.setFont(font)
    initial = name[0].upper() if name else "?"
    painter.drawText(pixmap.rect(), Qt.AlignCenter, initial)
    painter.end()
    return pixmap

def get_circular_avatar(image_path, name, size=40):
    if image_path and os.path.exists(image_path):
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            out = QPixmap(size, size)
            out.fill(Qt.transparent)
            painter = QPainter(out)
            painter.setRenderHint(QPainter.Antialiasing)
            scaled = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x_offset = (scaled.width() - size) // 2
            y_offset = (scaled.height() - size) // 2
            path = QPainterPath()
            path.addEllipse(0, 0, size, size)
            painter.setClipPath(path)
            painter.drawPixmap(-x_offset, -y_offset, scaled)
            painter.end()
            return out
    return create_avatar(name, size)

class ChatInputBox(QTextEdit):
    send_message_signal = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.setPlaceholderText(t('ENTER_MSG'))
        self.setStyleSheet("QTextEdit { padding: 10px; border: none; border-radius: 20px; color: #000000; background: #F3F4F6; font-size: 13px; }")
        self.setFixedHeight(45)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                super().keyPressEvent(event)
            else:
                event.accept() 
                self.send_message_signal.emit() 
                return
        else:
            super().keyPressEvent(event)

class InboxItemWidget(QWidget):
    def __init__(self, name, last_msg, unread_count, avatar_path, is_pinned=False, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: transparent; border: none;") 
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 10, 15, 10)
        
        self.avatar_container = QWidget()
        self.avatar_container.setFixedSize(45, 45)
        avatar_layout = QVBoxLayout(self.avatar_container)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        
        self.avatar_label = QLabel()
        self.avatar_label.setPixmap(get_circular_avatar(avatar_path, name, 40))
        avatar_layout.addWidget(self.avatar_label)

        self.text_layout = QVBoxLayout()
        self.text_layout.setSpacing(2)
        
        display_name = f"📌 {name}" if is_pinned else name
        self.name_label = QLabel(display_name)
        self.name_label.setStyleSheet("font-size: 13px; font-weight: bold;")
        
        self.msg_label = QLabel(last_msg)
        self.msg_label.setStyleSheet("color: #666666; font-size: 12px;")
        
        self.text_layout.addWidget(self.name_label)
        self.text_layout.addWidget(self.msg_label)

        self.badge_label = QLabel(str(unread_count))
        self.badge_label.setAlignment(Qt.AlignCenter)
        self.badge_label.setStyleSheet("background-color: #EF4444; color: white; border-radius: 8px; font-weight: bold; font-size: 9px; min-width: 16px; max-width: 16px; min-height: 16px; max-height: 16px;")
        self.badge_label.setVisible(unread_count > 0)

        self.layout.addWidget(self.avatar_container)
        self.layout.addLayout(self.text_layout)
        self.layout.addStretch()
        self.layout.addWidget(self.badge_label)
        
    def update_data(self, name, last_msg, unread_count, avatar_path, is_pinned=False):
        display_name = f"📌 {name}" if is_pinned else name
        self.name_label.setText(display_name)
        self.msg_label.setText(last_msg)
        self.badge_label.setText(str(unread_count))
        self.badge_label.setVisible(unread_count > 0)
        self.avatar_label.setPixmap(get_circular_avatar(avatar_path, name, 40))

class MessageBubble(QWidget):
    revoke_signal = pyqtSignal(object, str, str) 
    def __init__(self, author, text, timestamp, is_self, msg_id, image_path, avatar_path="", status="", is_channel=False, parent=None):
        super().__init__(parent)
        self.text_content = text
        self.is_self = is_self
        self.msg_id = msg_id
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 5, 10, 5)

        self.bubble_frame = QFrame()
        self.bubble_frame.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        bg_color = "#1A73E8" if is_self else "#F3F4F6"
        text_color = "white" if is_self else "black"
        self.bubble_frame.setStyleSheet(f"QFrame {{ background-color: {bg_color}; border-radius: 16px; border: none; }} QLabel {{ border: none; background: transparent; color: {text_color}; font-size: 13px; padding: 6px 10px; }}")
        
        bubble_layout = QVBoxLayout(self.bubble_frame)
        bubble_layout.setContentsMargins(5, 5, 5, 5)
        bubble_layout.setSpacing(4)

        if is_channel and not is_self and author != "Bot":
            name_label = QLabel(author)
            name_label.setStyleSheet("font-weight: bold; color: #1A73E8; font-size: 11px; padding: 0px 6px 0px 6px; margin: 0px;")
            bubble_layout.addWidget(name_label)

        if image_path and not os.path.exists(image_path): image_path = ""

        if image_path:
            try:
                reader = QImageReader(image_path)
                reader.setAutoTransform(True) 
                if reader.canRead():
                    orig_size = reader.size()
                    if orig_size.width() > 0 and orig_size.height() > 0:
                        orig_size.scale(250, 400, Qt.KeepAspectRatio)
                        reader.setScaledSize(orig_size)
                    image = reader.read()
                    if not image.isNull():
                        pixmap = QPixmap.fromImage(image)
                        img_label = QLabel()
                        img_label.setPixmap(pixmap)
                        img_label.setStyleSheet("border-radius: 6px; padding: 0px;") 
                        bubble_layout.addWidget(img_label)
            except:
                err_label = QLabel(t('IMG_ERR'))
                bubble_layout.addWidget(err_label)

        if text:
            words = text.split()
            formatted_text = "\n".join([" ".join(words[i:i+10]) for i in range(0, len(words), 10)])
            msg_label = QLabel(formatted_text)
            msg_label.setWordWrap(False) 
            msg_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            bubble_layout.addWidget(msg_label)

        time_text = timestamp
        if status: time_text += f" • {status}"
            
        time_label = QLabel(time_text)
        time_label.setStyleSheet("font-size: 10px; color: #888888; margin-top: 2px; border: none; padding: 0px;")

        meta_layout = QVBoxLayout()
        meta_layout.setSpacing(2)
        meta_layout.addWidget(self.bubble_frame)
        meta_layout.addWidget(time_label)
        
        alignment = Qt.AlignRight if is_self else Qt.AlignLeft
        meta_layout.setAlignment(self.bubble_frame, alignment)
        meta_layout.setAlignment(time_label, alignment)

        if is_self:
            self.layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
            self.layout.addLayout(meta_layout)
        else:
            self.avatar_label = QLabel()
            self.avatar_label.setPixmap(get_circular_avatar(avatar_path, author, 28))
            self.avatar_label.setAlignment(Qt.AlignTop)
            self.layout.addWidget(self.avatar_label)
            self.layout.addLayout(meta_layout)
            self.layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.bubble_frame.setContextMenuPolicy(Qt.CustomContextMenu)
        self.bubble_frame.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: white; border: none; } QMenu::item { padding: 8px 20px; color: red; font-size: 11px; } QMenu::item:selected { background-color: #FEE2E2; }")
        revoke_action = menu.addAction(t('REVOKE'))
        action = menu.exec_(self.bubble_frame.mapToGlobal(pos))
        if action == revoke_action:
            self.revoke_signal.emit(self, self.msg_id, self.text_content)

class MessengerUI(QWidget):
    send_msg_signal = pyqtSignal(str, str)
    search_user_signal = pyqtSignal(str) 
    request_delete_signal = pyqtSignal(str, str) 
    total_unread_updated = pyqtSignal(int) 
    initial_sync_signal = pyqtSignal(dict, list) 

    def __init__(self):
        super().__init__()
        load_dotenv()
        url: str = os.getenv("SUPABASE_URL")
        key: str = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        if not url or not key: self.supabase = None
        else: self.supabase: Client = create_client(url, key)

        self.chats_data = {} 
        self.current_user_id = None
        self.current_filter = "all" 
        
        self._last_rendered_chat_id = None
        self._rendered_msg_ids = set()

        self._inbox_debounce_timer = QTimer(self)
        self._inbox_debounce_timer.setSingleShot(True)
        self._inbox_debounce_timer.timeout.connect(self._do_refresh_inbox_list)

        self._chat_debounce_timer = QTimer(self)
        self._chat_debounce_timer.setSingleShot(True)
        self._chat_debounce_timer.timeout.connect(self._do_refresh_chat_display)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.setup_inbox_list()
        self.setup_chat_area()
        self.load_from_db()

    def update_total_unread(self):
        total = sum(data.get("unread_count", 0) for data in self.chats_data.values())
        self.total_unread_updated.emit(total)

    def apply_filter(self, filter_type):
        self.current_filter = filter_type
        
        self.btn_filter_all.setChecked(filter_type == "all")
        self.btn_filter_users.setChecked(filter_type == "users")
        self.btn_filter_customers.setChecked(filter_type == "customers")
        self.btn_filter_unread.setChecked(filter_type == "unread")

        self.chat_list.setUpdatesEnabled(False)
        for i in range(self.chat_list.count()):
            item = self.chat_list.item(i)
            chat_id = item.data(Qt.UserRole)
            data = self.chats_data.get(chat_id, {})
            
            unread = data.get("unread_count", 0)
            is_customer = data.get("is_customer", False)
            
            # [CẬP NHẬT] Ẩn mọi Channel khỏi Hộp Thư
            if data.get("name", "").startswith("#"):
                item.setHidden(True)
                continue

            if filter_type == "unread" and unread == 0: 
                item.setHidden(True)
            elif filter_type == "users" and is_customer:
                item.setHidden(True)
            elif filter_type == "customers" and not is_customer:
                item.setHidden(True)
            else: 
                item.setHidden(False)
                
        self.chat_list.setUpdatesEnabled(True)

    def _run_in_background(self, target_func, *args):
        threading.Thread(target=target_func, args=args, daemon=True).start()

    def _async_upsert_user(self, data):
        if not self.supabase: return
        try: self.supabase.table('users').upsert(data).execute()
        except: pass

    def _async_insert_msg(self, data):
        if not self.supabase: return
        try: self.supabase.table('messages').insert(data).execute()
        except: pass

    def _async_delete_msg(self, msg_id):
        if not self.supabase: return
        try: self.supabase.table('messages').delete().eq('msg_id', msg_id).execute()
        except: pass

    def _async_mark_all_read(self, user_id):
        if not self.supabase: return
        try: self.supabase.table('messages').update({'status': t('READ')}).eq('user_id', user_id).eq('status', t('RECEIVED')).execute()
        except: pass

    def _async_delete_user_and_msgs(self, user_id):
        if not self.supabase: return
        try:
            self.supabase.table('messages').delete().eq('user_id', user_id).execute()
            self.supabase.table('users').delete().eq('user_id', user_id).execute()
        except: pass

    def load_from_db(self):
        if not self.supabase: return
        try:
            users_res = self.supabase.table('users').select('*').execute()
            msgs_res = self.supabase.table('messages').select('*').execute()
            
            msgs_by_user = {}
            for m in msgs_res.data:
                uid = m['user_id']
                if uid not in msgs_by_user: msgs_by_user[uid] = []
                msgs_by_user[uid].append({
                    "sender": m['sender_name'], "text": m['text'], "time": m['time'],
                    "is_self": bool(m['is_self']), "msg_id": m['msg_id'], 
                    "image_path": m.get('image_path', ""), "status": m.get('status', t('READ'))
                })

            for uid in msgs_by_user: msgs_by_user[uid].sort(key=lambda x: get_sort_id(x.get("msg_id")))

            loaded_uids = set()
            for u in users_res.data:
                uid = u['user_id']
                uname = u['name']
                unread = u.get('unread_count') or 0
                pinned = u.get('pinned', False)
                is_customer = u.get('is_customer', False)
                loaded_uids.add(uid)
                
                avatar_path = ""
                if uname.startswith('#'):
                    avatar_path = os.path.join(IMAGE_DIR, f"guild_{uid}.png")
                else:
                    avatar_path = os.path.join(IMAGE_DIR, f"avatar_{uid}.png")
                
                if not os.path.exists(avatar_path): avatar_path = ""
                self.chats_data[uid] = {
                    "name": uname, "messages": msgs_by_user.get(uid, []), 
                    "unread_count": unread, "avatar_path": avatar_path, 
                    "pinned": pinned, "is_customer": is_customer
                }
            
            for uid, msgs in msgs_by_user.items():
                if uid not in loaded_uids:
                    uname = "Khách hàng"
                    avatar_path = os.path.join(IMAGE_DIR, f"avatar_{uid}.png")
                    if not os.path.exists(avatar_path): avatar_path = ""
                    self.chats_data[uid] = {
                        "name": uname, "messages": msgs, "unread_count": 0, 
                        "avatar_path": avatar_path, "pinned": False, "is_customer": False
                    }

            self.refresh_inbox_list()
            self.update_total_unread() 
        except: pass

    def save_user_to_db(self, user_id):
        data = {
            "user_id": user_id, 
            "name": self.chats_data[user_id]["name"], 
            "unread_count": self.chats_data[user_id]["unread_count"], 
            "avatar_path": self.chats_data[user_id].get("avatar_path", ""),
            "pinned": self.chats_data[user_id].get("pinned", False),
            "is_customer": self.chats_data[user_id].get("is_customer", False)
        }
        self._run_in_background(self._async_upsert_user, data)

    def save_msg_to_db(self, user_id, msg_data):
        data = {
            "user_id": user_id, "sender_name": msg_data["sender"], "text": msg_data["text"],
            "time": msg_data["time"], "is_self": bool(msg_data["is_self"]), "msg_id": msg_data["msg_id"],
            "image_path": msg_data.get("image_path", ""), "status": msg_data.get("status", t('READ')) 
        }
        self._run_in_background(self._async_insert_msg, data)

    def delete_msg_from_db(self, msg_id):
        self._run_in_background(self._async_delete_msg, msg_id)

    def on_bot_ready(self, msg):
        if hasattr(self, '_bot_ready_handled'): return
        self._bot_ready_handled = True
        sync_dict = {}
        user_ids = []
        for user_id, data in self.chats_data.items():
            user_ids.append(user_id)
            if data["messages"]:
                last_msg_id = data["messages"][-1].get("msg_id", "")
                if last_msg_id: sync_dict[user_id] = last_msg_id
        self.initial_sync_signal.emit(sync_dict, user_ids)

    def receive_avatar_update(self, chat_id, avatar_path):
        if chat_id in self.chats_data:
            self.chats_data[chat_id]["avatar_path"] = avatar_path
            self.refresh_inbox_list()
            if self.current_user_id == chat_id: self.refresh_chat_display()

    def setup_inbox_list(self):
        self.inbox_panel = QFrame()
        self.inbox_panel.setFixedWidth(320)
        self.inbox_panel.setStyleSheet("""
            QFrame { background-color: #FFFFFF; border: none; border-right: 1px solid #F3F4F6; }
            QLineEdit { padding: 8px; border: none; border-radius: 15px; margin: 15px; background: #F3F4F6; font-size: 12px; }
            QListWidget { border: none; outline: none; background: white; padding: 0px 5px; } 
            QListWidget::item { border: none; border-radius: 10px; margin-bottom: 2px; }
            QListWidget::item:hover { background-color: #F3F4F6; }
            QListWidget::item:selected { background-color: #E8F0FE; } 
            QPushButton { border: none; padding: 5px 10px; background: transparent; color: #666666; font-size: 11px; font-weight: bold; border-radius: 10px;}
            QPushButton:checked { background: #1A73E8; color: white; }
        """)
        
        layout = QVBoxLayout(self.inbox_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(t('SEARCH_CONVO'))
        self.search_bar.returnPressed.connect(self.emit_search_user)
        layout.addWidget(self.search_bar)
        
        filter_container = QWidget()
        filter_layout = QHBoxLayout(filter_container)
        filter_layout.setContentsMargins(15, 0, 15, 10)
        filter_layout.setSpacing(8)
        
        self.btn_filter_all = QPushButton("Tất cả")
        self.btn_filter_users = QPushButton("Người dùng")
        self.btn_filter_customers = QPushButton("Khách hàng")
        # [CẬP NHẬT] Xóa nút Lọc Kênh
        self.btn_filter_unread = QPushButton("Chưa đọc")
        
        buttons = [self.btn_filter_all, self.btn_filter_users, self.btn_filter_customers, self.btn_filter_unread]
        for btn in buttons:
            btn.setCheckable(True)
            filter_layout.addWidget(btn)
            
        filter_layout.addStretch() 
        self.btn_filter_all.setChecked(True)
        
        self.btn_filter_all.clicked.connect(lambda: self.apply_filter("all"))
        self.btn_filter_users.clicked.connect(lambda: self.apply_filter("users"))
        self.btn_filter_customers.clicked.connect(lambda: self.apply_filter("customers"))
        self.btn_filter_unread.clicked.connect(lambda: self.apply_filter("unread"))
        
        self.filter_scroll = QScrollArea()
        self.filter_scroll.setWidgetResizable(True)
        self.filter_scroll.setWidget(filter_container)
        self.filter_scroll.setFixedHeight(45)
        self.filter_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.filter_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.filter_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        def horizontal_wheel_event(event):
            self.filter_scroll.horizontalScrollBar().setValue(
                self.filter_scroll.horizontalScrollBar().value() - event.angleDelta().y()
            )
        self.filter_scroll.wheelEvent = horizontal_wheel_event
        
        layout.addWidget(self.filter_scroll)
        
        self.chat_list = QListWidget()
        self.chat_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.chat_list.itemClicked.connect(self.on_chat_selected)
        
        self.chat_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.chat_list.customContextMenuRequested.connect(self.show_chat_context_menu)
        
        layout.addWidget(self.chat_list)
        self.layout.addWidget(self.inbox_panel)

    def show_chat_context_menu(self, pos):
        item = self.chat_list.itemAt(pos)
        if not item: return
        
        user_id = item.data(Qt.UserRole)
        is_pinned = self.chats_data[user_id].get("pinned", False)
        is_customer = self.chats_data[user_id].get("is_customer", False)
        is_channel = self.chats_data[user_id]["name"].startswith('#')

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: white; border: 1px solid #D1D5DB; border-radius: 5px; } 
            QMenu::item { padding: 10px 25px 10px 15px; font-size: 13px; font-weight: bold; color: #374151;} 
            QMenu::item:selected { background-color: #E8F0FE; color: #1A73E8; }
            QMenu::separator { height: 1px; background: #E5E7EB; margin: 4px 0px 4px 0px; }
        """)
        
        pin_text = "Bỏ ghim" if is_pinned else "Ghim"
        pin_action = menu.addAction(pin_text)
        
        customer_action = None
        if not is_channel:
            menu.addSeparator()
            cust_text = "Hủy Khách hàng" if is_customer else "Đánh dấu Khách hàng"
            customer_action = menu.addAction(cust_text)
            
        menu.addSeparator()
        del_action = menu.addAction("Xóa đoạn chat")
        
        action = menu.exec_(self.chat_list.viewport().mapToGlobal(pos))
        if action == pin_action:
            self.toggle_pin_chat(user_id)
        elif customer_action and action == customer_action:
            self.toggle_customer_chat(user_id)
        elif action == del_action:
            self.delete_entire_chat(user_id)

    def toggle_pin_chat(self, user_id):
        current_pin = self.chats_data[user_id].get("pinned", False)
        self.chats_data[user_id]["pinned"] = not current_pin
        self.save_user_to_db(user_id)
        self.refresh_inbox_list()

    def toggle_customer_chat(self, user_id):
        current_cust = self.chats_data[user_id].get("is_customer", False)
        self.chats_data[user_id]["is_customer"] = not current_cust
        self.save_user_to_db(user_id)
        self.refresh_inbox_list()

    def delete_entire_chat(self, user_id):
        if user_id in self.chats_data:
            del self.chats_data[user_id]
        self._run_in_background(self._async_delete_user_and_msgs, user_id)
        if self.current_user_id == user_id:
            self.current_user_id = None
            self.refresh_chat_display()
        self.refresh_inbox_list()
        self.update_total_unread()

    def setup_chat_area(self):
        self.chat_panel = QFrame()
        self.chat_panel.setStyleSheet("background-color: #FFFFFF; border: none;")
        layout = QVBoxLayout(self.chat_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0) 
        
        self.scroll_container = QWidget()
        self.scroll_container_layout = QGridLayout(self.scroll_container)
        self.scroll_container_layout.setContentsMargins(0, 0, 0, 0)

        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet("background-color: white; border: none;")
        self.chat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll.verticalScrollBar().setSingleStep(15)
        
        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background-color: white; border: none;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_scroll.setWidget(self.chat_container)
        
        self.scroll_container_layout.addWidget(self.chat_scroll, 0, 0)
        
        self.overlay_layout = QVBoxLayout()
        self.overlay_layout.addStretch()
        self.btn_overlay_layout = QHBoxLayout()
        self.btn_overlay_layout.addStretch()

        self.btn_scroll_down = QPushButton(t('CURR_MSG'))
        self.btn_scroll_down.setCursor(Qt.PointingHandCursor)
        self.btn_scroll_down.setStyleSheet("""
            QPushButton { background-color: transparent; color: #1A73E8; font-weight: bold; border: none; font-size: 13px; outline: none; }
            QPushButton:hover, QPushButton:pressed { background-color: transparent; color: #1A73E8; border: none; outline: none; text-decoration: none; }
        """)
        self.btn_scroll_down.hide()
        self.btn_scroll_down.clicked.connect(self.smooth_scroll_to_bottom)

        self.btn_overlay_layout.addWidget(self.btn_scroll_down)
        self.btn_overlay_layout.addSpacing(20)
        self.overlay_layout.addLayout(self.btn_overlay_layout)
        self.overlay_layout.addSpacing(20)

        self.scroll_container_layout.addLayout(self.overlay_layout, 0, 0)
        self.chat_scroll.verticalScrollBar().valueChanged.connect(self.check_scroll_position)
        
        layout.addWidget(self.scroll_container, stretch=1) 
        
        input_container = QFrame()
        input_container.setStyleSheet("background-color: white; border: none; border-top: 1px solid #F3F4F6; padding: 10px 20px;")
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        quick_replies_widget = QWidget()
        quick_replies_layout = QHBoxLayout(quick_replies_widget)
        quick_replies_layout.setContentsMargins(0, 0, 0, 10) 
        quick_replies_layout.setSpacing(8)
        
        quick_messages = [t('Q1'), t('Q2'), t('Q3'), t('Q4'), t('Q5')]
        for msg in quick_messages:
            btn = QPushButton(msg)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("QPushButton { background-color: #E8F0FE; color: #1A73E8; border-radius: 14px; padding: 8px 14px; border: none; font-weight: bold; font-size: 12px; } QPushButton:hover { background-color: #D2E3FC; }")
            btn.clicked.connect(lambda checked, m=msg: self.send_quick_message(m))
            quick_replies_layout.addWidget(btn)
        quick_replies_layout.addStretch() 
        
        quick_scroll = QScrollArea()
        quick_scroll.setWidgetResizable(True)
        quick_scroll.setWidget(quick_replies_widget)
        quick_scroll.setFixedHeight(50)
        quick_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        quick_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        quick_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        quick_scroll.horizontalScrollBar().setSingleStep(10)
        
        def horizontal_wheel_event(event):
            quick_scroll.horizontalScrollBar().setValue(
                quick_scroll.horizontalScrollBar().value() - event.angleDelta().y()
            )
        quick_scroll.wheelEvent = horizontal_wheel_event
        
        input_layout.addWidget(quick_scroll)
        
        bottom_input_layout = QHBoxLayout()
        bottom_input_layout.setContentsMargins(0, 0, 0, 0)
        self.msg_input = ChatInputBox()
        self.msg_input.send_message_signal.connect(self.emit_send_message)
        
        icon_style = "background-color: #F3F4F6; border-radius: 18px; border: none;"
        
        btn_img = QPushButton()
        btn_img.setIcon(QIcon("icons/images.png"))
        btn_img.setIconSize(QSize(18, 18))
        btn_img.setFixedSize(36, 36)
        btn_img.setStyleSheet(icon_style)
        
        btn_emo = QPushButton()
        btn_emo.setIcon(QIcon("icons/emoji.png"))
        btn_emo.setIconSize(QSize(18, 18))
        btn_emo.setFixedSize(36, 36)
        btn_emo.setStyleSheet(icon_style)
        
        btn_att = QPushButton()
        btn_att.setIcon(QIcon("icons/link.png"))
        btn_att.setIconSize(QSize(18, 18))
        btn_att.setFixedSize(36, 36)
        btn_att.setStyleSheet(icon_style)
        
        self.btn_send = QPushButton()
        self.btn_send.setIcon(QIcon("icons/send.png"))
        self.btn_send.setIconSize(QSize(18, 18))
        self.btn_send.setStyleSheet("background-color: transparent; border: none;")
        self.btn_send.setFixedSize(36, 36)
        self.btn_send.setCursor(Qt.PointingHandCursor)
        self.btn_send.clicked.connect(self.emit_send_message)
        
        bottom_input_layout.addWidget(self.msg_input)
        bottom_input_layout.addSpacing(10)
        bottom_input_layout.addWidget(btn_img)
        bottom_input_layout.addWidget(btn_emo)
        bottom_input_layout.addWidget(btn_att)
        bottom_input_layout.addWidget(self.btn_send)
        input_layout.addLayout(bottom_input_layout)
        
        layout.addWidget(input_container)
        self.layout.addWidget(self.chat_panel)

    def check_scroll_position(self):
        bar = self.chat_scroll.verticalScrollBar()
        if bar.maximum() - bar.value() > 150: self.btn_scroll_down.show()
        else: self.btn_scroll_down.hide()

    def smooth_scroll_to_bottom(self):
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self._animate_scroll_step)
        self.anim_timer.start(15)

    def _animate_scroll_step(self):
        bar = self.chat_scroll.verticalScrollBar()
        current = bar.value()
        target = bar.maximum()
        if current >= target:
            self.anim_timer.stop()
            return
        step = (target - current) // 5
        if step == 0: step = 1
        bar.setValue(current + step)

    def force_scroll_to_bottom(self):
        bar = self.chat_scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    # [CẬP NHẬT] Tự động mở chat khi tìm kiếm ID
    def emit_search_user(self):
        user_id = self.search_bar.text().strip()
        if user_id.isdigit():
            self.open_chat_with_user(user_id)
            self.search_bar.clear()

    # [CẬP NHẬT] Hàm gọi để mở chat trực tiếp (dùng chung cho tìm kiếm và click sidebar)
    def open_chat_with_user(self, user_id, user_name="Khách hàng"):
        self.current_user_id = user_id
        if user_id not in self.chats_data:
            self.chats_data[user_id] = {
                "name": user_name, "messages": [], "unread_count": 0, 
                "avatar_path": "", "pinned": False, "is_customer": False
            }
            self.search_user_signal.emit(user_id)
        else:
            QTimer.singleShot(100, self.force_scroll_to_bottom)
        self.refresh_inbox_list()
        self.refresh_chat_display()

    def receive_new_user_from_search(self, chat_id, chat_name, avatar_path):
        if chat_id not in self.chats_data:
            self.chats_data[chat_id] = {"name": chat_name, "messages": [], "unread_count": 0, "avatar_path": avatar_path, "pinned": False, "is_customer": False}
            self.save_user_to_db(chat_id)
        else:
            self.chats_data[chat_id]["avatar_path"] = avatar_path
            self.save_user_to_db(chat_id)
        self.refresh_inbox_list()

    def receive_history(self, chat_id, chat_name, avatar_path, history_list):
        existing_data = self.chats_data.get(chat_id)
        if existing_data:
            existing_msgs = existing_data["messages"]
            existing_ids = {m["msg_id"] for m in existing_msgs}
            new_msgs_added = False
            for msg in history_list:
                if msg["msg_id"] not in existing_ids:
                    existing_msgs.append(msg)
                    self.save_msg_to_db(chat_id, msg)
                    new_msgs_added = True
            if new_msgs_added:
                existing_msgs.sort(key=lambda x: get_sort_id(x.get("msg_id")))
            if avatar_path and not existing_data["avatar_path"]:
                existing_data["avatar_path"] = avatar_path
                self.save_user_to_db(chat_id)
        else:
            self.chats_data[chat_id] = {"name": chat_name, "messages": history_list, "unread_count": 0, "avatar_path": avatar_path, "pinned": False, "is_customer": False}
            self.save_user_to_db(chat_id)
            for msg in history_list: self.save_msg_to_db(chat_id, msg)
            self.chats_data[chat_id]["messages"].sort(key=lambda x: get_sort_id(x.get("msg_id")))

        self.refresh_inbox_list()
        if self.current_user_id == chat_id: self.refresh_chat_display()

    def receive_incoming_message(self, chat_id, chat_name, sender_name, text, timestamp, msg_id, image_path, avatar_path):
        if chat_id not in self.chats_data:
            self.chats_data[chat_id] = {"name": chat_name, "messages": [], "unread_count": 0, "avatar_path": avatar_path, "pinned": False, "is_customer": False}
        else:
            self.chats_data[chat_id]["avatar_path"] = avatar_path
            
        status = t('READ') if self.current_user_id == chat_id else t('RECEIVED')
        new_msg = { "sender": sender_name, "text": text, "time": timestamp, "is_self": False, "msg_id": msg_id, "image_path": image_path, "status": status }
        self.chats_data[chat_id]["messages"].append(new_msg)
        self.chats_data[chat_id]["messages"].sort(key=lambda x: get_sort_id(x.get("msg_id")))
        self.save_msg_to_db(chat_id, new_msg)

        if self.current_user_id != chat_id: self.chats_data[chat_id]["unread_count"] += 1
        self.save_user_to_db(chat_id)
        
        self.refresh_inbox_list()
        self.update_total_unread() 
        if self.current_user_id == chat_id:
            is_channel = chat_name.startswith('#')
            self.render_single_message(sender_name, text, timestamp, False, msg_id, image_path, avatar_path, status, is_channel)

    def receive_sent_message_confirmation(self, chat_id, text, timestamp, msg_id, image_path, status_text=None):
        if status_text is None: status_text = t('SENT')
        if chat_id not in self.chats_data: return
        new_msg = { "sender": "Bot", "text": text, "time": timestamp, "is_self": True, "msg_id": msg_id, "image_path": image_path, "status": status_text }
        self.chats_data[chat_id]["messages"].append(new_msg)
        self.chats_data[chat_id]["messages"].sort(key=lambda x: get_sort_id(x.get("msg_id")))
        self.save_msg_to_db(chat_id, new_msg)

        self.refresh_inbox_list()
        
        is_channel = self.chats_data[chat_id]["name"].startswith('#')
        if self.current_user_id == chat_id:
            self.render_single_message("Bot", text, timestamp, True, msg_id, image_path, "", status_text, is_channel, force_scroll=True)

    def refresh_chat_display(self):
        self._chat_debounce_timer.start(50)

    def _do_refresh_chat_display(self):
        if not self.current_user_id or self.current_user_id not in self.chats_data:
            self._clear_chat_area()
            return

        self.chat_container.setUpdatesEnabled(False)

        if self._last_rendered_chat_id != self.current_user_id:
            self._clear_chat_area()
            self._last_rendered_chat_id = self.current_user_id
            self._rendered_msg_ids = set()

        data = self.chats_data[self.current_user_id]
        avatar_path = data.get("avatar_path", "")
        is_channel = data["name"].startswith('#')
        
        new_msgs_added = False
        for msg in data["messages"]:
            msg_id = msg.get("msg_id", "")
            if msg_id not in self._rendered_msg_ids:
                self.render_single_message(
                    msg["sender"], msg["text"], msg["time"], 
                    msg["is_self"], msg_id, msg.get("image_path", ""), 
                    avatar_path, msg.get("status", ""), is_channel
                )
                if msg_id:
                    self._rendered_msg_ids.add(msg_id)
                new_msgs_added = True
        
        self.chat_container.setUpdatesEnabled(True)
        if new_msgs_added:
            QTimer.singleShot(10, self.force_scroll_to_bottom)
            
    def _clear_chat_area(self):
        while self.chat_layout.count() > 0:
            item = self.chat_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._rendered_msg_ids = set()
        self._last_rendered_chat_id = None

    def on_chat_selected(self, item):
        user_id = item.data(Qt.UserRole)
        self.current_user_id = user_id
        
        messages_changed = False
        if user_id in self.chats_data:
            for msg in self.chats_data[user_id]["messages"]:
                if msg.get("status") == t('RECEIVED'):
                    msg["status"] = t('READ')
                    messages_changed = True
        
        if messages_changed: self._run_in_background(self._async_mark_all_read, user_id)
        self.refresh_chat_display()

        if self.chats_data[user_id]["unread_count"] > 0:
            self.chats_data[user_id]["unread_count"] = 0
            self.save_user_to_db(user_id)
            self.refresh_inbox_list()
            self.update_total_unread()

    def send_quick_message(self, text):
        if not self.current_user_id: return
        self.send_msg_signal.emit(self.current_user_id, text)

    def emit_send_message(self):
        if not self.current_user_id: return
        text = self.msg_input.toPlainText().strip()
        if text:
            QTimer.singleShot(0, self.msg_input.clear)
            self.send_msg_signal.emit(self.current_user_id, text)
            QTimer.singleShot(50, self.force_scroll_to_bottom)
            QTimer.singleShot(200, self.force_scroll_to_bottom)

    def refresh_inbox_list(self):
        self._inbox_debounce_timer.start(50)

    def _do_refresh_inbox_list(self):
        v_scroll = self.chat_list.verticalScrollBar().value()
        self.chat_list.setUpdatesEnabled(False)

        sorted_uids = sorted(
            self.chats_data.keys(),
            key=lambda k: (
                self.chats_data[k].get("pinned", False),
                get_sort_id(self.chats_data[k]["messages"][-1].get("msg_id")) if self.chats_data[k]["messages"] else 0
            ),
            reverse=True
        )

        target_count = len(sorted_uids)
        while self.chat_list.count() > target_count:
            self.chat_list.takeItem(self.chat_list.count() - 1)
        while self.chat_list.count() < target_count:
            new_item = QListWidgetItem()
            new_item.setSizeHint(QSize(0, 70))
            new_widget = InboxItemWidget("", "", 0, "") 
            self.chat_list.addItem(new_item)
            self.chat_list.setItemWidget(new_item, new_widget)

        for row_index, uid in enumerate(sorted_uids):
            data = self.chats_data[uid]
            msgs = data["messages"]
            is_channel = data["name"].startswith('#')
            
            if msgs:
                last_m = msgs[-1]
                if is_channel and not last_m["is_self"] and last_m["text"]:
                    last_msg = f"{last_m['sender']}: {last_m['text']}"
                else:
                    last_msg = last_m["text"] if last_m["text"] else t('PICTURE')
            else:
                last_msg = t('START_CONVO')

            snippet = (last_msg[:30] + '...') if len(last_msg) > 30 else last_msg

            item = self.chat_list.item(row_index)
            item.setData(Qt.UserRole, uid)
            
            widget = self.chat_list.itemWidget(item)
            widget.update_data(data["name"], snippet, data.get("unread_count", 0), data.get("avatar_path", ""), data.get("pinned", False))
            
            if uid == self.current_user_id:
                item.setSelected(True)
            else:
                item.setSelected(False)

        self.apply_filter(self.current_filter)
        self.chat_list.setUpdatesEnabled(True)
        self.chat_list.verticalScrollBar().setValue(v_scroll)

    def render_single_message(self, author, text, timestamp, is_self=False, msg_id="", image_path="", avatar_path="", status="", is_channel=False, force_scroll=False):
        bubble = MessageBubble(author, text, timestamp, is_self, msg_id, image_path, avatar_path, status, is_channel, parent=self.chat_container)
        bubble.revoke_signal.connect(self.handle_revoke_message)
        self.chat_layout.addWidget(bubble)
        
        bar = self.chat_scroll.verticalScrollBar()
        if force_scroll or bar.maximum() - bar.value() < 150:
            QTimer.singleShot(50, lambda: bar.setValue(bar.maximum()))

    def handle_revoke_message(self, bubble_widget, msg_id, text):
        self.chat_layout.removeWidget(bubble_widget)
        bubble_widget.deleteLater()
        
        if msg_id in self._rendered_msg_ids:
            self._rendered_msg_ids.remove(msg_id)
            
        if self.current_user_id in self.chats_data:
            messages = self.chats_data[self.current_user_id]["messages"]
            for msg in messages:
                if msg.get("msg_id") == msg_id:
                    messages.remove(msg)
                    self.delete_msg_from_db(msg_id)
                    break
        if msg_id: self.request_delete_signal.emit(self.current_user_id, msg_id)