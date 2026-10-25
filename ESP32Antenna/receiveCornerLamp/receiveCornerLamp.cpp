// example for  servo pressing a button

#include <esp_now.h>
#include <WiFi.h>
#include "Protocol.h"
// Variables to hold the data temporarily
volatile bool messageReady = false; 
uint8_t senderMac[6];
uint8_t message;

#include <Arduino.h>
#include <ESP32Servo.h>

Servo myServo;
// Choose a PWM-capable pin (avoid pins 34-39 as they are input only)
int servoPin = 9; 
int LampOnAngle = 140;
int LampOffAngle = 90;



void OnDataRecv(const uint8_t * mac, const uint8_t *incomingData, int len) {
  // 1. Copy the data into our global variables
  memcpy(senderMac, mac, 6);
  message=*incomingData;
  if(len>1){
    // whaaat? Only singular codes for now
    return;
  }
  
  // 2. Flip the switch to tell the loop() there is work to do
  messageReady = true; 
}

void setup() {
  //ESP-NOW:
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  if (esp_now_init() != ESP_OK) {
    return;
  }
  esp_now_register_recv_cb(OnDataRecv);


  // Server:
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);
  // Standard SG90 pulse widths are usually 500us to 2400us
  myServo.setPeriodHertz(50);      
  myServo.attach(servoPin, 600, 2550); 
  // TODO:
  Serial.begin(115200);
}

void loop() {
  if (messageReady == true) {
    if (memcmp(senderMac, MAC_TRANSMITTER, 6) != 0) {
      messageReady=false;
      // false code 1
      return;
    }

    if(message==CODE_TURN_ON){
      myServo.write(LampOnAngle);
    }
    else if(message==CODE_TURN_OFF){
      myServo.write(LampOffAngle);
    }
    else{
      //man this broken too:
    }

    messageReady = false;
  } 
}
