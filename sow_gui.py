import sys
import csv
import random
import matplotlib
matplotlib.use('Qt5Agg')  # Set the backend to Qt5Agg

from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QMainWindow, QMessageBox, QFrame
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPixmap
from datetime import datetime, timedelta

CONNECT_LED = False  # True
Fullscreen_Mode = False  # Set this to True for full-screen mode

if CONNECT_LED:
    from utils.gpio import blink_led
else:
    # Dummy function to represent blink_led functionality
    def blink_led(pin):
        print(f"Blinking LED on pin {pin}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set window title
        self.setWindowTitle('Super Oxygen Water Generator Model S1')

        # Check if Fullscreen_Mode is True
        if Fullscreen_Mode:
            self.showFullScreen()
        else:
            self.setGeometry(0, 0, 800, 480)

        # Data and timers
        self.o2_concentration = 250  # initial value for dissolved oxygen concentration
        self.water_production = 10  # initial value for oxygen water production
        self.data = []
        self.buffer = []
        self.start_time = datetime.now()
        self.csv_filename = f"sow_data_{self.start_time.strftime('%Y%m%d_%H%M%S')}.csv"

        # Setup CSV file
        self.create_csv_file()

        # Timers for updates and saving data
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self.update_output)
        self.data_timer.start(5000)  # Update every 5 seconds

        self.save_timer = QTimer()
        self.save_timer.timeout.connect(self.save_last_buffer_to_csv)
        self.save_timer.start(30000)  # Save data every 30 seconds

        # Main layout (grid)
        main_layout = QGridLayout()

        # Fonts
        large_font = QFont("Arial", 24, QFont.Bold)
        medium_font = QFont("Arial", 18, QFont.Bold)
        small_font = QFont("Arial", 12, QFont.Bold)

        # Set fixed sizes for rows and columns
        main_layout.setColumnStretch(0, 3)  # Left side with buttons
        main_layout.setColumnStretch(1, 1)  # Right side with output display

        main_layout.setRowStretch(0, 2)  # Top row with title and logo
        main_layout.setRowStretch(1, 3)  # Power button and System Booting
        main_layout.setRowStretch(2, 3)  # Pump and Chiller buttons
        main_layout.setRowStretch(3, 2)  # Auto Mode buttons
        main_layout.setRowStretch(4, 1)  # Detailed Input / Output button

        # Top section: Title and Logo
        top_layout = QHBoxLayout()

        title_layout = QVBoxLayout()
        title_label = QLabel('Super Oxygen Water Generator Model S1', self)
        title_label.setFont(large_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(title_label)

        main_screen_label = QLabel('Main Screen', self)
        main_screen_label.setFont(medium_font)
        main_screen_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(main_screen_label)

        top_layout.addLayout(title_layout)

        logo_pixmap = QLabel()
        logo_pixmap.setPixmap(QPixmap('logo.png').scaled(150, 150, Qt.KeepAspectRatio))
        logo_pixmap.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(logo_pixmap)

        main_layout.addLayout(top_layout, 0, 0, 1, 2)

        # Second row: Power button and System Booting
        power_and_booting_layout = QHBoxLayout()

        self.power_button = QPushButton('POWER', self)
        self.power_button.setFont(medium_font)
        self.power_button.setStyleSheet("background-color: white; color: black;")
        self.power_button.setFixedSize(150, 80)
        self.power_button.setCheckable(True)
        self.power_button.clicked.connect(lambda: self.confirm_action(self.toggle_power, self.power_button))
        power_and_booting_layout.addWidget(self.power_button, alignment=Qt.AlignLeft)

        self.system_booting_label = QLabel('', self)  # Default text is blank
        self.system_booting_label.setFont(medium_font)
        self.system_booting_label.setAlignment(Qt.AlignCenter)
        power_and_booting_layout.addWidget(self.system_booting_label)

        main_layout.addLayout(power_and_booting_layout, 1, 0)

        # Third row: Pump and Chiller buttons
        pump_buttons_layout = QHBoxLayout()

        self.main_pump_button = QPushButton('Main PUMP SW\n(On / Off)', self)
        self.main_pump_button.setFont(small_font)
        self.main_pump_button.setCheckable(True)
        self.main_pump_button.setStyleSheet("background-color: white; color: black;")
        self.main_pump_button.setFixedSize(150, 80)
        self.main_pump_button.clicked.connect(lambda: self.check_power_and_confirm(self.toggle_pump1, self.main_pump_button))
        pump_buttons_layout.addWidget(self.main_pump_button, alignment=Qt.AlignLeft)

        # Up/Down Toggle and Speed Display for Main Pump
        toggle_layout_main = QVBoxLayout()

        self.up_button_main = QPushButton('▲', self)
        self.up_button_main.setFont(small_font)
        self.up_button_main.setFixedSize(30, 20)
        self.up_button_main.clicked.connect(lambda: self.change_speed(self.speed_display_main, 0.1))
        toggle_layout_main.addWidget(self.up_button_main)

        self.down_button_main = QPushButton('▼', self)
        self.down_button_main.setFont(small_font)
        self.down_button_main.setFixedSize(30, 20)
        self.down_button_main.clicked.connect(lambda: self.change_speed(self.speed_display_main, -0.1))
        toggle_layout_main.addWidget(self.down_button_main)

        pump_buttons_layout.addLayout(toggle_layout_main)

        self.speed_display_main = QLabel('', self)  # Default blank text
        self.speed_display_main.setFont(small_font)
        self.speed_display_main.setFixedSize(40, 20)  # Fixed space for the display
        self.speed_display_main.setAlignment(Qt.AlignCenter)
        pump_buttons_layout.addWidget(self.speed_display_main)

        self.cycle_pump_button = QPushButton('Cycle PUMP SW\n(On / Off)', self)
        self.cycle_pump_button.setFont(small_font)
        self.cycle_pump_button.setCheckable(True)
        self.cycle_pump_button.setStyleSheet("background-color: white; color: black;")
        self.cycle_pump_button.setFixedSize(150, 80)
        self.cycle_pump_button.clicked.connect(lambda: self.check_power_and_confirm(self.toggle_pump2, self.cycle_pump_button))
        pump_buttons_layout.addWidget(self.cycle_pump_button, alignment=Qt.AlignCenter)

        # Up/Down Toggle and Speed Display for Cycle Pump
        toggle_layout_cycle = QVBoxLayout()

        self.up_button_cycle = QPushButton('▲', self)
        self.up_button_cycle.setFont(small_font)
        self.up_button_cycle.setFixedSize(30, 20)
        self.up_button_cycle.clicked.connect(lambda: self.change_speed(self.speed_display_cycle, 0.1))
        toggle_layout_cycle.addWidget(self.up_button_cycle)

        self.down_button_cycle = QPushButton('▼', self)
        self.down_button_cycle.setFont(small_font)
        self.down_button_cycle.setFixedSize(30, 20)
        self.down_button_cycle.clicked.connect(lambda: self.change_speed(self.speed_display_cycle, -0.1))
        toggle_layout_cycle.addWidget(self.down_button_cycle)

        pump_buttons_layout.addLayout(toggle_layout_cycle)

        self.speed_display_cycle = QLabel('', self)  # Default blank text
        self.speed_display_cycle.setFont(small_font)
        self.speed_display_cycle.setFixedSize(40, 20)  # Fixed space for the display
        self.speed_display_cycle.setAlignment(Qt.AlignCenter)
        pump_buttons_layout.addWidget(self.speed_display_cycle)

        self.chiller_button = QPushButton('Chiller SW\n(On / Off)', self)
        self.chiller_button.setFont(small_font)
        self.chiller_button.setCheckable(True)
        self.chiller_button.setStyleSheet("background-color: white; color: black;")
        self.chiller_button.setFixedSize(150, 80)
        self.chiller_button.clicked.connect(lambda: self.check_power_and_confirm(self.toggle_pump3, self.chiller_button))
        pump_buttons_layout.addWidget(self.chiller_button, alignment=Qt.AlignRight)

        main_layout.addLayout(pump_buttons_layout, 2, 0)

        # Fourth row: Auto Mode buttons
        auto_mode_buttons_layout = QHBoxLayout()

        self.auto_mode1_button = QPushButton('Auto Mode\n(Highest Performance)', self)
        self.auto_mode1_button.setFont(small_font)
        self.auto_mode1_button.setCheckable(True)
        self.auto_mode1_button.setStyleSheet("background-color: white; color: black;")
        self.auto_mode1_button.setFixedSize(200, 80)
        self.auto_mode1_button.clicked.connect(lambda: self.check_power_and_confirm(self.toggle_auto_mode, self.auto_mode1_button))
        auto_mode_buttons_layout.addWidget(self.auto_mode1_button, alignment=Qt.AlignCenter)

        self.auto_mode2_button = QPushButton('Auto Mode\n(Power Save)', self)
        self.auto_mode2_button.setFont(small_font)
        self.auto_mode2_button.setCheckable(True)
        self.auto_mode2_button.setStyleSheet("background-color: white; color: black;")
        self.auto_mode2_button.setFixedSize(200, 80)
        self.auto_mode2_button.clicked.connect(lambda: self.check_power_and_confirm(self.toggle_auto_mode, self.auto_mode2_button))
        auto_mode_buttons_layout.addWidget(self.auto_mode2_button, alignment=Qt.AlignCenter)

        main_layout.addLayout(auto_mode_buttons_layout, 3, 0)

        # Right section: Output display with narrower lines
        output_frame = QFrame()
        output_frame.setFrameShape(QFrame.Box)
        output_frame.setLineWidth(1)
        output_layout = QVBoxLayout(output_frame)

        # Output Display for Dissolved Oxygen Concentration
        o2_concentration_label = QLabel('Dissolved Oxygen Concentration:', self)
        o2_concentration_label.setFont(small_font)
        o2_concentration_label.setAlignment(Qt.AlignCenter)
        self.oxygen_label = QLabel(f'{self.o2_concentration} ppm', self)
        self.oxygen_label.setFont(medium_font)
        self.oxygen_label.setStyleSheet("color: red;")
        self.oxygen_label.setAlignment(Qt.AlignCenter)
        output_layout.addWidget(o2_concentration_label)
        output_layout.addWidget(self.oxygen_label)

        # Output Display for Oxygen Water Production
        water_production_label = QLabel('Oxygen Water Production:', self)
        water_production_label.setFont(small_font)
        water_production_label.setAlignment(Qt.AlignCenter)
        self.water_label = QLabel(f'{self.water_production} lpm', self)
        self.water_label.setFont(medium_font)
        self.water_label.setStyleSheet("color: red;")
        self.water_label.setAlignment(Qt.AlignCenter)
        output_layout.addWidget(water_production_label)
        output_layout.addWidget(self.water_label)

        main_layout.addWidget(output_frame, 1, 1, 3, 1)

        # Fifth row: Detailed Input / Output button below output panel, aligned with Auto Mode buttons
        self.detailed_button = QPushButton('Detailed Input / Output', self)
        self.detailed_button.setFont(small_font)
        self.detailed_button.setFixedSize(200, 50)
        self.detailed_button.clicked.connect(self.show_detailed_screen)

        detailed_button_layout = QHBoxLayout()
        detailed_button_layout.addStretch()
        detailed_button_layout.addWidget(self.detailed_button)
        detailed_button_layout.addStretch()

        main_layout.addLayout(detailed_button_layout, 4, 1)

        # Central Widget Setup
        central_widget = QWidget(self)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def toggle_power(self):
        if self.power_button.isChecked():
            self.power_button.setStyleSheet("background-color: red; color: white;")
            self.system_booting_label.setText("System now booting...")
            blink_led(17)  # Replace with actual GPIO pin if necessary
            QTimer.singleShot(5000, self.set_system_running)  # Set system as running after 5 seconds
        else:
            self.power_button.setStyleSheet("background-color: white; color: black;")
            blink_led(17)  # Replace with actual GPIO pin if necessary
            self.system_booting_label.setText("System shut down...")

    def set_system_running(self):
        self.system_booting_label.setText("System now working!")

    def check_power_and_confirm(self, action, button):
        if not self.power_button.isChecked():
            QMessageBox.warning(self, 'Warning', 'Power is off. Please turn on the power first.')
            button.setChecked(False)  # Ensure the button stays OFF
            return
        self.confirm_action(action, button)

    def toggle_pump1(self):
        button = self.sender()
        if button.isChecked():
            button.setStyleSheet("background-color: blue; color: white;")
            self.speed_display_main.setText('1.0')  # Set default speed
            blink_led(27)  # Replace with actual GPIO pin if necessary
        else:
            button.setStyleSheet("background-color: white; color: black;")
            self.speed_display_main.setText('')  # Clear speed display
            blink_led(27)  # Replace with actual GPIO pin if necessary
            
    def toggle_pump2(self):
        button = self.sender()
        if button.isChecked():
            button.setStyleSheet("background-color: blue; color: white;")
            self.speed_display_cycle.setText('1.0')  # Set default speed
            blink_led(22)  # Replace with actual GPIO pin if necessary
        else:
            button.setStyleSheet("background-color: white; color: black;")
            self.speed_display_cycle.setText('')  # Clear speed display
            blink_led(22)  # Replace with actual GPIO pin if necessary
            
    def toggle_pump3(self):
        button = self.sender()
        if button.isChecked():
            button.setStyleSheet("background-color: blue; color: white;")
            blink_led(23)  # Replace with actual GPIO pin if necessary
        else:
            button.setStyleSheet("background-color: white; color: black;")
            blink_led(23)  # Replace with actual GPIO pin if necessary

    def toggle_auto_mode(self):
        button = self.sender()

        if button.isChecked():
            # Turn off the other auto mode button
            if button == self.auto_mode1_button:
                self.auto_mode2_button.setChecked(False)
                self.auto_mode2_button.setStyleSheet("background-color: white; color: black;")
            elif button == self.auto_mode2_button:
                self.auto_mode1_button.setChecked(False)
                self.auto_mode1_button.setStyleSheet("background-color: white; color: black;")

            button.setStyleSheet("background-color: blue; color: white;")
        else:
            button.setStyleSheet("background-color: white; color: black;")

    def change_speed(self, speed_display, delta):
        current_speed = float(speed_display.text()) if speed_display.text() else 1.0
        new_speed = round(min(max(current_speed + delta, 0.5), 2.0), 1)  # Ensure speed stays within 0.5 to 2.0
        speed_display.setText(f"{new_speed}")
        self.change_speed_action(new_speed)

    def change_speed_action(self, speed):
        print(f"Speed changed to: {speed}")
        # Implement any additional functionality needed when the speed changes

    def update_output(self):
        # Randomly update dissolved oxygen concentration and oxygen water production
        self.o2_concentration = round(random.uniform(240, 260), 3)
        self.water_production = round(random.uniform(8, 12), 3)
        self.oxygen_label.setText(f'{self.o2_concentration} ppm')
        self.water_label.setText(f'{self.water_production} lpm')

        # Add the new data to the buffer
        current_time = datetime.now()
        self.buffer.append([current_time, self.o2_concentration, self.water_production])

    def save_last_buffer_to_csv(self):
        if not self.buffer:
            return
        try:
            with open(self.csv_filename, 'a', newline='') as file:
                writer = csv.writer(file)
                for entry in self.buffer:
                    writer.writerow([entry[0].strftime('%Y-%m-%d %H:%M:%S.%f'), entry[1], entry[2]])
            self.buffer.clear()
        except Exception as e:
            print(f"Error saving to CSV file: {e}")

    def create_csv_file(self):
        try:
            with open(self.csv_filename, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["datetime", "dissolved oxygen concentration", "oxygen water production"])
        except Exception as e:
            print(f"Error creating CSV file: {e}")

    def show_detailed_screen(self):
        # Function to show detailed input/output screen
        QMessageBox.information(self, 'Detailed Input/Output', 'Switching to Detailed Input/Output Screen.')

    def confirm_action(self, action, button):
        current_state = button.isChecked()
        button.setChecked(not current_state)  # Temporarily revert the state
        reply = QMessageBox.question(self, 'Confirmation', 'Are you sure to change settings?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            button.setChecked(current_state)  # Set the state to the intended state
            action()
        else:
            button.setChecked(not current_state)  # Revert to the original state

def main():
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
