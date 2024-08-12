import sys
import csv
import random
import matplotlib
matplotlib.use('Qt5Agg')  # Set the backend to Qt5Agg

from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QDoubleSpinBox, QGroupBox, QSplitter, QCheckBox, QComboBox, QMainWindow, QMessageBox, QDesktopWidget
from PyQt5.QtCore import Qt, QTimer, QTime, QDateTime
from PyQt5.QtGui import QFont, QPixmap
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import MaxNLocator
from datetime import datetime, timedelta

CONNECT_LED = False  # True
if CONNECT_LED:
    from utils.gpio import blink_led
else:
    # Dummy function to represent blink_led functionality
    def blink_led(pin):
        print(f"Blinking LED on pin {pin}")

class TimeSeriesGraph(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self.xlim_duration = timedelta(minutes=10)  # Default xlim duration
        self.ax.set_xlim(datetime.now(), datetime.now() + self.xlim_duration)
        self.times = []
        self.data = {}
        self.lines = {}
        self.ax.legend(loc='upper left')
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def update_plot(self, times, data, units, multipliers):
        if not times:
            return  # Return if there are no times to plot
        self.ax.clear()
        self.times = times
        for label, values in data.items():
            unit = units.get(label, '')
            multiplier = multipliers.get(label, 1)
            self.ax.plot(self.times, [v * multiplier for v in values], label=f'{label} (x{multiplier} {unit})')
        self.ax.set_xlim(self.times[-1] - self.xlim_duration, self.times[-1])
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self.ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
        self.ax.legend(loc='upper left')
        self.canvas.draw()

    def set_xlim_duration(self, duration):
        self.xlim_duration = duration
        if self.times:
            self.ax.set_xlim(self.times[-1] - self.xlim_duration, self.times[-1])
            self.canvas.draw()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.headers = ["idx", "datetime", "dissolved oxygen concentration", "pressure", "flow rate", "pump speed", "Upper tank temp", "lower tank temp", "C-box", "External temp"]
        self.units = {
            "dissolved oxygen concentration": "ppm",
            "pressure": "atm",
            "flow rate": "L/min",
            "pump speed": "",
            "Upper tank temp": "°C",
            "lower tank temp": "°C",
            "C-box": "°C",
            "External temp": "°C"
        }
        self.multipliers = {
            "dissolved oxygen concentration": 0.1,
            "pressure": 1,
            "flow rate": 10,
            "pump speed": 10,
            "Upper tank temp": 1,
            "lower tank temp": 1,
            "C-box": 1,
            "External temp": 1
        }
        self.data = []
        self.buffer = []
        self.start_time = datetime.now()
        self.csv_filename = f"sow_data_{self.start_time.strftime('%Y%m%d_%H%M%S')}.csv"
        self.o2 = 250
        self.pressure = 25
        self.flow_rate = 2
        self.pump_speed = 1.0
        self.upper_temp = 4
        self.lower_temp = 5
        self.cbox_temp = self.lower_temp + 4
        self.external_temp = 25  # Static value for external temperature
        self.graph_data = {
            'Temperature': ['Upper tank temp', 'lower tank temp', 'C-box', 'External temp'],
            'Pressure': ['pressure'],
            'Flow Rate': ['flow rate'],
            'Pump Speed': ['pump speed']
        }
        self.selected_buttons = {
            'Temperature': False,
            'Pressure': False,
            'Flow Rate': False,
            'Pump Speed': False
        }
        self.output_labels = {}  # Dictionary to map buttons to their corresponding output labels
        self.connect_led = True  # Example flag to simulate LED connection
        self.initUI()
        self.create_csv_file()
        self.read_csv_file()  # Initialize the GUI with data from the CSV file
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self.update_data)
        self.data_timer.start(5000)  # Update data every 5 seconds
        self.save_timer = QTimer()
        self.save_timer.timeout.connect(self.save_last_buffer_to_csv)
        self.save_timer.start(30000)  # Save data every 30 seconds

    def initUI(self):
        self.setWindowTitle('S.O.W Machine v1')
        self.setFixedSize(800, 400)  # Set fixed size

        self.setGeometry(0, 0, 800, 400)  # Set the position to (0, 0) and size to (800, 400)
        
        font = QFont("Arial", 12)
        mainLayout = QHBoxLayout()
        leftLayout = QVBoxLayout()

        # Input Group
        self.inputGroup = QGroupBox('<Input>')
        self.inputGroup.setFont(font)
        self.inputLayout = QGridLayout()

        # Auto/Manual Button
        self.auto_manual_button = QPushButton('Auto / Manual')
        self.auto_manual_button.setFont(font)
        self.auto_manual_button.setCheckable(True)
        self.auto_manual_button.setChecked(False)  # Default mode is Auto (off)
        self.auto_manual_button.setFixedHeight(21)  # Reduced height to 70%
        self.auto_manual_button.toggled.connect(self.toggle_manual_mode)
        self.inputLayout.addWidget(self.auto_manual_button, 0, 0, 1, 3)

        # Profile Buttons
        self.profile_buttons = []
        for i in range(1, 4):
            profile_button = QPushButton(f'Profile {i}')
            profile_button.setFont(font)
            profile_button.setCheckable(True)
            profile_button.setChecked(False)
            profile_button.setFixedHeight(21)  # Reduced height to 70%
            profile_button.clicked.connect(lambda _, b=profile_button: self.confirm_action(lambda: self.update_profile_buttons(b), b))
            self.profile_buttons.append(profile_button)
            self.inputLayout.addWidget(profile_button, 1, i-1)

        # Manual Controls
        pump_speed_label = QLabel('Pump Speed')
        pump_speed_label.setFont(font)
        pump_speed_label.setFixedHeight(21)  # Reduced height to 70%
        self.inputLayout.addWidget(pump_speed_label, 2, 0)
        self.pump_speed_spinbox = QDoubleSpinBox()
        self.pump_speed_spinbox.setFont(font)
        self.pump_speed_spinbox.setRange(0, 2)
        self.pump_speed_spinbox.setDecimals(1)
        self.pump_speed_spinbox.setSingleStep(0.2)
        self.pump_speed_spinbox.setValue(1.0)
        self.pump_speed_spinbox.setFixedHeight(21)  # Reduced height to 70%
        self.inputLayout.addWidget(self.pump_speed_spinbox, 2, 1)
        lower_temp_label = QLabel('Lower Tank Temp')
        lower_temp_label.setFont(font)
        lower_temp_label.setFixedHeight(21)  # Reduced height to 70%
        self.inputLayout.addWidget(lower_temp_label, 3, 0)
        self.lower_temp_spinbox = QDoubleSpinBox()
        self.lower_temp_spinbox.setFont(font)
        self.lower_temp_spinbox.setSuffix(' °C')
        self.lower_temp_spinbox.setRange(1, 10)
        self.lower_temp_spinbox.setDecimals(2)
        self.lower_temp_spinbox.setSingleStep(0.5)
        self.lower_temp_spinbox.setValue(5)
        self.lower_temp_spinbox.setFixedHeight(21)  # Reduced height to 70%
        self.inputLayout.addWidget(self.lower_temp_spinbox, 3, 1)
        pressure_label = QLabel('Pressure')
        pressure_label.setFont(font)
        pressure_label.setFixedHeight(21)  # Reduced height to 70%
        self.inputLayout.addWidget(pressure_label, 4, 0)
        self.pressure_spinbox = QDoubleSpinBox()
        self.pressure_spinbox.setFont(font)
        self.pressure_spinbox.setSuffix(' atm')
        self.pressure_spinbox.setRange(23, 27)
        self.pressure_spinbox.setDecimals(1)
        self.pressure_spinbox.setSingleStep(0.5)
        self.pressure_spinbox.setValue(25)
        self.pressure_spinbox.setFixedHeight(21)  # Reduced height to 70%
        self.inputLayout.addWidget(self.pressure_spinbox, 4, 1)
        self.change_confirm_button1 = QPushButton('Confirm')
        self.change_confirm_button1.setFont(font)
        self.change_confirm_button1.setStyleSheet("color: green;")  # Change text color to green
        self.change_confirm_button1.setFixedHeight(21)  # Reduced height to 70%
        self.change_confirm_button1.clicked.connect(lambda: self.confirm_action(self.update_pump_speed_temp_pressure, self.change_confirm_button1))
        self.inputLayout.addWidget(self.change_confirm_button1, 4, 2)
        self.pump1_button = QPushButton('Pump1 on / off')
        self.pump1_button.setFont(font)
        self.pump1_button.setCheckable(True)
        self.pump1_button.setFixedHeight(21)  # Reduced height to 70%
        self.pump1_button.clicked.connect(lambda: self.confirm_action(lambda: self.toggle_pump1_action(), self.pump1_button))
        self.inputLayout.addWidget(self.pump1_button, 5, 0)
        self.pump2_button = QPushButton('Pump2 on / off')
        self.pump2_button.setFont(font)
        self.pump2_button.setCheckable(True)
        self.pump2_button.setFixedHeight(21)  # Reduced height to 70%
        self.pump2_button.clicked.connect(lambda: self.confirm_action(lambda: self.toggle_pump2_action(), self.pump2_button))
        self.inputLayout.addWidget(self.pump2_button, 5, 1)
        self.chiller_button = QPushButton('Chiller S/W on / off')
        self.chiller_button.setFont(font)
        self.chiller_button.setCheckable(True)
        self.chiller_button.setFixedHeight(21)  # Reduced height to 70%
        self.chiller_button.clicked.connect(lambda: self.confirm_action(lambda: self.toggle_chiller_action(), self.chiller_button))
        self.inputLayout.addWidget(self.chiller_button, 5, 2)
        flow_label = QLabel('Flow Rate')
        flow_label.setFont(font)
        flow_label.setFixedHeight(21)  # Reduced height to 70%
        self.inputLayout.addWidget(flow_label, 6, 0)
        self.flow_spinbox = QDoubleSpinBox()
        self.flow_spinbox.setFont(font)
        self.flow_spinbox.setSuffix(' L/min')
        self.flow_spinbox.setRange(1.5, 2.5)
        self.flow_spinbox.setDecimals(1)
        self.flow_spinbox.setSingleStep(0.1)
        self.flow_spinbox.setValue(2)
        self.flow_spinbox.setFixedHeight(21)  # Reduced height to 70%
        self.inputLayout.addWidget(self.flow_spinbox, 6, 1)
        self.change_confirm_button2 = QPushButton('Confirm')
        self.change_confirm_button2.setFont(font)
        self.change_confirm_button2.setStyleSheet("color: green;")  # Change text color to green
        self.change_confirm_button2.setFixedHeight(21)  # Reduced height to 70%
        self.change_confirm_button2.clicked.connect(lambda: self.confirm_action(self.update_flow_rate, self.change_confirm_button2))
        self.inputLayout.addWidget(self.change_confirm_button2, 6, 2)

        # Hide manual controls initially
        for i in range(2, 7):
            self.inputLayout.itemAtPosition(i, 0).widget().setVisible(False)
            self.inputLayout.itemAtPosition(i, 1).widget().setVisible(False)
            if self.inputLayout.itemAtPosition(i, 2):
                self.inputLayout.itemAtPosition(i, 2).widget().setVisible(False)

        self.inputGroup.setLayout(self.inputLayout)
        leftLayout.addWidget(self.inputGroup)

        # Real-time Changes Group
        self.realtimeGroup = QGroupBox('<Real-time Changes>')
        self.realtimeGroup.setFont(font)
        self.realtimeLayout = QVBoxLayout()

        self.seeInputButton = QPushButton('See Input')
        self.seeInputButton.setFont(font)
        self.seeInputButton.setFixedHeight(21)  # Reduced height to 70%
        self.seeInputButton.clicked.connect(self.show_input_group)
        self.realtimeLayout.addWidget(self.seeInputButton)

        buttonLayout = QHBoxLayout()
        self.temp_button = QCheckBox('Temperature')
        self.temp_button.setFont(font)
        self.temp_button.setFixedHeight(21)  # Reduced height to 70%
        self.temp_button.stateChanged.connect(self.update_graph_selection)
        buttonLayout.addWidget(self.temp_button)
        self.pressure_button = QCheckBox('Pressure')
        self.pressure_button.setFont(font)
        self.pressure_button.setFixedHeight(21)  # Reduced height to 70%
        self.pressure_button.stateChanged.connect(self.update_graph_selection)
        buttonLayout.addWidget(self.pressure_button)
        self.flow_button = QCheckBox('Flow Rate')
        self.flow_button.setFont(font)
        self.flow_button.setFixedHeight(21)  # Reduced height to 70%
        self.flow_button.stateChanged.connect(self.update_graph_selection)
        buttonLayout.addWidget(self.flow_button)
        self.pump_speed_button = QCheckBox('Pump Speed')
        self.pump_speed_button.setFont(font)
        self.pump_speed_button.setFixedHeight(21)  # Reduced height to 70%
        self.pump_speed_button.stateChanged.connect(self.update_graph_selection)
        buttonLayout.addWidget(self.pump_speed_button)
        self.realtimeLayout.addLayout(buttonLayout)

        self.graph = TimeSeriesGraph()
        self.realtimeLayout.addWidget(self.graph)

        sliderLayout = QHBoxLayout()
        self.slider_label = QLabel("X-axis scale", self)
        self.slider_label.setFont(font)
        self.slider_label.setFixedHeight(21)  # Reduced height to 70%
        sliderLayout.addWidget(self.slider_label, alignment=Qt.AlignRight)
        self.xlim_combo = QComboBox()
        self.xlim_combo.addItems(["1 min", "3 min", "10 min", "30 min", "1 hour", "1 day"])
        self.xlim_combo.setFont(font)
        self.xlim_combo.setFixedHeight(21)  # Reduced height to 70%
        self.xlim_combo.setCurrentIndex(2)  # Set default to "10 min"
        self.xlim_combo.currentIndexChanged.connect(self.change_xlim)
        sliderLayout.addWidget(self.xlim_combo, alignment=Qt.AlignRight)
        self.realtimeLayout.addLayout(sliderLayout)

        self.realtimeGroup.setLayout(self.realtimeLayout)
        self.realtimeGroup.setVisible(False)  # Hide real-time changes group initially
        leftLayout.addWidget(self.realtimeGroup)

        # Button to toggle between Input and Real-time Changes
        self.toggleButton = QPushButton('See real-time changes')
        self.toggleButton.setFont(font)
        self.toggleButton.setFixedHeight(21)  # Reduced height to 70%
        self.toggleButton.clicked.connect(self.toggle_group)
        leftLayout.addWidget(self.toggleButton)

        # Right Layout
        rightLayout = QVBoxLayout()
        self.outputGroup = QGroupBox('<Output>')
        self.outputGroup.setFont(font)
        self.outputLayout = QGridLayout()

        # Synchronized Outputs
        self.pump1_status_label = QLabel('Pump1:')
        self.pump1_status_label.setFont(font)
        self.pump1_status_label.setFixedHeight(21)  # Reduced height to 70%
        self.outputLayout.addWidget(self.pump1_status_label, 0, 0)
        self.pump1_status_value = QLabel('Off')
        self.pump1_status_value.setFont(font)
        self.pump1_status_value.setFixedHeight(21)  # Reduced height to 70%
        self.outputLayout.addWidget(self.pump1_status_value, 0, 1)
        self.output_labels['Pump1'] = self.pump1_status_value  # Map button to output label

        self.pump2_status_label = QLabel('Pump2:')
        self.pump2_status_label.setFont(font)
        self.pump2_status_label.setFixedHeight(21)  # Reduced height to 70%
        self.outputLayout.addWidget(self.pump2_status_label, 1, 0)
        self.pump2_status_value = QLabel('Off')
        self.pump2_status_value.setFont(font)
        self.pump2_status_value.setFixedHeight(21)  # Reduced height to 70%
        self.outputLayout.addWidget(self.pump2_status_value, 1, 1)
        self.output_labels['Pump2'] = self.pump2_status_value  # Map button to output label

        self.chiller_status_label = QLabel('Chiller S/W:')
        self.chiller_status_label.setFont(font)
        self.chiller_status_label.setFixedHeight(21)  # Reduced height to 70%
        self.outputLayout.addWidget(self.chiller_status_label, 2, 0)
        self.chiller_status_value = QLabel('Off')
        self.chiller_status_value.setFont(font)
        self.chiller_status_value.setFixedHeight(21)  # Reduced height to 70%
        self.outputLayout.addWidget(self.chiller_status_value, 2, 1)
        self.output_labels['Chiller S/W'] = self.chiller_status_value  # Map button to output label

        # Other Outputs
        self.o2_label = QLabel('D.O. Meter (ppm)')
        self.o2_label.setFont(font)
        self.o2_label.setFixedHeight(21)  # Reduced height to 70%
        self.outputLayout.addWidget(self.o2_label, 3, 0)
        self.o2_value = QLabel('250')
        self.o2_value.setFont(font)
        self.o2_value.setFixedHeight(21)  # Reduced height to 70%
        self.outputLayout.addWidget(self.o2_value, 3, 1)
        self.upper_temp_label = QLabel('Upper Tank Temp (°C)')
        self.upper_temp_label.setFont(font)
        self.upper_temp_label.setFixedHeight(21)  # Reduced height to 70%
        self.outputLayout.addWidget(self.upper_temp_label, 3, 2)
        self.upper_temp_value = QLabel('4')
        self.upper_temp_value.setFont(font)
        self.upper_temp_value.setFixedHeight(21)  # Reduced height to 70%
        self.outputLayout.addWidget(self.upper_temp_value, 3, 3)
        self.pressure_label = QLabel('Pressure (atm)')
        self.pressure_label.setFont(font)
        self.pressure_label.setFixedHeight(21)  # Reduced height to 70%
        self.outputLayout.addWidget(self.pressure_label, 4, 0)
        self.pressure_value = QLabel('25')
        self.pressure_value.setFont(font)
        self.pressure_value.setFixedHeight(21)  # Reduced height to 70%
        self.outputLayout.addWidget(self.pressure_value, 4, 1)
        self.lower_temp_label = QLabel('Lower Tank Temp (°C)')
        self.lower_temp_label.setFont(font)
        self.lower_temp_label.setFixedHeight(21)  # Reduced height to 70%
        self.outputLayout.addWidget(self.lower_temp_label, 4, 2)
        self.lower_temp_value = QLabel('5')
        self.lower_temp_value.setFont(font)
        self.lower_temp_value.setFixedHeight(21)  # Reduced height to 70%
        self.outputLayout.addWidget(self.lower_temp_value, 4, 3)
        self.flow_label = QLabel('Flow Rate (L/min)')
        self.flow_label.setFont(font)
        self.flow_label.setFixedHeight(21)  # Reduced height to 70%
        self.outputLayout.addWidget(self.flow_label, 5, 0)
        self.flow_value = QLabel('2')
        self.flow_value.setFont(font)
        self.flow_value.setFixedHeight(21)  # Reduced height to 70%
        self.outputLayout.addWidget(self.flow_value, 5, 1)
        self.cbox_label = QLabel('C-box (°C)')
        self.cbox_label.setFont(font)
        self.cbox_label.setFixedHeight(21)  # Reduced height to 70%
        self.outputLayout.addWidget(self.cbox_label, 5, 2)
        self.cbox_value = QLabel('9')
        self.cbox_value.setFont(font)
        self.cbox_value.setFixedHeight(21)  # Reduced height to 70%
        self.outputLayout.addWidget(self.cbox_value, 5, 3)
        self.pump_speed_label = QLabel('Pump Speed')
        self.pump_speed_label.setFont(font)
        self.pump_speed_label.setFixedHeight(21)  # Reduced height to 70%
        self.outputLayout.addWidget(self.pump_speed_label, 6, 0)
        self.pump_speed_value = QLabel('1')
        self.pump_speed_value.setFont(font)
        self.pump_speed_value.setFixedHeight(21)  # Reduced height to 70%
        self.outputLayout.addWidget(self.pump_speed_value, 6, 1)
        self.outputGroup.setLayout(self.outputLayout)
        rightLayout.addWidget(self.outputGroup)
        
        # Side panel layout
        sideGroup = QGroupBox('<Side Panel>')
        sideGroup.setFont(font)
        sideLayout = QGridLayout()
        current_time_text = QLabel('Current Time:')
        current_time_text.setFont(font)
        current_time_text.setFixedHeight(21)  # Reduced height to 70%
        sideLayout.addWidget(current_time_text, 0, 0)
        self.current_time_label = QLabel()
        self.current_time_label.setFont(font)
        self.current_time_label.setFixedHeight(21)  # Reduced height to 70%
        self.update_time()
        timer = QTimer(self)
        timer.timeout.connect(self.update_time)
        timer.start(1000)
        sideLayout.addWidget(self.current_time_label, 0, 1)
        external_temp_text = QLabel('External Temperature (°C):')
        external_temp_text.setFont(font)
        external_temp_text.setFixedHeight(21)  # Reduced height to 70%
        sideLayout.addWidget(external_temp_text, 1, 0)
        self.external_temp_value = QLabel('25')
        self.external_temp_value.setFont(font)
        self.external_temp_value.setFixedHeight(21)  # Reduced height to 70%
        sideLayout.addWidget(self.external_temp_value, 1, 1)
        logo_label = QLabel('logo of S.O.W machine v1')
        logo_label.setFont(font)
        logo_label.setFixedHeight(21)  # Reduced height to 70%
        sideLayout.addWidget(logo_label, 2, 0, 1, 2)
        logo_pixmap = QLabel()
        logo_pixmap.setPixmap(QPixmap('sow_machine.jpg').scaled(100, 100, Qt.KeepAspectRatio))
        logo_pixmap.setAlignment(Qt.AlignCenter)
        logo_pixmap.setFixedHeight(21)  # Reduced height to 70%
        sideLayout.addWidget(logo_pixmap, 3, 0, 1, 2)
        sideGroup.setLayout(sideLayout)
        rightLayout.addWidget(sideGroup)
        
        splitter = QSplitter(Qt.Horizontal)
        left_widget = QWidget()
        left_widget.setLayout(leftLayout)
        right_widget = QWidget()
        right_widget.setLayout(rightLayout)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 400])  # Set initial sizes as 1:1 ratio
        mainLayout.addWidget(splitter)
        central_widget = QWidget()
        central_widget.setLayout(mainLayout)
        self.setCentralWidget(central_widget)

    def create_csv_file(self):
        try:
            with open(self.csv_filename, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(self.headers)
        except Exception as e:
            print(f"Error creating CSV file: {e}")

    def read_csv_file(self):
        try:
            with open(self.csv_filename, 'r') as file:
                reader = csv.reader(file)
                next(reader)  # Skip the header
                self.data = [row for row in reader]
                for row in self.data:
                    row[1] = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S.%f')  # Parse datetime strings
                    for i in range(2, len(row)):
                        row[i] = float(row[i])  # Convert the remaining fields to float
            self.update_output_group()
            self.update_graphs()
        except FileNotFoundError:
            print("CSV file not found, starting with an empty dataset.")
        except Exception as e:
            print(f"Error reading CSV file: {e}")

    def update_data(self):
        current_time = datetime.now()
        idx = len(self.data) + 1
        self.o2 = self.get_new_value(self.o2, 50, 400, 5)
        self.pressure = self.get_new_value(self.pressure, 23, 27, 0.1)
        self.flow_rate = self.get_new_value(self.flow_rate, 1.5, 2.5, 0.1)
        self.pump_speed = self.get_new_value(self.pump_speed, 0, 2, 0.2)
        self.upper_temp = self.get_new_value(self.upper_temp, 1, 10, 0.02)
        self.lower_temp = self.get_new_value(self.lower_temp, 1, 10, 0.02)
        self.cbox_temp = round(self.lower_temp + 4, 3)
        row = [idx, current_time, self.o2, self.pressure, self.flow_rate, self.pump_speed, self.upper_temp, self.lower_temp, self.cbox_temp, self.external_temp]
        self.data.append(row)
        self.buffer.append(row)
        self.update_graphs()
        self.update_output_group()

    def get_new_value(self, current_value, min_value, max_value, max_change_rate):
        change = random.uniform(-max_change_rate, max_change_rate)
        new_value = current_value + change
        return round(max(min(new_value, max_value), min_value), 3)

    def update_pump_speed_temp_pressure(self):
        self.pump_speed = self.pump_speed_spinbox.value()
        self.lower_temp = self.lower_temp_spinbox.value()
        self.pressure = self.pressure_spinbox.value()
        self.cbox_temp = round(self.lower_temp + 4, 3)
        self.pump_speed_value.setText(str(self.pump_speed))
        self.lower_temp_value.setText(str(self.lower_temp))
        self.pressure_value.setText(str(self.pressure))
        self.cbox_value.setText(str(self.cbox_temp))
        if self.data:
            self.data[-1][5] = self.pump_speed
            self.data[-1][7] = self.lower_temp
            self.data[-1][3] = self.pressure
            self.data[-1][8] = self.cbox_temp
        self.update_graphs()
        self.update_output_group()

    def update_flow_rate(self):
        self.flow_rate = self.flow_spinbox.value()
        self.flow_value.setText(str(self.flow_rate))
        if self.data:
            self.data[-1][4] = self.flow_rate
        self.update_graphs()
        self.update_output_group()

    def save_last_buffer_to_csv(self):
        if not self.buffer:
            return
        try:
            with open(self.csv_filename, 'a', newline='') as file:
                writer = csv.writer(file)
                last_row = self.buffer[-1]
                writer.writerow([last_row[0], last_row[1].strftime('%Y-%m-%d %H:%M:%S.%f')] + last_row[2:])
            self.buffer.clear()
        except Exception as e:
            print(f"Error saving to CSV file: {e}")

    def update_output_group(self):
        if self.data:
            latest_data = self.data[-1]
            self.o2_value.setText(str(latest_data[2]))
            self.pressure_value.setText(str(latest_data[3]))
            self.flow_value.setText(str(latest_data[4]))
            self.pump_speed_value.setText(str(latest_data[5]))
            self.upper_temp_value.setText(str(latest_data[6]))
            self.lower_temp_value.setText(str(latest_data[7]))
            self.cbox_value.setText(str(latest_data[8]))
            self.external_temp_value.setText(str(latest_data[9]))
        self.update_status_color(self.pump1_status_value, self.pump1_button.isChecked())
        self.update_status_color(self.pump2_status_value, self.pump2_button.isChecked())
        self.update_status_color(self.chiller_status_value, self.chiller_button.isChecked())

    def update_status_color(self, label, status):
        if status:
            label.setText('On')
            label.setStyleSheet("color: red;")
        else:
            label.setText('Off')
            label.setStyleSheet("color: black;")

    def update_graphs(self):
        if not self.data:
            return
        times = [row[1] for row in self.data]
        data_dict = {}
        for key, selected in self.selected_buttons.items():
            if selected:
                for label in self.graph_data[key]:
                    data_dict[label] = [row[self.headers.index(label)] for row in self.data]
        if self.graph:
            self.graph.update_plot(times, data_dict, self.units, self.multipliers)

    def update_time(self):
        if self.current_time_label:
            current_time = QTime.currentTime().toString('hh:mm:ss')
            self.current_time_label.setText(current_time)

    def toggle_manual_mode(self):
        checked = self.auto_manual_button.isChecked()
        for i in range(2, 7):  # 5 manual control rows (2 to 6)
            self.inputLayout.itemAtPosition(i, 0).widget().setVisible(checked)
            self.inputLayout.itemAtPosition(i, 1).widget().setVisible(checked)
            if self.inputLayout.itemAtPosition(i, 2):
                self.inputLayout.itemAtPosition(i, 2).widget().setVisible(checked)
        for button in self.profile_buttons:
            button.setVisible(not checked)

    def update_profile_buttons(self, button):
        for b in self.profile_buttons:
            if b != button:
                b.setChecked(False)
        self.toggle_button_color(button)

    def toggle_button_color(self, button):
        if button.isChecked():
            button.setStyleSheet("color: red;")
        else:
            button.setStyleSheet("color: black;")
        self.update_status_color(self.output_labels.get(button.text(), QLabel()), button.isChecked())

    def update_graph_selection(self, state):
        checkbox = self.sender()
        label = checkbox.text()
        self.selected_buttons[label] = state == Qt.Checked
        self.update_graphs()

    def change_xlim(self, index):
        durations = {
            0: timedelta(minutes=1),
            1: timedelta(minutes=3),
            2: timedelta(minutes=10),
            3: timedelta(minutes=30),
            4: timedelta(hours=1),
            5: timedelta(days=1)
        }
        if self.graph:
            self.graph.set_xlim_duration(durations[index])

    def toggle_group(self):
        if self.inputGroup.isVisible():
            self.inputGroup.setVisible(False)
            self.realtimeGroup.setVisible(True)
            self.toggleButton.setText('See Input')
        else:
            self.inputGroup.setVisible(True)
            self.realtimeGroup.setVisible(False)
            self.toggleButton.setText('See real-time changes')

    def show_input_group(self):
        self.inputGroup.setVisible(True)
        self.realtimeGroup.setVisible(False)
        self.toggleButton.setText('See real-time changes')

    def confirm_action(self, action, button):
        current_state = button.isChecked()
        button.setChecked(not current_state)  # Temporarily revert the state
        reply = QMessageBox.question(self, 'Confirmation', 'Are you sure to change settings?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            button.setChecked(current_state)  # Set the state to the intended state
            action()
        else:
            button.setChecked(not current_state)  # Revert to the original state

    def toggle_pump1_action(self):
        self.toggle_button_color(self.pump1_button)
        if self.connect_led:
            blink_led(17)

    def toggle_pump2_action(self):
        self.toggle_button_color(self.pump2_button)
        if self.connect_led:
            blink_led(18)
            
    def toggle_chiller_action(self):
        self.toggle_button_color(self.chiller_button)
        if self.connect_led:
            blink_led(27)

def main():
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()  # Show the main window
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
