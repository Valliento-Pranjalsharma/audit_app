import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QFrame, QTableWidget, QTableWidgetItem, QLineEdit,
    QSizePolicy, QMessageBox, QSplitter, QWidget, QStyle, QToolButton, QHeaderView,
    QScrollArea
)
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap


# --- Sample Transaction Data ---
# This list holds the data for the audit transactions.
# Each tuple represents a single transaction with various details.
# The structure is:
# (ID, Timestamp, TC Class, AVC, Amount/Duration, VehRegNo, Payment Mode,
#  Vehicle Class, Booth, Camera, Title, Video Path, LP Image Path, All Images Path)
transaction_data = [
    (1, "2024-07-19 11:20", "A1", "Audit Footage 12", "$00:25", "XYZ-123",
     "Cash", "Car", "A1", "001", "Audit Footage 12",
     r"C:\Users\ASUS\OneDrive\Desktop\audit_app\audit_app\videos\video12.mp4",
     r"C:\Users\ASUS\OneDrive\Desktop\audit_app\audit_app\thumbnails\thumb12.png",
     r"C:\Users\ASUS\OneDrive\Desktop\audit_app\audit_app\thumbnails\thumb12.png"),
    (2, "2024-07-19 11:10", "A1", "Audit Footage 13", "$00:30", "XYZ-124",
     "Card", "Truck", "A1", "002", "Audit Footage 13",
     r"C:\Users\ASUS\OneDrive\Desktop\audit_app\audit_app\videos\video13.mp4",
     r"C:\Users\ASUS\OneDrive\Desktop\audit_app\audit_app\thumbnails\thumb13.png",
     r"C:\Users\ASUS\OneDrive\Desktop\audit_app\audit_app\thumbnails\thumb13.png"),
    (3, "2024-07-19 11:00", "A2", "Audit Footage 14", "$00:35", "XYZ-125",
     "Pass", "Bike", "A2", "003", "Audit Footage 14",
     r"C:\Users\ASUS\OneDrive\Desktop\audit_app\audit_app\videos\video14.mp4",
     r"C:\Users\ASUS\OneDrive\Desktop\audit_app\audit_app\thumbnails\thumb14.png",
     r"C:\Users\ASUS\OneDrive\Desktop\audit_app\audit_app\thumbnails\thumb14.png"),
    (4, "2024-07-19 10:50", "A3", "Audit Footage 15", "$00:40", "XYZ-126",
     "Cash", "Car", "A3", "004", "Audit Footage 15",
     r"C:\Users\ASUS\OneDrive\Desktop\audit_app\audit_app\videos\video15.mp4",
     r"C:\Users\ASUS\OneDrive\Desktop\audit_app\audit_app\thumbnails\thumb15.png",
     r"C:\Users\ASUS\OneDrive\Desktop\audit_app\audit_app\thumbnails\thumb15.png"),
]

# Populate additional sample data for demonstration purposes
for i in range(5, 40):
    transaction_data.append((
        i,
        f"2024-07-19 10:{50 - (i % 60):02d}", # Timestamp
        f"A{i%5 + 1}", # TC Class
        f"Audit Footage {10 + i}", # AVC
        f"${20 + i}", # Amount / Duration (re-used for both in this example)
        f"XYZ-{100 + i}", # VehRegNo
        "Cash" if i % 3 == 0 else "Card", # Payment Mode
        ["Car", "Truck", "Bike", "Bus", "Van"][i % 5], # Vehicle Class
        f"A{i%5 + 1}", # Booth
        f"00{i:03d}", # Camera (original txn[9] is 001, 002 etc)
        f"Audit Footage {10 + i}", # Title (original txn[10] is Audit Footage)
        r"C:\Users\ASUS\OneDrive\Desktop\audit_app\audit_app\videos\video12.mp4", # Sample Video Path
        r"C:\Users\ASUS\OneDrive\Desktop\audit_app\audit_app\thumbnails\thumb12.png", # Sample LP Image Path
        r"C:\Users\ASUS\OneDrive\Desktop\audit_app\audit_app\thumbnails\thumb12.png" # Sample All Images Path
    ))


class AuditApp(QMainWindow):
    """
    Main application window for the Audit App.
    It provides a UI for viewing transaction data, playing associated videos,
    displaying images, and performing audit actions.
    """
    def __init__(self):
        """
        Initializes the AuditApp window, sets up the main layout,
        and calls methods to create the left, center, and right panels.
        """
        super().__init__()
        self.setWindowTitle("Audit App with Embedded Windows Media Player")
        self.setGeometry(150, 80, 1600, 900) # Set initial window position and size

        self.current_video_path = None # Stores the path of the currently playing video

        # Create a QSplitter to allow resizing of panels horizontally
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.main_splitter) # Set the splitter as the central widget

        # Call methods to create and add each panel to the splitter
        self.create_left_panel()
        self.create_center_panel()
        self.create_right_panel()

    def create_left_panel(self):
        """
        Creates the left panel of the application, containing filter inputs,
        Refresh/Done buttons, and an embedded Windows Media Player.
        """
        self.left_panel = QFrame()
        self.left_panel.setStyleSheet("background-color: #232629;") # Dark background
        self.left_panel.setMinimumWidth(350) # Set a minimum width for the panel
        self.left_layout = QVBoxLayout(self.left_panel) # Vertical layout for the left panel
        self.left_layout.setContentsMargins(12, 12, 12, 12) # Padding around content
        self.left_layout.setSpacing(15) # Spacing between widgets

        # --- Filter Section ---
        self.filters_frame = QFrame()
        self.filters_layout = QVBoxLayout(self.filters_frame)
        self.filters_layout.setSpacing(10)
        filter_labels = [
            "Lane:", "Shift:", "User:", "Vehicle Class:", "Exempt Class:",
            "Payment Mode:", "Pass Type:", "Tran Filter:", "Start Date:", "End Date:"
        ]
        self.filter_entries = {} # Dictionary to store QLineEdit widgets for filters
        for label in filter_labels:
            lbl = QLabel(label)
            lbl.setStyleSheet("color: white; font-weight: bold; font-size: 11pt;")
            edit = QLineEdit()
            edit.setStyleSheet("background-color: #2e3237; color: white; border-radius: 3px; padding: 6px;")
            self.filters_layout.addWidget(lbl)
            self.filters_layout.addWidget(edit)
            self.filter_entries[label] = edit # Store the QLineEdit for later access
        self.left_layout.addWidget(self.filters_frame)

        # --- Buttons Section (Refresh and Done) ---
        btn_frame = QHBoxLayout() # Horizontal layout for buttons
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet(
            "background-color: #303841; color: white; padding: 8px; font-weight: bold; border-radius: 5px;"
        )
        refresh_btn.clicked.connect(self.refresh_table) # Connect refresh button to method
        done_btn = QPushButton("Done")
        done_btn.setStyleSheet(
            "background-color: #218c54; color: white; padding: 8px; font-weight: bold; border-radius: 5px;"
        )
        btn_frame.addWidget(refresh_btn)
        btn_frame.addWidget(done_btn)
        self.left_layout.addLayout(btn_frame)

        # --- Video Player Section ---
        video_label = QLabel("Video Player")
        video_label.setStyleSheet("color: white; font-size: 16pt; font-weight: bold; margin-top: 20px;")
        self.left_layout.addWidget(video_label)

        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: black; border-radius: 6px;")
        self.video_frame.setFixedSize(400, 225) # Fixed size for the video player frame
        self.video_layout = QVBoxLayout(self.video_frame)
        self.video_layout.setContentsMargins(0, 0, 0, 0) # No padding for the video player

        # QAxWidget is used to embed ActiveX controls, specifically Windows Media Player (WMPlayer.OCX)
        self.player = QAxWidget("WMPlayer.OCX")
        self.player.setProperty("uiMode", "full") # Display full UI controls
        self.player.setProperty("stretchToFit", True) # Stretch video to fit control size
        self.player.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # Allow player to expand
        self.video_layout.addWidget(self.player)
        self.left_layout.addWidget(self.video_frame, alignment=Qt.AlignHCenter) # Center the video frame
        self.main_splitter.addWidget(self.left_panel) # Add the left panel to the main splitter

    def create_center_panel(self):
        """
        Creates the central panel of the application, which includes:
        - Input fields for Transaction ID and Vehicle Registration Number.
        - Buttons for Get, Export as PDF, and Export to Excel.
        - A QTableWidget to display transaction data.
        - Labels to display LP (License Plate) and All Images.
        """
        self.center_panel = QFrame()
        # Set white background for the main center panel for a clean look
        self.center_panel.setStyleSheet("background-color: white; border-radius: 8px;")
        self.center_layout = QVBoxLayout(self.center_panel) # Vertical layout for the center panel
        self.center_layout.setContentsMargins(12, 12, 12, 12) # Padding around content
        self.center_layout.setSpacing(12) # Spacing between widgets

        # --- Top Header Panel (Filter/Export Controls) ---
        header_panel = QFrame()
        header_panel.setStyleSheet("background-color: #f0f0f0; border-radius: 5px; padding: 10px;")
        header_layout = QHBoxLayout(header_panel) # Horizontal layout for header controls
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(15)

        # Transaction ID input
        tran_id_label = QLabel("Tran Id:")
        tran_id_label.setStyleSheet("color: #333; font-weight: bold; font-size: 14px;")
        self.tran_id_input = QLineEdit()
        self.tran_id_input.setPlaceholderText("Enter Tran Id")
        self.tran_id_input.setFixedWidth(120)
        self.tran_id_input.setStyleSheet("background-color: white; color: black; border: 1px solid #ccc; border-radius: 3px; padding: 5px;")

        # Vehicle Registration Number input
        veh_reg_label = QLabel("Veh Reg No:")
        veh_reg_label.setStyleSheet("color: #333; font-weight: bold; font-size: 14px;")
        self.veh_reg_input = QLineEdit()
        self.veh_reg_input.setPlaceholderText("Enter Vehicle No")
        self.veh_reg_input.setFixedWidth(120)
        self.veh_reg_input.setStyleSheet("background-color: white; color: black; border: 1px solid #ccc; border-radius: 3px; padding: 5px;")

        # Get Button
        get_btn = QPushButton("Get")
        get_btn.setFixedWidth(60)
        get_btn.setStyleSheet("background-color: #007bff; color: white; padding: 6px 12px; border-radius: 5px; font-weight: bold;")
        get_btn.clicked.connect(self.apply_filters) # Connect to the filter application method

        # Export as PDF Button
        export_pdf_btn = QPushButton("Export as PDF")
        export_pdf_btn.setFixedWidth(100)
        export_pdf_btn.setStyleSheet("background-color: #28a745; color: white; padding: 6px 12px; border-radius: 5px; font-weight: bold;")
        # TODO: Add PDF export logic here when implemented

        # Export to Excel Button (QToolButton for icon)
        excel_btn = QToolButton()
        excel_btn.setIcon(self.style().standardIcon(QStyle.SP_DriveHDIcon)) # Standard icon for hard drive/export
        excel_btn.setIconSize(QSize(24, 24))
        excel_btn.setToolTip("Export to Excel")
        excel_btn.setStyleSheet("background-color: #ffc107; border-radius: 5px; padding: 5px;")
        # TODO: Add Excel export logic here when implemented

        # Add widgets to the header layout
        header_layout.addWidget(tran_id_label)
        header_layout.addWidget(self.tran_id_input)
        header_layout.addWidget(veh_reg_label)
        header_layout.addWidget(self.veh_reg_input)
        header_layout.addWidget(get_btn)
        header_layout.addWidget(export_pdf_btn)
        header_layout.addWidget(excel_btn)
        header_layout.addStretch() # Pushes all widgets to the left

        self.center_layout.addWidget(header_panel) # Add the header panel to the center layout

        # --- Transaction Table Section ---
        self.table = QTableWidget()
        self.table.setRowCount(len(transaction_data))
        self.table.setColumnCount(11) # Define 11 columns for the table
        headers = [
            "Time", "TC Class", "AVC", "Amount", "VehRegNo", "Payment Mode",
            "Vehicle Class", "Booth", "Camera", "Title", "Duration"
        ]
        self.table.setHorizontalHeaderLabels(headers) # Set column headers
        self.table.setSelectionBehavior(self.table.SelectRows) # Select entire row on click
        self.table.setEditTriggers(self.table.NoEditTriggers) # Make table read-only
        self.table.verticalHeader().setVisible(False) # Hide row numbers

        # Apply enhanced table styling for a modern look
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                color: #333; /* Darker text for better contrast */
                gridline-color: #e0e0e0; /* Lighter gridlines */
                font-size: 11pt;
                font-family: 'Segoe UI', Arial, sans-serif; /* Modern, clean font */
                border: 1px solid #ddd; /* Subtle border around table */
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: #f8f8f8; /* Light header background */
                color: #333;
                padding: 8px; /* More padding for headers */
                border: 1px solid #e0e0e0;
                font-weight: bold;
                font-size: 10pt;
            }
            QTableWidget::item {
                padding: 5px; /* Padding for table cells */
            }
            QTableWidget::item:selected {
                background-color: #cceeff; /* Lighter blue for selection highlight */
                color: #333;
            }
            /* Custom scroll bar styling for a cleaner look */
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
                height: 0px; /* Hide default scroll bar buttons */
            }
        """)

        # Stretch columns to fill the available space horizontally
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Ensure scroll bars are always visible if content overflows
        self.table.setHorizontalScrollMode(self.table.ScrollPerPixel)
        self.table.setVerticalScrollMode(self.table.ScrollPerPixel)
        self.table.cellClicked.connect(self.on_table_row_selected) # Connect cell click to handler
        self.populate_transaction_table() # Populate the table with initial data
        self.center_layout.addWidget(self.table) # Add the table to the center layout

        # --- Images Section (LP Image and All Images) ---
        self.images_frame = QFrame()
        self.images_frame.setStyleSheet("background-color: #f0f0f0; border-radius: 5px; padding: 10px;")
        images_layout = QHBoxLayout(self.images_frame) # Horizontal layout for images
        images_layout.setContentsMargins(0, 0, 0, 0)
        images_layout.setSpacing(15) # Increased spacing for better visual separation

        # LP (License Plate) Image Label
        self.lp_image_label = QLabel("LP Image")
        self.lp_image_label.setStyleSheet(
            "background-color: white; color: #555; font-size: 12pt; border-radius: 6px; border: 1px dashed #ccc;"
        )
        self.lp_image_label.setFixedSize(320, 180) # Fixed size for consistency
        self.lp_image_label.setAlignment(Qt.AlignCenter) # Center text/image
        self.lp_image_label.setScaledContents(True) # Scale pixmap to fit label
        images_layout.addWidget(self.lp_image_label)

        # All Images Label
        self.all_image_label = QLabel("All Images")
        self.all_image_label.setStyleSheet(
            "background-color: white; color: #555; font-size: 12pt; border-radius: 6px; border: 1px dashed #ccc;"
        )
        self.all_image_label.setFixedSize(320, 180) # Fixed size for consistency
        self.all_image_label.setAlignment(Qt.AlignCenter)
        self.all_image_label.setScaledContents(True)
        images_layout.addWidget(self.all_image_label)

        images_layout.addStretch() # Pushes images to the left

        self.center_layout.addWidget(self.images_frame) # Add the images frame to the center layout
        self.main_splitter.addWidget(self.center_panel) # Add the center panel to the main splitter

    def create_right_panel(self):
        """
        Creates the right panel of the application, displaying transaction details,
        an audit comment input, and various audit action buttons.
        """
        self.right_panel = QFrame()
        self.right_panel.setStyleSheet("background-color: #383838; border-radius: 8px;") # Dark gray background
        self.right_panel.setMinimumWidth(320) # Set a minimum width for the panel
        self.right_layout = QVBoxLayout(self.right_panel) # Vertical layout for the right panel
        self.right_layout.setContentsMargins(12, 12, 12, 12) # Padding around content
        self.right_layout.setSpacing(15) # Spacing between widgets

        # --- Transaction Details Info Box ---
        self.info_box = QLabel("Select a transaction to see details")
        self.info_box.setStyleSheet(
            "background-color: white; padding: 12px; font-size: 12pt; border-radius: 6px; color: #333;")
        self.info_box.setWordWrap(True) # Allow text to wrap within the label
        self.info_box.setMinimumHeight(280) # Set a minimum height for the info box
        self.right_layout.addWidget(self.info_box)

        # --- Audit Comment Section ---
        comment_lbl = QLabel("Audit Comment:")
        # Text color is already set to white for better visibility on dark background
        comment_lbl.setStyleSheet("color: white; font-weight: bold; font-size: 11pt;")
        self.right_layout.addWidget(comment_lbl)

        self.comment_edit = QLineEdit()
        self.comment_edit.setStyleSheet(
            "background-color: #505050; color: white; padding: 8px; border-radius: 5px;")
        self.right_layout.addWidget(self.comment_edit)

        # --- Audit Action Buttons ---
        audit_buttons = [
            "Edit Transaction", "Cancel Transaction", "ETC Audit",
            "IAVC Audit", "Operator Correct", "AVC Correct", "Auditor Correct"
        ]
        # Text color of buttons is already set to white for better visibility
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
            background-color: #686868;  /* Lighter shade on hover */
                        }
                    """

        for txt in audit_buttons:
            btn = QPushButton(txt)
            btn.setStyleSheet(btn_style)
            # Connect each button to the audit_button_clicked method, passing its text
            btn.clicked.connect(lambda checked, t=txt: self.audit_button_clicked(t))
            self.right_layout.addWidget(btn)

        self.right_layout.addStretch() # Pushes all widgets to the top
        self.main_splitter.addWidget(self.right_panel) # Add the right panel to the main splitter

    def populate_transaction_table(self):
        """
        Populates the QTableWidget with data from the `transaction_data` list.
        Clears existing rows before adding new ones.
        """
        self.table.setRowCount(0) # Clear existing rows to prevent duplicates on refresh
        self.table.setRowCount(len(transaction_data)) # Set the number of rows based on data length

        for row_idx, txn in enumerate(transaction_data):
            # Populate each cell with the corresponding data from the transaction tuple
            self.table.setItem(row_idx, 0, QTableWidgetItem(txn[1]))   # Time (txn[1])
            self.table.setItem(row_idx, 1, QTableWidgetItem(txn[2]))   # TC Class (txn[2])
            self.table.setItem(row_idx, 2, QTableWidgetItem(txn[3]))   # AVC (txn[3])
            self.table.setItem(row_idx, 3, QTableWidgetItem(txn[4]))   # Amount (txn[4])
            self.table.setItem(row_idx, 4, QTableWidgetItem(txn[5]))   # VehRegNo (txn[5])
            self.table.setItem(row_idx, 5, QTableWidgetItem(txn[6]))   # Payment Mode (txn[6])
            self.table.setItem(row_idx, 6, QTableWidgetItem(txn[7]))   # Vehicle Class (txn[7])
            self.table.setItem(row_idx, 7, QTableWidgetItem(txn[8]))   # Booth (txn[8])
            self.table.setItem(row_idx, 8, QTableWidgetItem(txn[9]))   # Camera (txn[9])
            self.table.setItem(row_idx, 9, QTableWidgetItem(txn[10]))  # Title (txn[10])
            self.table.setItem(row_idx, 10, QTableWidgetItem(txn[4]))  # Duration (re-using amount for duration as per original mapping)

    def on_table_row_selected(self, row, column):
        """
        Handler for when a row in the transaction table is clicked.
        Updates the info box with transaction details, loads images,
        and plays the associated video.
        """
        txn = transaction_data[row] # Get the selected transaction data

        # Update the info box with detailed transaction information
        details = (
            f"<b>ID:</b> {txn[0]}<br>"
            f"<b>Title:</b> {txn[10]}<br>"
            f"<b>Timestamp:</b> {txn[1]}<br>"
            f"<b>Duration:</b> {txn[4]}<br>" # Using txn[4] as Duration as per table mapping
            f"<b>Booth:</b> {txn[8]}<br>"
            f"<b>Camera:</b> {txn[9]}<br>"
            f"<b>Vehicle No:</b> {txn[5]}"
        )
        self.info_box.setText(details)

        # --- Load LP Image ---
        lp_image_path = txn[12]
        if os.path.exists(lp_image_path):
            # Load pixmap, scale it to fit the label while maintaining aspect ratio
            pixmap = QPixmap(lp_image_path).scaled(self.lp_image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lp_image_label.setPixmap(pixmap)
        else:
            self.lp_image_label.setText("LP Image Not Found") # Display message if image not found
            self.lp_image_label.setPixmap(QPixmap()) # Clear any previous pixmap

        # --- Load All Images ---
        all_image_path = txn[13]
        if os.path.exists(all_image_path):
            pixmap = QPixmap(all_image_path).scaled(self.all_image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.all_image_label.setPixmap(pixmap)
        else:
            self.all_image_label.setText("All Images Not Found")
            self.all_image_label.setPixmap(QPixmap()) # Clear any previous pixmap

        # --- Play Video ---
        video_path = txn[11]
        if os.path.exists(video_path):
            # Use dynamicCall to interact with the ActiveX WMPlayer control
            self.player.dynamicCall('URL', video_path)
            self.current_video_path = video_path
        else:
            QMessageBox.warning(self, "Video Not Found", f"Video not found:\n{video_path}")
            self.current_video_path = None # Reset current video path

    def refresh_table(self):
        """
        Resets all filter inputs, repopulates the transaction table with all data,
        clears the info box and image displays, and stops video playback.
        """
        # Clear all filter input fields in the left panel
        for entry in self.filter_entries.values():
            entry.clear()
        # Clear the specific filter inputs in the center panel
        self.tran_id_input.clear()
        self.veh_reg_input.clear()

        self.populate_transaction_table() # Repopulate table with original, unfiltered data

        # Reset info box and image labels to their default states
        self.info_box.setText("Select a transaction to see details")
        self.lp_image_label.clear()
        self.lp_image_label.setText("LP Image")
        self.all_image_label.clear()
        self.all_image_label.setText("All Images")

        # Stop video playback if a video is currently loaded
        if self.current_video_path:
            self.player.dynamicCall('controls.stop')
        self.current_video_path = None

    def apply_filters(self):
        """
        This method is a placeholder for implementing actual data filtering logic.
        It retrieves the current values from the Transaction ID and Vehicle Reg No inputs.
        """
        tran_id = self.tran_id_input.text()
        veh_reg_no = self.veh_reg_input.text()

        # For demonstration, show a message box with the current filter values
        QMessageBox.information(self, "Apply Filters",
                                f"Applying filters:\nTransaction ID: '{tran_id}'\nVehicle Reg No: '{veh_reg_no}'\n"
                                "Implement actual filtering logic here to update the table.")
        # TODO: Implement actual filtering logic here.
        # This would typically involve:
        # 1. Filtering `transaction_data` based on `tran_id` and `veh_reg_no`.
        # 2. Updating `self.table.setRowCount()` and then populating the table
        #    with the `filtered_data`.

    def audit_button_clicked(self, action_name):
        """
        Generic handler for all audit action buttons.
        Displays a message box indicating which button was clicked.
        """
        QMessageBox.information(self, "Audit Action",
                                 f"Button '{action_name}' clicked.\nImplement audit logic here.")


# --- Main Application Entry Point ---
if __name__ == "__main__":
    # Create the QApplication instance
    app = QApplication(sys.argv)
    # Create an instance of the AuditApp main window
    audit_app = AuditApp()
    # Show the main window
    audit_app.show()
    # Start the Qt event loop and exit the application when it finishes
    sys.exit(app.exec_())