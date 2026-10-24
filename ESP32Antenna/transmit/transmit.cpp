#include <Arduino.h>
#include <esp_now.h>
#include <WiFi.h>

void OnDataRecv(const uint8_t *, const uint8_t *, int);

void setup() {
  Serial.begin(115200);
  
  // ESP-NOW requires the WiFi to be in Station Mode
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  WiFi.setTxPower(WIFI_POWER_8_5dBm);
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }
  
  // Register the receive callback to pass incoming ESP-NOW packets
  esp_now_register_recv_cb(OnDataRecv);
}

// Callback when ESP-NOW data is received from remote nodes
void OnDataRecv(const uint8_t * mac, const uint8_t *incomingData, int len) {
  // Print received data back to the Python script over USB
  for(int i=0; i<6; i++) {
    Serial.printf("%02X", mac[i]);
    if(i<5) Serial.print(":");
  }
  Serial.print("|");
  Serial.write(incomingData, len);
  Serial.println(); 
}

void loop() {
  // Check if Python sent a command over USB
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n'); // Read until the newline
    command.trim();
    // Parse the command (Format expected: FF:FF:FF:FF:FF:FF|PAYLOAD)
    int separatorIndex = command.indexOf('|');
    if (separatorIndex > 0) {
      String macStr = command.substring(0, separatorIndex);
      String payload = command.substring(separatorIndex + 1);
      // Convert MAC String to byte array
      uint8_t targetAddress[6];
      int values[6];
      if (6 == sscanf(macStr.c_str(), "%x:%x:%x:%x:%x:%x", &values[0], &values[1], &values[2], &values[3], &values[4], &values[5])) {
        for (int i = 0; i < 6; ++i) {
          targetAddress[i] = (uint8_t) values[i];
        }
        
        // Register the peer temporarily
        esp_now_peer_info_t peerInfo = {};
        memcpy(peerInfo.peer_addr, targetAddress, 6);
        peerInfo.channel = 0;  
        peerInfo.encrypt = false;
        
        if (!esp_now_is_peer_exist(targetAddress)) {
          esp_now_add_peer(&peerInfo);
        }
        
        // Send the payload over ESP-NOW
        // 1. Convert the text string into a mathematical integer
        int mathValue = payload.toInt();
        // 2. Squash it into a single byte (0-255, perfect for servo angles or simple codes)
        uint8_t rawByte = (uint8_t)mathValue;
        // 3. Send the raw byte over ESP-NOW instead of the text string
        esp_now_send(targetAddress, &rawByte, sizeof(rawByte));
      }
    }
  }
  delay(1);
} 