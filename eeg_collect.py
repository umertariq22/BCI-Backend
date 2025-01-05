import serial
import time
import numpy as np
import pandas as pd

class SensorReader:
    def __init__(self, port, baud_rate=115200, timeout=1):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.ser = None
        self.FREQ = 512 
            
    def connect(self):
        try:
            self.ser = serial.Serial()
            self.ser.port = self.port
            self.ser.baudrate = self.baud_rate
            self.ser.timeout = self.timeout
            self.ser.setDTR(False)
            self.ser.setRTS(False)
            
            self.ser.open()
            print(f"Connected to {self.port} at {self.baud_rate} baud.")
        except Exception as e:
            print(f"Failed to connect to {self.port}: {e}")
            return False
        return True
    
    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print(f"Disconnected from {self.port}")
        
        return True

    def send_command(self, command):
        if self.ser and self.ser.is_open:
            self.ser.write(command.encode() + b'\n')
            print(f"Sent command: {command}")
            return True
        else:
            print("Serial connection is not open")
            return False

    def start_reading(self):
        return self.send_command("start_reading")

    def stop_reading(self):
        return self.send_command("stop_reading")

    def read_data(self):
        if self.ser and self.ser.is_open:
            if self.ser.in_waiting > 0:
                data = self.ser.readline().decode('utf-8').strip()
                return data
        return None

    def read_sensor_data(self):
        while True:
            data = self.read_data()
            if data:
                data = int(data)
                return data
            else:
                return None
    
    def read_one_second_data(self):
        data = []
        for _ in range(self.FREQ):
            sample = self.read_sensor_data()
            if sample:
                data.append(sample)
            if len(data) == self.FREQ:
                return data
            time.sleep(1/self.FREQ)
        
        return None
    
    
if __name__ == "__main__":
    sensor = SensorReader(port='COM7')  # Replace with your serial port
    eeg_data = []
    if sensor.connect():
        try:
            started_reading = sensor.start_reading()
            
            for data in sensor.read_sensor_data():
                eeg_data.append(data)
        except KeyboardInterrupt:
            print("Reading interrupted.")
        finally:
            sensor.stop_reading()
            sensor.disconnect()
    
    eeg_data = np.array(eeg_data)
    eeg_data = eeg_data.flatten()  
    
    df = pd.DataFrame(eeg_data,columns=['eeg_data'])
    df.to_csv("eeg_data.csv", index=False)
    print("EEG data saved to eeg_data.csv")
    
    
    
