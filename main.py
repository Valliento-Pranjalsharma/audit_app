import sys
import os
import mysql.connector
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QFrame, QTableWidget, QTableWidgetItem, QLineEdit,
    QSizePolicy, QMessageBox, QSplitter, QWidget, QStyle, QToolButton, QHeaderView,
    QComboBox, QDateEdit, QFileDialog
)
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import Qt, QSize, QDate
from PyQt5.QtGui import QPixmap, QIcon, QTextDocument
from PyQt5.QtPrintSupport import QPrinter

def get_transaction_data():
    """
    Connects to the MySQL database, fetches all data from audit_table,
    and returns it as a list of tuples.
    Returns an empty list and prints an error if the connection fails.
    """
    try:
        mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Pranjal@283203",
            database="audit_app_db"
        )
        mycursor = mydb.cursor()
        mycursor.execute("SELECT * FROM audit_table")
        results = mycursor.fetchall()
        mycursor.close()
        mydb.close()
        return results        
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return []

# Fetch data from the database initially
transaction_data = get_transaction_data()

class AuditApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audit App with Embedded Windows Media Player")
        self.setGeometry(150, 80, 1600, 900)
        self.current_video_path = None
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.main_splitter)

        self.create_left_panel()
        self.create_center_panel()
        self.create_right_panel()
        self.populate_filter_comboboxes()

    def create_left_panel(self):
        self.left_panel = QFrame()
        self.left_panel.setStyleSheet("background-color: #232629;")
        self.left_panel.setMinimumWidth(350)
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(12, 12, 12, 12)
        self.left_layout.setSpacing(15)

        self.filters_frame = QFrame()
        self.filters_layout = QVBoxLayout(self.filters_frame)
        self.filters_layout.setSpacing(10)
        
        filter_labels_and_db_columns = {
            "Lane:": 12, "Shift:": 13, "User:": 14, "Vehicle Class:": 7,
            "Exempt Class:": 15, "Payment Mode:": 6, "Pass Type:": 16,
        }
        self.filter_comboboxes = {}
        for label, _ in filter_labels_and_db_columns.items():
            lbl = QLabel(label)
            lbl.setStyleSheet("color: white; font-weight: bold; font-size: 11pt;")
            combo = QComboBox()
            combo.setStyleSheet("background-color: #2e3237; color: white; border-radius: 3px; padding: 6px;")
            self.filters_layout.addWidget(lbl)
            self.filters_layout.addWidget(combo)
            self.filter_comboboxes[label] = combo

        date_filter_labels = ["Start Date:", "End Date:"]
        self.date_filters = {}
        for label in date_filter_labels:
            lbl = QLabel(label)
            lbl.setStyleSheet("color: white; font-weight: bold; font-size: 11pt;")
            date_edit = QDateEdit()
            date_edit.setCalendarPopup(True)
            date_edit.setStyleSheet("background-color: #2e3237; color: white; border-radius: 3px; padding: 6px;")
            date_edit.setDate(QDate.currentDate())
            self.filters_layout.addWidget(lbl)
            self.filters_layout.addWidget(date_edit)
            self.date_filters[label] = date_edit
            
        self.left_layout.addWidget(self.filters_frame)
        
        btn_frame = QHBoxLayout()
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet(
            "background-color: #303841; color: white; padding: 8px; font-weight: bold; border-radius: 5px;"
        )
        refresh_btn.clicked.connect(self.refresh_table)
        # Done button
        done_btn = QPushButton("Done")
        done_btn.setStyleSheet(
            "background-color: #218c54; color: white; padding: 8px; font-weight: bold; border-radius: 5px;"
        )
        done_btn.clicked.connect(self.done_button_logic)
        btn_frame.addWidget(refresh_btn)
        btn_frame.addWidget(done_btn)
        self.left_layout.addLayout(btn_frame)

        video_label = QLabel("Video Player")
        video_label.setStyleSheet("color: white; font-size: 16pt; font-weight: bold; margin-top: 20px;")
        self.left_layout.addWidget(video_label)

        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: black; border-radius: 6px;")
        self.video_frame.setFixedSize(400, 225)
        self.video_layout = QVBoxLayout(self.video_frame)
        self.video_layout.setContentsMargins(0, 0, 0, 0)

        self.player = QAxWidget("WMPlayer.OCX")
        self.player.setProperty("uiMode", "full")
        self.player.setProperty("stretchToFit", True)
        self.player.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_layout.addWidget(self.player)
        self.left_layout.addWidget(self.video_frame, alignment=Qt.AlignHCenter)
        self.main_splitter.addWidget(self.left_panel)

    def done_button_logic(self):
        """
        This function will get called when 'Done' is clicked.
        Customize the logic as needed.
        """
        filled_filters = {k: v.currentText() for k, v in self.filter_comboboxes.items() if v.currentText()}
        comment = self.comment_edit.text() if hasattr(self, "comment_edit") else ""
        QMessageBox.information(self, "Done", f"Filters: {filled_filters}\nComment: {comment}\n\n(Implement your logic here)")

    def create_center_panel(self):
        self.center_panel = QFrame()
        self.center_panel.setStyleSheet("background-color: white; border-radius: 8px;")
        self.center_layout = QVBoxLayout(self.center_panel)
        self.center_layout.setContentsMargins(12, 12, 12, 12)
        self.center_layout.setSpacing(12)

        header_panel = QFrame()
        header_panel.setStyleSheet("background-color: #f0f0f0; border-radius: 5px; padding: 10px;")
        header_layout = QHBoxLayout(header_panel)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(15)

        tran_id_label = QLabel("Tran Id:")
        tran_id_label.setStyleSheet("color: #333; font-weight: bold; font-size: 14px;")
        self.tran_id_input = QLineEdit()
        self.tran_id_input.setPlaceholderText("Enter Tran Id")
        self.tran_id_input.setFixedWidth(120)
        self.tran_id_input.setStyleSheet("background-color: white; color: black; border: 1px solid #ccc; border-radius: 3px; padding: 5px;")

        veh_reg_label = QLabel("Veh Reg No:")
        veh_reg_label.setStyleSheet("color: #333; font-weight: bold; font-size: 14px;")
        self.veh_reg_input = QLineEdit()
        self.veh_reg_input.setPlaceholderText("Enter Vehicle No")
        self.veh_reg_input.setFixedWidth(120)
        self.veh_reg_input.setStyleSheet("background-color: white; color: black; border: 1px solid #ccc; border-radius: 3px; padding: 5px;")

        get_btn = QPushButton("Get")
        get_btn.setFixedWidth(60)
        get_btn.setStyleSheet("background-color: #007bff; color: white; padding: 6px 12px; border-radius: 5px; font-weight: bold;")
        get_btn.clicked.connect(self.apply_filters)

        export_pdf_btn = QPushButton("Export as PDF")
        export_pdf_btn.setFixedWidth(110)
        export_pdf_btn.setStyleSheet("background-color: #28a745; color: white; padding: 6px 12px; border-radius: 5px; font-weight: bold;")
        # Set icon for Export as PDF button (built-in file save icon used as example)
        export_pdf_icon = self.style().standardIcon(QStyle.SP_DialogSaveButton)
        export_pdf_btn.setIcon(export_pdf_icon)
        export_pdf_btn.setIconSize(QSize(16,16))
        export_pdf_btn.clicked.connect(self.export_pdf)

        excel_btn = QToolButton()
        excel_btn.setIcon(self.style().standardIcon(QStyle.SP_DriveHDIcon))
        excel_btn.setIconSize(QSize(24, 24))
        excel_btn.setToolTip("Export to Excel")
        excel_btn.setStyleSheet("background-color: #ffc107; border-radius: 5px; padding: 5px;")
        # You can implement Excel export later and connect excel_btn.clicked

        header_layout.addWidget(tran_id_label)
        header_layout.addWidget(self.tran_id_input)
        header_layout.addWidget(veh_reg_label)
        header_layout.addWidget(self.veh_reg_input)
        header_layout.addWidget(get_btn)
        header_layout.addWidget(export_pdf_btn)
        header_layout.addWidget(excel_btn)
        header_layout.addStretch()

        self.center_layout.addWidget(header_panel)

        self.table = QTableWidget()
        self.table.setRowCount(len(transaction_data))
        self.table.setColumnCount(14)
        headers = [
            "Time", "TC Class", "AVC", "Amount", "VehRegNo", "Payment Mode",
            "Vehicle Class", "Booth", "Camera", "Title", "Duration",
            "LP Image Path", "All Image Path", "Video Path"
        ]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)

        header = self.table.horizontalHeader()
        for col in range(self.table.columnCount() - 1):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.table.columnCount() - 1, QHeaderView.Stretch)

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                color: #333;
                gridline-color: #e0e0e0;
                font-size: 11pt;
                font-family: 'Segoe UI', Arial, sans-serif;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: #f8f8f8;
                color: #333;
                padding: 8px;
                border: 1px solid #e0e0e0;
                font-weight: bold;
                font-size: 10pt;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #cceeff;
                color: #333;
            }
            QTableWidget::item:hover {
                background-color: #e6f7ff;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
            }
            QScrollBar:horizontal {
                border: none;
                background: #f0f0f0;
                height: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:horizontal {
                background: #c0c0c0;
                min-width: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                border: none;
            }
        """)

        self.table.cellClicked.connect(self.on_table_row_selected)
        self.populate_transaction_table(transaction_data)
        self.center_layout.addWidget(self.table)

        self.images_frame = QFrame()
        self.images_frame.setStyleSheet("background-color: #f0f0f0; border-radius: 5px; padding: 10px;")
        images_layout = QHBoxLayout(self.images_frame)
        images_layout.setContentsMargins(0, 0, 0, 0)
        images_layout.setSpacing(15)

        self.lp_image_label = QLabel("LP Image")
        self.lp_image_label.setStyleSheet(
            "background-color: white; color: #555; font-size: 12pt; border-radius: 6px; border: 1px dashed #ccc;"
        )
        self.lp_image_label.setFixedSize(320, 180)
        self.lp_image_label.setAlignment(Qt.AlignCenter)
        self.lp_image_label.setScaledContents(True)
        images_layout.addWidget(self.lp_image_label)

        self.all_image_label = QLabel("All Images")
        self.all_image_label.setStyleSheet(
            "background-color: white; color: #555; font-size: 12pt; border-radius: 6px; border: 1px dashed #ccc;"
        )
        self.all_image_label.setFixedSize(320, 180)
        self.all_image_label.setAlignment(Qt.AlignCenter)
        self.all_image_label.setScaledContents(True)
        images_layout.addWidget(self.all_image_label)

        images_layout.addStretch()
        self.center_layout.addWidget(self.images_frame)
        self.main_splitter.addWidget(self.center_panel)

    def create_right_panel(self):
        self.right_panel = QFrame()
        self.right_panel.setStyleSheet("background-color: #383838; border-radius: 8px;")
        self.right_panel.setMinimumWidth(320)
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(12, 12, 12, 12)
        self.right_layout.setSpacing(15)

        self.info_box = QLabel("Select a transaction to see details")
        self.info_box.setStyleSheet(
            "background-color: white; padding: 12px; font-size: 12pt; border-radius: 6px; color: #333;")
        self.info_box.setWordWrap(True)
        self.info_box.setMinimumHeight(280)
        self.right_layout.addWidget(self.info_box)

        comment_lbl = QLabel("Audit Comment:")
        comment_lbl.setStyleSheet("color: white; font-weight: bold; font-size: 11pt;")
        self.right_layout.addWidget(comment_lbl)

        self.comment_edit = QLineEdit()
        self.comment_edit.setStyleSheet(
            "background-color: #505050; color: white; padding: 8px; border-radius: 5px;")
        self.right_layout.addWidget(self.comment_edit)

        audit_buttons = [
            "Edit Transaction", "Cancel Transaction", "ETC Audit",
            "IAVC Audit", "Operator Correct", "AVC Correct", "Auditor Correct"
        ]
        btn_style = """
            QPushButton {
            background-color: #505050;
            color: white;
            padding: 10px;
            font-weight: bold;
            border-radius: 6px;
            margin-top: 7px;
                        }
            QPushButton:hover {
            background-color: #686868;
                        }
                    """

        for txt in audit_buttons:
            btn = QPushButton(txt)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(lambda checked, t=txt: self.audit_button_clicked(t))
            self.right_layout.addWidget(btn)

        self.right_layout.addStretch()
        self.main_splitter.addWidget(self.right_panel)

    def populate_filter_comboboxes(self):
        filter_map = {
            "Lane:": 12, "Shift:": 13, "User:": 14, "Vehicle Class:": 7,
            "Exempt Class:": 15, "Payment Mode:": 6, "Pass Type:": 16,
        }

        for combo in self.filter_comboboxes.values():
            combo.clear()
            combo.addItem("") 

        for label, col_index in filter_map.items():
            if col_index < len(transaction_data[0]) if transaction_data else False:
                unique_values = sorted(list(set(str(txn[col_index]).strip() for txn in transaction_data)))
                self.filter_comboboxes[label].addItems(unique_values)

    def populate_transaction_table(self, data):
        self.table.setRowCount(0)
        if not data:
            return
        
        self.table.setRowCount(len(data))
        
        for row_idx, txn in enumerate(data):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(txn[1]))) # Time
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(txn[2]))) # TC Class
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(txn[3]))) # AVC
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(txn[4]))) # Amount
            self.table.setItem(row_idx, 4, QTableWidgetItem(str(txn[5]))) # VehRegNo
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(txn[6]))) # Payment Mode
            self.table.setItem(row_idx, 6, QTableWidgetItem(str(txn[7]))) # Vehicle Class
            self.table.setItem(row_idx, 7, QTableWidgetItem(str(txn[8]))) # Booth
            self.table.setItem(row_idx, 8, QTableWidgetItem(str(txn[9]))) # Camera
            self.table.setItem(row_idx, 9, QTableWidgetItem(str(txn[10]))) # Title
            self.table.setItem(row_idx, 10, QTableWidgetItem(str(txn[11]))) # Duration
            self.table.setItem(row_idx, 11, QTableWidgetItem(str(txn[21]))) # lp_image_path
            self.table.setItem(row_idx, 12, QTableWidgetItem(str(txn[22]))) # all_image_path
            self.table.setItem(row_idx, 13, QTableWidgetItem(str(txn[23]))) # video_path

    def on_table_row_selected(self, row, column):
        global transaction_data
        if not transaction_data or row >= len(transaction_data):
            return

        txn = transaction_data[row]

        # Autofill top input fields
        self.tran_id_input.setText(str(txn[0]))
        self.veh_reg_input.setText(str(txn[5]))

        details = (
            f"<b>ID:</b> {txn[0]}<br>"
            f"<b>Title:</b> {txn[10]}<br>"
            f"<b>Timestamp:</b> {txn[1]}<br>"
            f"<b>Duration:</b> {txn[11]}<br>"
            f"<b>Booth:</b> {txn[8]}<br>"
            f"<b>Camera:</b> {txn[9]}<br>"
            f"<b>Vehicle No:</b> {txn[5]}"
        )
        self.info_box.setText(details)
        
        lp_image_path = str(txn[21])
        all_image_path = str(txn[22])
        video_path = str(txn[23])

        if os.path.exists(lp_image_path):
            pixmap = QPixmap(lp_image_path).scaled(self.lp_image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lp_image_label.setPixmap(pixmap)
        else:
            self.lp_image_label.setText("LP Image Not Found")
            self.lp_image_label.setPixmap(QPixmap())

        if os.path.exists(all_image_path):
            pixmap = QPixmap(all_image_path).scaled(self.all_image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.all_image_label.setPixmap(pixmap)
        else:
            self.all_image_label.setText("All Images Not Found")
            self.all_image_label.setPixmap(QPixmap())

        if os.path.exists(video_path):
            self.player.dynamicCall('URL', video_path)
            self.current_video_path = video_path
        else:
            QMessageBox.warning(self, "Video Not Found", f"Video not found:\n{video_path}")
            self.current_video_path = None

    def refresh_table(self):
        global transaction_data
        transaction_data = get_transaction_data()
        
        for combo in self.filter_comboboxes.values():
            combo.setCurrentIndex(0)
        self.tran_id_input.clear()
        self.veh_reg_input.clear()

        for date_edit in self.date_filters.values():
            date_edit.setDate(QDate.currentDate())

        self.populate_filter_comboboxes()
        self.populate_transaction_table(transaction_data)

        self.info_box.setText("Select a transaction to see details")
        self.lp_image_label.clear()
        self.lp_image_label.setText("LP Image")
        self.all_image_label.clear()
        self.all_image_label.setText("All Images")

        if self.current_video_path:
            self.player.dynamicCall('controls.stop')
        self.current_video_path = None

    def apply_filters(self):
        global transaction_data
        
        filters = {}
        
        for label, combo in self.filter_comboboxes.items():
            value = combo.currentText().strip()
            if value:
                filters[label.replace(":", "")] = value
                
        tran_id_filter = self.tran_id_input.text().strip()
        if tran_id_filter:
            filters['Tran Id'] = tran_id_filter

        veh_reg_no_filter = self.veh_reg_input.text().strip().upper()
        if veh_reg_no_filter:
            filters['Veh Reg No'] = veh_reg_no_filter
            
        start_date_filter = self.date_filters["Start Date:"].date().toString("yyyy-MM-dd")
        end_date_filter = self.date_filters["End Date:"].date().toString("yyyy-MM-dd")
        
        filter_map = {
            'Tran Id': 0,
            'Veh Reg No': 5,
            'Lane': 12,
            'Shift': 13,
            'User': 14,
            'Vehicle Class': 7,
            'Payment Mode': 6,
            'Pass Type': 16,
            'Exempt Class': 15,
        }

        if not filters and not start_date_filter and not end_date_filter:
            self.refresh_table()
            return

        filtered_data = []
        for txn in transaction_data:
            match = True
            
            for filter_name, filter_value in filters.items():
                col_index = filter_map.get(filter_name)
                if col_index is not None:
                    if filter_name in ['Tran Id', 'Veh Reg No']:
                        if filter_value.upper() not in str(txn[col_index]).strip().upper():
                            match = False
                            break
                    else:
                        if str(txn[col_index]).strip().upper() != filter_value.upper():
                            match = False
                            break

            if match and start_date_filter and end_date_filter:
                transaction_date_str = str(txn[1]).split(" ")[0]
                if not (start_date_filter <= transaction_date_str <= end_date_filter):
                    match = False
            
            if match:
                filtered_data.append(txn)

        if not filtered_data:
            QMessageBox.information(self, "No Results", "No transactions matched your search criteria.")
            self.populate_transaction_table([])
        else:
            self.populate_transaction_table(filtered_data)

    def audit_button_clicked(self, action_name):
        QMessageBox.information(self, "Audit Action",
                                f"Button '{action_name}' clicked.\nImplement audit logic here.")

    def export_pdf(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export PDF", "", "PDF Files (*.pdf)")
        if not filename:
            return

        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(filename)
        printer.setPaperSize(QPrinter.A4)
        printer.setOrientation(QPrinter.Landscape)

        html = "<html><head><style>"
        html += "table, th, td { border: 1px solid black; border-collapse: collapse; padding:4px; }"
        html += "th { background-color: #f0f0f0; font-weight: bold; }"
        html += "</style></head><body><table>"
        # Headers
        html += "<tr>"
        for c in range(self.table.columnCount()):
            item = self.table.horizontalHeaderItem(c)
            html += "<th>{}</th>".format(item.text() if item else "")
        html += "</tr>"
        # Rows
        for r in range(self.table.rowCount()):
            html += "<tr>"
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                html += "<td>{}</td>".format(item.text() if item else "")
            html += "</tr>"
        html += "</table></body></html>"

        doc = QTextDocument()
        doc.setHtml(html)
        doc.setPageSize(printer.pageRect().size())
        doc.print_(printer)

        QMessageBox.information(self, "Exported", f"Table exported as PDF:\n{filename}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    audit_app = AuditApp()
    audit_app.show()
    sys.exit(app.exec_())
