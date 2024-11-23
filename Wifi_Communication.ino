#include <WiFi.h>
#include <HTTPClient.h>

// Replace with your Wi-Fi network credentials
const char* ssid = "Redmi Note 11";
const char* password = "atfu1234";

// Replace with your server URL
const char* serverName = "http://192.168.120.169:8000/eeg";

void setup() {
  Serial.begin(115200);
  
  // Connect to Wi-Fi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to Wi-Fi");
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("\nConnected to Wi-Fi");
  Serial.println("ESP32 IP Address: " + WiFi.localIP().toString());
  Serial.println("Connecting to: " + String(serverName));


  // Send POST request
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverName);
    http.addHeader("Content-Type", "application/json");

    // Create JSON payload
    String jsonPayload = "{\"key1\":\"value1\",\"key2\":\"value2\"}";

    // Send POST request
    int httpResponseCode = http.POST(jsonPayload);
    Serial.println("HTTP Response code: " + String(httpResponseCode));

    // Check response
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("HTTP Response code: " + String(httpResponseCode));
      Serial.println("Response: " + response);
    } else {
      Serial.println("Error in sending POST request");
      Serial.println("HTTP Response code: " + String(httpResponseCode));
    }

    http.end();  // Free resources
  } else {
    Serial.println("Wi-Fi not connected");
  }
}

void loop() {
  // Empty - no actions needed here for this example
}
