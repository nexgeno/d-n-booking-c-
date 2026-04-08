# ui/autorep_ui.py

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QLabel, QFrame, QLineEdit, QPushButton, QTextEdit, QMenu, QApplication)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from const.autorep import load_auto_replies, add_or_update_reply, delete_reply, AUTO_REPLIES_CACHE
from const.lang import t
import threading

class AutoRepUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #F3F4F6;")
        self.layout = QHBoxLayout(self) 
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(20)

        left_container = QWidget()
        left_container.setFixedWidth(350)
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        form_frame = QFrame()
        form_frame.setStyleSheet("background-color: white; border-radius: 12px;")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(20, 25, 20, 25)
        form_layout.setSpacing(15)

        # [CẬP NHẬT] Đã gỡ bỏ tiêu đề "THÊM TỪ KHÓA MỚI"

        lbl_kw = QLabel(t('KW_TRIGGER'))
        lbl_kw.setStyleSheet("font-size: 12px; font-weight: bold; color: #6B7280;")
        form_layout.addWidget(lbl_kw)

        self.kw_input = QLineEdit()
        self.kw_input.setPlaceholderText(t('KW_PLACEHOLDER'))
        self.kw_input.setFocusPolicy(Qt.ClickFocus)
        self.kw_input.setStyleSheet("padding: 12px; border: 1px solid #D1D5DB; border-radius: 8px; font-size: 13px; background-color: #F9FAFB; color: #111827;")
        form_layout.addWidget(self.kw_input)

        lbl_res = QLabel(t('BOT_REPLY'))
        lbl_res.setStyleSheet("font-size: 12px; font-weight: bold; color: #6B7280; margin-top: 10px;")
        form_layout.addWidget(lbl_res)

        self.res_input = QTextEdit()
        self.res_input.setPlaceholderText(t('REPLY_PLACEHOLDER'))
        self.res_input.setFocusPolicy(Qt.ClickFocus)
        self.res_input.setStyleSheet("padding: 12px; border: 1px solid #D1D5DB; border-radius: 8px; font-size: 13px; background-color: #F9FAFB; color: #111827;")
        form_layout.addWidget(self.res_input)

        self.btn_save = QPushButton(t('SAVE_KW'))
        self.btn_save.setFixedHeight(45)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet("""
            QPushButton { background-color: #1A73E8; color: white; font-weight: bold; font-size: 13px; border-radius: 8px; border: none; margin-top: 10px;}
            QPushButton:hover { background-color: #1557B0; }
        """)
        self.btn_save.clicked.connect(self.save_keyword)
        form_layout.addWidget(self.btn_save)

        left_layout.addWidget(form_frame)
        left_layout.addStretch()
        self.layout.addWidget(left_container)

        right_container = QFrame()
        right_container.setStyleSheet("background-color: white; border-radius: 12px;")
        table_layout = QVBoxLayout(right_container)
        table_layout.setContentsMargins(20, 20, 20, 20)

        # [CẬP NHẬT] Đã gỡ bỏ tiêu đề "Danh sách Kịch bản Tự động"

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels([t('COL_KW'), t('COL_REPLY')])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)

        self.table.setStyleSheet("""
            QTableWidget { border: none; background-color: white; font-size: 13px; color: #374151; gridline-color: #E5E7EB; outline: none; }
            QHeaderView::section { background-color: #F9FAFB; color: #6B7280; font-weight: bold; padding: 15px; border: none; border-bottom: 1px solid #E5E7EB; text-align: left; }
            QTableWidget::item { padding: 12px; border-bottom: 1px solid #F3F4F6; }
            QTableWidget::item:hover { background-color: transparent; }
        """)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        table_layout.addWidget(self.table)
        self.layout.addWidget(right_container, stretch=1)

        threading.Thread(target=self.load_data_thread, daemon=True).start()

    def mousePressEvent(self, event):
        focus_widget = QApplication.focusWidget()
        if focus_widget:
            focus_widget.clearFocus()
        super().mousePressEvent(event)

    def load_data_thread(self):
        load_auto_replies()
        QTimer.singleShot(0, self.refresh_table)

    def refresh_table(self):
        v_scroll = self.table.verticalScrollBar().value()
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(AUTO_REPLIES_CACHE))
        for row, (kw, res) in enumerate(AUTO_REPLIES_CACHE.items()):
            item_kw = QTableWidgetItem(kw)
            font = QFont()
            font.setBold(True)
            item_kw.setFont(font)
            self.table.setItem(row, 0, item_kw)
            self.table.setItem(row, 1, QTableWidgetItem(res))
        self.table.setUpdatesEnabled(True)
        self.table.verticalScrollBar().setValue(v_scroll)

    def save_keyword(self):
        kw = self.kw_input.text().strip()
        res = self.res_input.toPlainText().strip()
        if not kw or not res: return
        self.btn_save.setText(t('SAVING'))
        self.btn_save.setDisabled(True)

        def worker():
            add_or_update_reply(kw, res)
            QTimer.singleShot(0, self.on_save_done)

        threading.Thread(target=worker, daemon=True).start()

    def on_save_done(self):
        self.kw_input.clear()
        self.res_input.clear()
        self.kw_input.clearFocus()
        self.res_input.clearFocus()
        self.btn_save.setText(t('SAVE_KW'))
        self.btn_save.setDisabled(False)
        self.refresh_table()

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if item:
            row = item.row()
            kw = self.table.item(row, 0).text()

            menu = QMenu(self.table)
            menu.setStyleSheet("""
                QMenu { background-color: white; border: 1px solid #D1D5DB; border-radius: 5px; } 
                QMenu::item { padding: 10px 25px 10px 15px; font-size: 13px; font-weight: bold; color: #374151;} 
                QMenu::item:selected { background-color: #E8F0FE; color: #1A73E8; }
            """)
            del_action = menu.addAction(t('DEL_SCRIPT'))
            
            action = menu.exec_(self.table.viewport().mapToGlobal(pos))
            if action == del_action:
                threading.Thread(target=self.delete_worker, args=(kw,), daemon=True).start()

    def delete_worker(self, kw):
        delete_reply(kw)
        QTimer.singleShot(0, self.refresh_table)