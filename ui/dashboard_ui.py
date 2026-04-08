from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QLabel, QFrame, QLineEdit, QComboBox, QMenu, QStackedWidget, QApplication, QListWidget, QPushButton, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QTimer
from PyQt5.QtGui import QPainter, QColor, QFont, QPainterPath, QPen
from const.dashboard import get_dashboard_headers_member, get_dashboard_headers_channel
from const.lang import t
from datetime import datetime, timedelta

class MemberPopup(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating) 
        
        self.setStyleSheet("""
            QFrame { background-color: white; border: 1px solid #D1D5DB; border-radius: 8px; }
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { border: none; outline: none; background-color: white; font-size: 13px; color: #374151; font-weight: bold;}
            QListWidget::item { padding: 8px 10px; border-bottom: 1px solid #F3F4F6; }
            QListWidget::item:selected { background-color: transparent; color: #374151; }
        """)
        self.list_widget.setSelectionMode(QListWidget.NoSelection)
        self.list_widget.setFocusPolicy(Qt.NoFocus)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff) 
        self.layout.addWidget(self.list_widget)

    def show_data(self, names, pos):
        self.list_widget.clear()
        self.list_widget.addItems(names)
        h = min(len(names) * 36 + 12, 250) 
        self.setFixedSize(220, h)
        self.move(pos)
        self.show()
        self.raise_()

class ClickableCard(QFrame):
    clicked = pyqtSignal(str)
    
    def __init__(self, title, value, inactive_bg, active_bg, identifier):
        super().__init__()
        self.identifier = identifier
        self.inactive_bg = inactive_bg
        self.active_bg = active_bg
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"background-color: {self.inactive_bg}; border: none; border-radius: 10px; padding: 15px;")
        vbox = QVBoxLayout(self)
        vbox.setSpacing(5)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: white; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet("color: white; font-size: 28px; font-weight: bold; background: transparent; border: none;")
        self.lbl_sub = QLabel("")
        self.lbl_sub.setStyleSheet("color: #E0F2FE; font-size: 11px; font-weight: bold; background: transparent; border: none;")
        
        vbox.addWidget(lbl_title)
        vbox.addWidget(self.lbl_value)
        vbox.addWidget(self.lbl_sub)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.identifier)
            
    def set_active(self, is_active):
        if is_active: self.setStyleSheet(f"background-color: {self.active_bg}; border: none; border-radius: 10px; padding: 15px;")
        else: self.setStyleSheet(f"background-color: {self.inactive_bg}; border: none; border-radius: 10px; padding: 15px;")
            
    def update_data(self, value, sub_text):
        self.lbl_value.setText(str(value))
        self.lbl_sub.setText(sub_text)
        
        if "0.0%" in sub_text:
            self.lbl_sub.setStyleSheet("color: #E0F2FE; font-size: 11px; font-weight: bold; background: transparent; border: none;") 
        elif "↑" in sub_text or "+" in sub_text:
            self.lbl_sub.setStyleSheet("color: #4ADE80; font-size: 11px; font-weight: bold; background: transparent; border: none;") 
        elif "↓" in sub_text or "-" in sub_text:
            self.lbl_sub.setStyleSheet("color: #F87171; font-size: 11px; font-weight: bold; background: transparent; border: none;") 
        else:
            self.lbl_sub.setStyleSheet("color: #E0F2FE; font-size: 11px; font-weight: bold; background: transparent; border: none;")

class PieChartWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(180, 180)
        self.data = {}
        self.colors = ["#8B5CF6", "#3B82F6", "#F59E0B", "#10B981", "#EF4444", "#6366F1", "#EC4899", "#14B8A6", "#F97316", "#06B6D4", "#84CC16", "#A855F7"]

    def set_data(self, data):
        sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)
        self.data = dict(sorted_data)
        self.update()

    def paintEvent(self, event):
        if not self.data: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        total = sum(self.data.values())
        if total == 0: return
        rect = QRectF(10, 10, self.width() - 20, self.height() - 20)
        start_angle = 0
        for i, (role, count) in enumerate(self.data.items()):
            span_angle = (count / total) * 360 * 16
            painter.setBrush(QColor(self.colors[i % len(self.colors)]))
            painter.setPen(Qt.NoPen)
            painter.drawPie(rect, int(start_angle), int(span_angle))
            start_angle += span_angle
        painter.setBrush(QColor("white"))
        inner_rect = QRectF(50, 50, self.width() - 100, self.height() - 100)
        painter.drawEllipse(inner_rect)

class LineChartWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 180)
        self.data = []
        
    def set_data(self, data):
        self.data = data
        self.update()
        
    def paintEvent(self, event):
        if not self.data: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        margin_left = 35
        margin_bottom = 25
        margin_top = 15
        margin_right = 25
        
        w = self.width() - margin_left - margin_right
        h = self.height() - margin_top - margin_bottom
        
        axis_pen = QPen(QColor("#9CA3AF"), 2)
        painter.setPen(axis_pen)
        painter.drawLine(margin_left, margin_top, margin_left, margin_top + h) 
        painter.drawLine(margin_left, margin_top + h, margin_left + w, margin_top + h) 
        
        max_val = max(self.data) if self.data and max(self.data) > 0 else 1
        
        painter.setFont(QFont("Arial", 8, QFont.Bold))
        painter.setPen(QColor("#6B7280"))
        for i in range(4):
            val = int(max_val * i / 3)
            y = margin_top + h - (val / max_val) * h
            painter.drawText(0, int(y) - 10, margin_left - 5, 20, Qt.AlignRight | Qt.AlignVCenter, str(val))
            if i > 0:
                painter.setPen(QPen(QColor("#E5E7EB"), 1, Qt.DashLine))
                painter.drawLine(margin_left, int(y), margin_left + w, int(y))
                painter.setPen(QColor("#6B7280"))
        
        now = datetime.now()
        dates = [
            (now - timedelta(days=21)).strftime("%d/%m/%Y"), 
            (now - timedelta(days=14)).strftime("%d/%m/%Y"), 
            (now - timedelta(days=7)).strftime("%d/%m/%Y"), 
            now.strftime("%d/%m/%Y")
        ]
        
        points = []
        for i, val in enumerate(self.data):
            x = margin_left + int(i * (w / max(1, len(self.data) - 1)))
            y = margin_top + int(h - (val / max_val) * h)
            points.append((x, y))
            date_str = dates[i] if i < len(dates) else ""
            painter.drawText(int(x - 40), int(margin_top + h + 5), 80, 20, Qt.AlignCenter, date_str)
            
        if points:
            path = QPainterPath()
            path.moveTo(points[0][0], points[0][1])
            for x, y in points[1:]: path.lineTo(x, y)
            pen = QPen(QColor("#8B5CF6"), 3)
            painter.setPen(pen)
            painter.drawPath(path)
            
            painter.setBrush(QColor("white"))
            painter.setPen(QPen(QColor("#8B5CF6"), 2))
            for x, y in points:
                painter.drawEllipse(int(x) - 4, int(y) - 4, 8, 8)

class DashboardUI(QWidget):
    go_to_chat_signal = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #F3F4F6;")
        self.dashboard_data = {}
        self.current_tab = "MEMBERS"
        self.member_popup = MemberPopup(self)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)
        
        cards_layout = QHBoxLayout()
        self.member_card = ClickableCard(t('MEMBERS'), "0", "#3B82F6", "#3B82F6", "MEMBERS")  
        self.admin_card = ClickableCard(t('ADMIN'), "0", "#3B82F6", "#3B82F6", "ADMIN")  
        self.staff_card = ClickableCard(t('STAFF'), "0", "#3B82F6", "#3B82F6", "STAFF")       
        self.channel_card = ClickableCard(t('CHANNELS'), "0", "#3B82F6", "#3B82F6", "CHANNELS")       
        
        self.member_card.set_active(True)
        self.member_card.clicked.connect(self.switch_tab)
        self.admin_card.clicked.connect(self.switch_tab)
        self.staff_card.clicked.connect(self.switch_tab)
        self.channel_card.clicked.connect(self.switch_tab)
        
        cards_layout.addWidget(self.member_card)
        cards_layout.addWidget(self.admin_card)
        cards_layout.addWidget(self.staff_card)
        cards_layout.addWidget(self.channel_card)
        self.layout.addLayout(cards_layout)
        
        charts_layout = QHBoxLayout()
        line_frame = QFrame()
        line_frame.setStyleSheet("background-color: white; border-radius: 10px;")
        line_vbox = QVBoxLayout(line_frame)
        self.line_chart = LineChartWidget()
        line_vbox.addWidget(self.line_chart)
        
        pie_frame = QFrame()
        pie_frame.setStyleSheet("background-color: white; border-radius: 10px;")
        pie_vbox = QVBoxLayout(pie_frame)
        pie_title = QLabel(t('ROLE_STATS'))
        pie_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        pie_vbox.addWidget(pie_title)
        
        self.pie_chart = PieChartWidget()
        pie_hbox = QHBoxLayout()
        pie_hbox.addWidget(self.pie_chart)
        
        legend_scroll = QScrollArea()
        legend_scroll.setWidgetResizable(True)
        legend_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff) 
        legend_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        legend_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        def make_wheel_event_legend(s):
            def wheel_event(event):
                s.verticalScrollBar().setValue(s.verticalScrollBar().value() - event.angleDelta().y())
                event.accept() 
            return wheel_event
        legend_scroll.wheelEvent = make_wheel_event_legend(legend_scroll)
        
        legend_container = QWidget()
        legend_container.setStyleSheet("background: transparent;")
        self.pie_legend = QVBoxLayout(legend_container)
        self.pie_legend.setAlignment(Qt.AlignTop)
        
        legend_scroll.setWidget(legend_container)
        pie_hbox.addWidget(legend_scroll)
        pie_vbox.addLayout(pie_hbox)
        
        charts_layout.addWidget(line_frame, stretch=2)
        charts_layout.addWidget(pie_frame, stretch=1)
        self.layout.addLayout(charts_layout)
        
        self.table_container = QFrame()
        self.table_container.setStyleSheet("background-color: white; border-radius: 10px;")
        table_layout = QVBoxLayout(self.table_container)
        
        header_layout = QHBoxLayout()
        
        self.staff_filter_container = QWidget()
        staff_filter_layout = QHBoxLayout(self.staff_filter_container)
        staff_filter_layout.setContentsMargins(0, 0, 0, 0)
        staff_filter_layout.setSpacing(10)
        
        self.btn_staff_all = QPushButton("Tất cả")
        self.btn_staff_princess = QPushButton("Công chúa")
        self.btn_staff_prince = QPushButton("Hoàng tử")
        
        for btn in [self.btn_staff_all, self.btn_staff_princess, self.btn_staff_prince]:
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton { border: none; padding: 6px 15px; background: #F3F4F6; color: #6B7280; font-size: 12px; font-weight: bold; border-radius: 15px;}
                QPushButton:checked { background: #1A73E8; color: white; }
            """)
            staff_filter_layout.addWidget(btn)
            
        self.btn_staff_all.setChecked(True)
        self.btn_staff_all.clicked.connect(lambda: self.on_staff_filter_clicked("all"))
        self.btn_staff_princess.clicked.connect(lambda: self.on_staff_filter_clicked("princess"))
        self.btn_staff_prince.clicked.connect(lambda: self.on_staff_filter_clicked("prince"))
        self.staff_filter_container.hide()
        
        header_layout.addWidget(self.staff_filter_container)
        header_layout.addStretch()
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(t('SEARCH_ID'))
        self.search_bar.setFixedWidth(200)
        self.search_bar.setFocusPolicy(Qt.ClickFocus)
        self.search_bar.setStyleSheet("padding: 6px; border: 1px solid #D1D5DB; border-radius: 6px; font-size: 12px;")
        self.search_bar.textChanged.connect(self.apply_filters)
        
        self.role_filter = QComboBox()
        self.role_filter.setFixedWidth(200)
        self.role_filter.setFocusPolicy(Qt.ClickFocus)
        self.role_filter.setStyleSheet("""
            QComboBox { padding: 6px; border: 1px solid #D1D5DB; border-radius: 6px; font-size: 12px; background-color: white; color: black; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background-color: white; color: black; selection-background-color: white; selection-color: black; outline: none; border: 1px solid #D1D5DB; }
            QComboBox QAbstractItemView::item:hover { background-color: white; color: black; }
        """)
        self.role_filter.addItem(t('ALL_ROLES'))
        self.role_filter.currentTextChanged.connect(self.apply_filters)
        
        header_layout.addWidget(self.search_bar)
        header_layout.addWidget(self.role_filter)
        table_layout.addLayout(header_layout)

        self.tables_stack = QStackedWidget()

        self.normal_table = QTableWidget()
        self.setup_table_css(self.normal_table)
        self.tables_stack.addWidget(self.normal_table)

        table_layout.addWidget(self.tables_stack)
        self.layout.addWidget(self.table_container, stretch=1)

    def mousePressEvent(self, event):
        focus_widget = QApplication.focusWidget()
        if focus_widget:
            focus_widget.clearFocus()
        super().mousePressEvent(event)

    def on_staff_filter_clicked(self, filter_type):
        self.btn_staff_all.setChecked(filter_type == "all")
        self.btn_staff_princess.setChecked(filter_type == "princess")
        self.btn_staff_prince.setChecked(filter_type == "prince")
        self.apply_filters()

    def setup_table_css(self, table):
        table.setSelectionMode(QTableWidget.NoSelection) 
        table.setFocusPolicy(Qt.NoFocus)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        
        table.cellPressed.connect(self.on_table_cell_pressed)

        table.setStyleSheet("""
            QTableWidget { border: none; background-color: white; font-size: 13px; color: #374151; gridline-color: #E5E7EB; outline: none; }
            QHeaderView::section { background-color: #F9FAFB; color: #6B7280; font-weight: bold; padding: 12px; border: none; border-bottom: 1px solid #E5E7EB; text-align: left; }
            QTableWidget::item { padding: 5px 10px; border-bottom: 1px solid #F3F4F6; }
            QTableWidget::item:hover { background-color: transparent; }
            QTableWidget::item:selected { background-color: transparent; color: #374151; }
        """)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self.show_context_menu)

    def on_table_cell_pressed(self, row, col):
        if self.current_tab != "CHANNELS" or col != 2: return
        sender_table = self.sender()
        item = sender_table.item(row, col)
        if item:
            members_str = item.data(Qt.UserRole)
            if members_str:
                names = members_str.split("\n")
                rect = sender_table.visualRect(sender_table.model().index(row, col))
                pos = sender_table.viewport().mapToGlobal(rect.bottomLeft())
                pos.setY(pos.y() + 2)
                QTimer.singleShot(10, lambda: self.member_popup.show_data(names, pos))

    def switch_tab(self, tab_name):
        self.current_tab = tab_name
        self.member_card.set_active(tab_name == "MEMBERS")
        self.admin_card.set_active(tab_name == "ADMIN")
        self.staff_card.set_active(tab_name == "STAFF")
        self.channel_card.set_active(tab_name == "CHANNELS")
        
        if tab_name == "STAFF":
            self.staff_filter_container.show()
            self.role_filter.hide()
            
            headers = get_dashboard_headers_member().copy() 
            if "LOẠI" not in headers:
                headers.insert(-1, "LOẠI")
            
            self.normal_table.setColumnCount(len(headers))
            self.normal_table.setHorizontalHeaderLabels(headers)
            h = self.normal_table.horizontalHeader()
            h.setSectionResizeMode(0, QHeaderView.Stretch)
            h.setSectionResizeMode(1, QHeaderView.Stretch)
            h.setSectionResizeMode(2, QHeaderView.Stretch)
            h.setSectionResizeMode(3, QHeaderView.Stretch)
            h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
            h.setSectionResizeMode(5, QHeaderView.ResizeToContents)
            
        elif tab_name == "CHANNELS":
            self.staff_filter_container.hide()
            self.role_filter.hide()
            
            self.normal_table.setColumnCount(3)
            self.normal_table.setHorizontalHeaderLabels(get_dashboard_headers_channel())
            h = self.normal_table.horizontalHeader()
            h.setSectionResizeMode(0, QHeaderView.Stretch)
            h.setSectionResizeMode(1, QHeaderView.Stretch)
            h.setSectionResizeMode(2, QHeaderView.Stretch)
            
        else:
            self.staff_filter_container.hide()
            self.role_filter.show()
            
            headers_mem = get_dashboard_headers_member().copy()
            if "LOẠI" in headers_mem:
                headers_mem.remove("LOẠI")
                
            self.normal_table.setColumnCount(len(headers_mem))
            self.normal_table.setHorizontalHeaderLabels(headers_mem)
            h = self.normal_table.horizontalHeader()
            h.setSectionResizeMode(0, QHeaderView.Stretch)
            h.setSectionResizeMode(1, QHeaderView.Stretch)
            h.setSectionResizeMode(2, QHeaderView.Stretch)
            h.setSectionResizeMode(3, QHeaderView.Stretch)
            h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
            
        self.apply_filters()

    def update_members(self, data_dict):
        data_str = str(data_dict)
        if getattr(self, "last_data_str", None) == data_str:
            return
        self.last_data_str = data_str

        self.dashboard_data = data_dict
        stats = data_dict.get('stats_pct', {})
        self.member_card.update_data(len(data_dict.get('members', [])), stats.get('members', ''))
        self.admin_card.update_data(len(data_dict.get('admins', [])), stats.get('admins', ''))
        staff_total = len(data_dict.get('staff_princess', [])) + len(data_dict.get('staff_prince', []))
        self.staff_card.update_data(staff_total, stats.get('staff', ''))
        self.channel_card.update_data(len(data_dict.get('channels', [])), stats.get('channels', ''))
        self.line_chart.set_data(data_dict.get('joins', []))
        
        role_counts = data_dict.get('roles', {})
        self.pie_chart.set_data(role_counts)
        for i in reversed(range(self.pie_legend.count())): 
            self.pie_legend.itemAt(i).widget().setParent(None)
            
        for i, (role, count) in enumerate(self.pie_chart.data.items()):
            lbl = QLabel(f"● {role}: {count}".replace("&", "&&"))
            lbl.setTextFormat(Qt.PlainText) 
            lbl.setStyleSheet(f"color: {self.pie_chart.colors[i % len(self.pie_chart.colors)]}; font-weight: bold; font-size: 12px;")
            self.pie_legend.addWidget(lbl)

        self.role_filter.blockSignals(True)
        self.role_filter.clear()
        self.role_filter.addItem(t('ALL_ROLES'))
        for r in role_counts.keys():
            self.role_filter.addItem(r.replace("&", "&&"))
        self.role_filter.blockSignals(False)
        self.apply_filters()

    def populate_table(self, table, data_list, mode="members"):
        v_scroll = table.verticalScrollBar().value()
        table.setUpdatesEnabled(False)
        
        table.clearContents()
        
        table.setRowCount(len(data_list))
        
        for row, item in enumerate(data_list):
            if mode == "channels":
                i_name = QTableWidgetItem(item.get('name', ''))
                i_id = QTableWidgetItem(item.get('id', ''))
                i_count = QTableWidgetItem(item.get('count', ''))
                members_list = item.get('members_list', '')
                if members_list: i_count.setData(Qt.UserRole, members_list)
                i_id.setTextAlignment(Qt.AlignCenter)
                i_count.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 0, i_name)
                table.setItem(row, 1, i_id)
                table.setItem(row, 2, i_count)
                
            elif mode == "staff":
                i_name = QTableWidgetItem(item.get('name', ''))
                i_user = QTableWidgetItem(item.get('user', ''))
                i_id = QTableWidgetItem(item.get('id', ''))
                i_roles = QTableWidgetItem(item.get('roles', ''))
                
                type_str = item.get('type', '')
                type_color = "#EC4899" if type_str == "Công chúa" else "#3B82F6"
                i_type = QTableWidgetItem(type_str)
                i_type.setForeground(QColor(type_color))
                
                i_id.setTextAlignment(Qt.AlignCenter)
                i_type.setTextAlignment(Qt.AlignCenter)
                
                table.setItem(row, 0, i_name)
                table.setItem(row, 1, i_user)
                table.setItem(row, 2, i_id)
                table.setItem(row, 3, i_roles)
                table.setItem(row, 4, i_type)
                
                status = item.get('activity', 'offline')
                if status == 'online': color = "#2ECC71"
                elif status == 'idle': color = "#F1C40F"
                elif status == 'dnd': color = "#E74C3C"
                else: color = "#95A5A6"
                
                lbl_icon = QLabel()
                lbl_icon.setFixedSize(12, 12)
                lbl_icon.setStyleSheet(f"background-color: {color}; border-radius: 6px;")
                widget_container = QWidget()
                lay = QHBoxLayout(widget_container)
                lay.setContentsMargins(0, 0, 0, 0)
                lay.setAlignment(Qt.AlignCenter)
                lay.addWidget(lbl_icon)
                table.setCellWidget(row, 5, widget_container)
                
            else:
                i_name = QTableWidgetItem(item.get('name', ''))
                i_user = QTableWidgetItem(item.get('user', ''))
                i_id = QTableWidgetItem(item.get('id', ''))
                i_roles = QTableWidgetItem(item.get('roles', ''))
                i_id.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 0, i_name)
                table.setItem(row, 1, i_user)
                table.setItem(row, 2, i_id)
                table.setItem(row, 3, i_roles)
                
                status = item.get('activity', 'offline')
                if status == 'online': color = "#2ECC71"
                elif status == 'idle': color = "#F1C40F"
                elif status == 'dnd': color = "#E74C3C"
                else: color = "#95A5A6"
                
                lbl_icon = QLabel()
                lbl_icon.setFixedSize(12, 12)
                lbl_icon.setStyleSheet(f"background-color: {color}; border-radius: 6px;")
                widget_container = QWidget()
                lay = QHBoxLayout(widget_container)
                lay.setContentsMargins(0, 0, 0, 0)
                lay.setAlignment(Qt.AlignCenter)
                lay.addWidget(lbl_icon)
                table.setCellWidget(row, 4, widget_container)
                
        table.setUpdatesEnabled(True)
        table.verticalScrollBar().setValue(v_scroll)

    def apply_filters(self):
        if not self.dashboard_data: return
        search_id = self.search_bar.text().strip().lower()
        selected_role = self.role_filter.currentText().replace("&&", "&") 
        
        if self.current_tab == "STAFF":
            f_princess = []
            for m in self.dashboard_data.get('staff_princess', []):
                if search_id and search_id not in m.get('id', '').lower(): continue
                m_copy = m.copy()
                m_copy['type'] = "Công chúa"
                f_princess.append(m_copy)
                
            f_prince = []
            for m in self.dashboard_data.get('staff_prince', []):
                if search_id and search_id not in m.get('id', '').lower(): continue
                m_copy = m.copy()
                m_copy['type'] = "Hoàng tử"
                f_prince.append(m_copy)
                
            combined = []
            
            if self.btn_staff_all.isChecked():
                combined = f_princess + f_prince
            elif self.btn_staff_princess.isChecked():
                combined = f_princess
            elif self.btn_staff_prince.isChecked():
                combined = f_prince
            else:
                self.btn_staff_all.setChecked(True)
                combined = f_princess + f_prince
            
            combined = sorted(combined, key=lambda x: x.get('name', '').lower())
            self.populate_table(self.normal_table, combined, "staff")
            
        else:
            if self.current_tab == "MEMBERS": source_list = self.dashboard_data.get('members', [])
            elif self.current_tab == "ADMIN": source_list = self.dashboard_data.get('admins', [])
            else: source_list = self.dashboard_data.get('channels', [])
                
            filtered = []
            for item in source_list:
                if search_id and search_id not in item.get('id', '').lower(): continue
                if self.current_tab != "CHANNELS" and selected_role != t('ALL_ROLES') and selected_role not in item.get('roles', ''): continue
                filtered.append(item)
                
            if self.current_tab != "CHANNELS":
                filtered = sorted(filtered, key=lambda x: x.get('name', '').lower())
                self.populate_table(self.normal_table, filtered, "members")
            else:
                self.populate_table(self.normal_table, filtered, "channels")

    def show_context_menu(self, pos):
        sender_table = self.sender() 
        item = sender_table.itemAt(pos)
        if item:
            row = item.row()
            if self.current_tab == "CHANNELS":
                user_id = sender_table.item(row, 1).text()
                user_name = f"#{sender_table.item(row, 0).text()}"
            elif self.current_tab == "STAFF":
                user_id = sender_table.item(row, 2).text()
                user_name = sender_table.item(row, 0).text()
            else:
                user_id = sender_table.item(row, 2).text()
                user_name = sender_table.item(row, 0).text()

            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu { background-color: white; border: 1px solid #D1D5DB; border-radius: 5px; } 
                QMenu::item { padding: 10px 25px 10px 15px; font-size: 13px; font-weight: bold; color: #374151;} 
                QMenu::item:selected { background-color: #E8F0FE; color: #1A73E8; }
            """)
            msg_action = menu.addAction("Nhắn tin")
            action = menu.exec_(sender_table.viewport().mapToGlobal(pos))
            if action == msg_action:
                self.go_to_chat_signal.emit(user_id, user_name)