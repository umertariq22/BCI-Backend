#define SAMPLE_RATE 512
#define BAUD_RATE 115200
#define NUM_INPUTS 3 // Number of analog input pins

const uint8_t input_pins[NUM_INPUTS] = {36,39,34};

bool reading = false;

void setup() {
  Serial.begin(BAUD_RATE);
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    if (command == "start_reading") {
      reading = true;
    } else if (command == "stop_reading") {
      reading = false;
    }
  }

  if (reading) {
    static unsigned long past = 0;
    unsigned long present = micros();
    unsigned long interval = present - past;
    past = present;

    static long timer = 0;
    timer -= interval;

    if (timer < 0) {
      timer += 1000000 / SAMPLE_RATE;

      // Read and send data as a comma-separated array
      for (int i = 0; i < NUM_INPUTS; i++) {
        int sensor_value = analogRead(input_pin[i]);
        Serial.print(sensor_value);
        if (i < NUM_INPUTS - 1) {
          Serial.print(","); // Add a comma between values
        }
      }
      Serial.println(); // End the line after each set of readings
    }
  }
}
