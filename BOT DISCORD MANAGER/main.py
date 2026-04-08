import sys
import os
import traceback
from dotenv import load_dotenv

# [CẬP NHẬT] CHỈ tắt cảnh báo rác (Font OpenType) của PyQt5
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false;qt.text.font.*=false"

# [CẬP NHẬT] Bật lại bộ bắt lỗi của Python để biết App đang crash ở đâu
def global_exception_handler(exctype, value, tb):
    print("\n--- LỖI HỆ THỐNG / SYSTEM ERROR ---")
    traceback.print_exception(exctype, value, tb)

sys.excepthook = global_exception_handler
load_dotenv()

os.environ['APP_LANG'] = 'vi'

from const.lang import t
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QFrame, QStackedWidget, QLabel, QProgressBar, QGraphicsDropShadowEffect
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, qInstallMessageHandler

# Khóa miệng cảnh báo của PyQt5
def qt_message_handler(mode, context, message):
    pass
qInstallMessageHandler(qt_message_handler)

from ui.messenger_ui import MessengerUI
from ui.dashboard_ui import DashboardUI 
from ui.autorep_ui import AutoRepUI  
from ui.applications_ui import ApplicationsUI 
from ui.staff_ui import StaffUI 

from const.messenger import DiscordBotLogic

TOKEN = os.getenv("DISCORD_TOKEN")

class LoadingScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(450, 260)

        self.frame = QFrame(self)
        self.frame.setGeometry(15, 15, 420, 230)
        self.frame.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 15px; }")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 4)
        self.frame.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.frame)
        layout.setContentsMargins(40, 40, 40, 30)

        self.title = QLabel("NEXGENO")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("font-size: 28px; font-weight: 900; color: #1A73E8; letter-spacing: 2px;")
        layout.addWidget(self.title)

        self.subtitle = QLabel("Hệ Thống Quản Lý Discord Bot")
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.subtitle.setStyleSheet("font-size: 13px; font-weight: bold; color: #6B7280; margin-bottom: 25px;")
        layout.addWidget(self.subtitle)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setStyleSheet("""
            QProgressBar { border: none; border-radius: 3px; background-color: #E5E7EB; }
            QProgressBar::chunk { background-color: #1A73E8; border-radius: 3px; }
        """)
        layout.addWidget(self.progress)

        self.status_lbl = QLabel("Đang kết nối đến hệ thống...")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        self.status_lbl.setStyleSheet("font-size: 12px; color: #9CA3AF; margin-top: 15px;")
        layout.addWidget(self.status_lbl)

    def update_progress(self, percent, text):
        self.progress.setValue(percent)
        self.status_lbl.setText(text)


class SidebarButton(QWidget):
    clicked = pyqtSignal()
    
    def __init__(self, text, badge_text="", badge_color=""):
        super().__init__()
        self.setFixedHeight(40)
        self.setCursor(Qt.PointingHandCursor)
        self.is_checked = False
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 0, 15, 0)
        self.layout.setSpacing(12)
        
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(18, 18)
        self.icon_label.setStyleSheet("background-color: #6B7280; border-radius: 9px;") 
        
        self.text_label = QLabel(text)
        self.text_label.setStyleSheet("color: #9CA3AF; font-size: 13px; font-weight: bold; background: transparent;")
        
        self.layout.addWidget(self.icon_label)
        self.layout.addWidget(self.text_label)
        self.layout.addStretch()
        
        self.badge_color = badge_color if badge_color else "#EF4444"
        self.badge = QLabel()
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setFixedHeight(20)
        self.layout.addWidget(self.badge)
        self.set_badge(badge_text)
            
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.update_style()
        
    def set_badge(self, text):
        if text and str(text) != "0":
            self.badge.setText(str(text))
            self.badge.setStyleSheet(f"background-color: {self.badge_color}; color: white; border-radius: 10px; padding: 2px 6px; font-size: 10px; font-weight: bold;")
            self.badge.setVisible(True)
        else:
            self.badge.setVisible(False)

    def update_style(self):
        if self.is_checked:
            self.setStyleSheet("SidebarButton { background-color: #1A73E8; border-radius: 8px; }")
            self.text_label.setStyleSheet("color: white; font-size: 13px; font-weight: bold; background: transparent;")
            self.icon_label.setStyleSheet("background-color: white; border-radius: 9px;") 
        else:
            self.setStyleSheet("SidebarButton { background-color: transparent; border-radius: 8px; }")
            self.text_label.setStyleSheet("color: #9CA3AF; font-size: 13px; font-weight: bold; background: transparent;")
            self.icon_label.setStyleSheet("background-color: #6B7280; border-radius: 9px;")
            
    def enterEvent(self, event):
        if not self.is_checked:
            self.text_label.setStyleSheet("color: white; font-size: 13px; font-weight: bold; background: transparent;")
            self.icon_label.setStyleSheet("background-color: white; border-radius: 9px;")
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.update_style()
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

class MainApp(QMainWindow):
    def __init__(self, splash=None):
        super().__init__()
        self.splash = splash
        self.setWindowTitle("Bot Manager")
        self.resize(1500, 800)
        self.setWindowIcon(QIcon("logo.png"))
        
        self.main_widget = QWidget()
        self.main_layout = QHBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setCentralWidget(self.main_widget)

        self.inbox_btn = None
        self.applications_btn = None
        
        self.content_area = QStackedWidget()
        
        self.messenger_ui = MessengerUI()
        self.dashboard_ui = DashboardUI()
        self.autorep_ui = AutoRepUI() 
        self.applications_ui = ApplicationsUI() 
        self.staff_ui = StaffUI() 
        
        self.setup_sidebar()
        
        self.main_layout.addWidget(self.content_area)
        self.content_area.addWidget(self.dashboard_ui) 
        self.content_area.addWidget(self.messenger_ui)
        self.content_area.addWidget(self.autorep_ui)
        self.content_area.addWidget(self.staff_ui) 
        self.content_area.addWidget(self.applications_ui) 

        self.messenger_ui.total_unread_updated.connect(self.update_inbox_badge)
        self.messenger_ui.update_total_unread()
        
        self.dashboard_ui.go_to_chat_signal.connect(self.switch_to_chat)
        self.applications_ui.go_to_chat_signal.connect(self.switch_to_chat) 
        self.staff_ui.go_to_chat_signal.connect(self.switch_to_chat)
        
        self.setup_bot_logic()

    def mousePressEvent(self, event):
        focus_widget = QApplication.focusWidget()
        if focus_widget:
            focus_widget.clearFocus()
        super().mousePressEvent(event)

    def update_inbox_badge(self, total_unread):
        if self.inbox_btn:
            self.inbox_btn.set_badge(str(total_unread) if total_unread > 0 else "")

    def update_applications_badge(self, total_pending):
        if self.applications_btn:
            self.applications_btn.set_badge(str(total_pending) if total_pending > 0 else "")

    def setup_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(240)
        self.sidebar.setStyleSheet("QFrame { background-color: #111827; border: none; }") 
        
        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(2)
        
        self.sidebar_buttons = []
        
        menu_structure = [
            (t('OVERVIEW'), [(t('DASHBOARD'), "", "")]),
            (t('MANAGEMENT'), [
                (t('INBOX'), "", "#EF4444"), 
                (t('AUTOREP'), "", ""),
                ("Nhân viên", "", ""), 
                ("Đơn xin việc", "", "#EF4444") 
            ]),
            (t('SALES'), [
                (t('CUSTOMERS'), "", ""),
                (t('ORDERS'), "", "#F97316"), 
                (t('REPORTS'), "", "")
            ]),
            (t('SYSTEM'), [(t('SETTINGS'), "", "")])
        ]
        
        for group_name, items in menu_structure:
            group_lbl = QLabel(group_name)
            group_lbl.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: bold; padding-top: 15px; padding-bottom: 5px; padding-left: 5px;")
            layout.addWidget(group_lbl)
            
            for text, badge_text, badge_color in items:
                btn = SidebarButton(text, badge_text, badge_color)
                btn.clicked.connect(lambda b=btn: self.on_sidebar_clicked(b))
                layout.addWidget(btn)
                self.sidebar_buttons.append(btn)
                
                if text == t('DASHBOARD'):
                    btn.is_checked = True
                    btn.update_style()
                if text == t('INBOX') or text == "Hộp thư":
                    self.inbox_btn = btn
                if text == "Đơn xin việc":
                    self.applications_btn = btn
                    
        layout.addStretch()
        self.main_layout.addWidget(self.sidebar)

    def on_sidebar_clicked(self, clicked_btn):
        for btn in self.sidebar_buttons:
            btn.is_checked = (btn == clicked_btn)
            btn.update_style()
        
        text = clicked_btn.text_label.text()
        if text == t('INBOX') or text == "Hộp thư":
            self.content_area.setCurrentWidget(self.messenger_ui)
        elif text == t('DASHBOARD') or text == "Dashboard":
            self.content_area.setCurrentWidget(self.dashboard_ui)
        elif text == t('AUTOREP') or text == "Trả lời tự động":
            self.content_area.setCurrentWidget(self.autorep_ui)
        elif text == "Nhân viên":
            self.content_area.setCurrentWidget(self.staff_ui)
        elif text == "Đơn xin việc":
            self.content_area.setCurrentWidget(self.applications_ui)

    def switch_to_chat(self, user_id, user_name):
        for btn in self.sidebar_buttons:
            if btn.text_label.text() == t('INBOX') or btn.text_label.text() == "Hộp thư":
                self.on_sidebar_clicked(btn)
                break
        self.messenger_ui.search_bar.setText(user_id)
        self.messenger_ui.emit_search_user()

    def setup_bot_logic(self):
        if not TOKEN:
            if self.splash: self.splash.update_progress(100, "Lỗi: Chưa có Token!")
            self.show()
            return

        self.bot_thread = DiscordBotLogic(TOKEN)
        
        self.bot_thread.incoming_msg_signal.connect(self.messenger_ui.receive_incoming_message)
        self.bot_thread.history_signal.connect(self.messenger_ui.receive_history)
        self.bot_thread.user_fetched_signal.connect(self.messenger_ui.receive_new_user_from_search)
        self.bot_thread.message_sent_signal.connect(self.messenger_ui.receive_sent_message_confirmation)
        
        self.messenger_ui.send_msg_signal.connect(self.bot_thread.send_message_to_discord)
        self.messenger_ui.search_user_signal.connect(self.bot_thread.search_user_by_id)
        self.messenger_ui.request_delete_signal.connect(self.bot_thread.delete_message_on_discord)
        
        self.bot_thread.avatar_updated_signal.connect(self.messenger_ui.receive_avatar_update)
        self.messenger_ui.initial_sync_signal.connect(self.bot_thread.start_initial_sync)
        
        self.bot_thread.members_fetched_signal.connect(self.dashboard_ui.update_members)
        
        if hasattr(self.applications_ui, 'total_pending_updated'):
            self.applications_ui.total_pending_updated.connect(self.update_applications_badge)
        self.applications_ui.approve_signal.connect(self.bot_thread.handle_approve_app)
        self.applications_ui.reject_signal.connect(self.bot_thread.handle_reject_app)
        self.applications_ui.sync_draft_signal.connect(self.bot_thread.handle_sync_draft)
        
        self.staff_ui.sync_profile_signal.connect(self.bot_thread.handle_update_staff)
        if hasattr(self.staff_ui, 'delete_staff_signal'):
            self.staff_ui.delete_staff_signal.connect(self.bot_thread.handle_delete_staff)
        self.bot_thread.staff_update_success_signal.connect(self.staff_ui.on_update_success)
        
        self.applications_ui.request_upload_image_signal.connect(self.bot_thread.handle_upload_local_image)
        self.staff_ui.request_upload_image_signal.connect(self.bot_thread.handle_upload_local_image)
        self.bot_thread.image_uploaded_to_discord.connect(self.applications_ui.receive_uploaded_image)
        self.bot_thread.image_uploaded_to_discord.connect(self.staff_ui.receive_uploaded_image)
        
        self.bot_thread.new_application_signal.connect(self.applications_ui.load_data)
        self.bot_thread.staff_updated_signal.connect(self.staff_ui.load_data)
        
        if self.splash:
            self.bot_thread.progress_signal.connect(self.splash.update_progress)
            
        self.bot_thread.sync_completed_signal.connect(self.on_sync_completed)
        self.bot_thread.bot_ready_signal.connect(self.messenger_ui.on_bot_ready)
        
        self.bot_thread.start()

    def on_sync_completed(self):
        if not self.isVisible() and not hasattr(self, '_is_verifying'):
            self._is_verifying = True
            if self.splash:
                self.splash.update_progress(100, "Xác minh hoàn tất! Đang khởi động UI...")
            QTimer.singleShot(1000, self.finish_verification)

    def finish_verification(self):
        if self.splash:
            self.splash.close()
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    splash = LoadingScreen()
    splash.show()
    
    window = MainApp(splash)
    sys.exit(app.exec_())