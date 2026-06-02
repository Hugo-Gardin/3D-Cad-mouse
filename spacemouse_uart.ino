/*
 * SpaceMouse UART — ESP32 WROOM
 * Envoie les valeurs des axes via Serial (USB)
 * Format : "X:0,Y:0,Z:0,B:0\n"
 * Axes : GPIO32 (X), GPIO35 (Y), GPIO34 (Z), bouton GPIO33
 */

#include "soc/rtc_cntl_reg.h"

const int PIN_X    = 32;
const int PIN_Y    = 35;
const int PIN_Z    = 34;
const int PIN_BTN  = 33;
const int CENTER_X = 1906;
const int CENTER_Y = 1998;
const int CENTER_Z = 2048;
const int DEADZONE = 60;

int readADC(int pin) {
  long s = 0;
  for (int i = 0; i < 8; i++) { s += analogRead(pin); delayMicroseconds(100); }
  return s / 8;
}

int16_t toHID(int raw, int center) {
  int d = raw - center;
  if (abs(d) < DEADZONE) return 0;
  d = (d > 0) ? d - DEADZONE : d + DEADZONE;
  float n = constrain((float)d / (2048.0f - DEADZONE), -1.0f, 1.0f);
  return (int16_t)(n * 32767.0f);
}

void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  Serial.begin(115200);
  analogSetAttenuation(ADC_11db);
  analogReadResolution(12);
  pinMode(PIN_BTN, INPUT_PULLUP);
}

unsigned long lastSend = 0;

void loop() {
  if (millis() - lastSend < 16) return;
  lastSend = millis();

  int16_t x =  toHID(readADC(PIN_X), CENTER_X);
  int16_t y = -toHID(readADC(PIN_Y), CENTER_Y);
  int16_t z =  toHID(readADC(PIN_Z), CENTER_Z);
  int btn = digitalRead(PIN_BTN) == LOW ? 1 : 0;

  // Format simple parseable par Python
  Serial.print("X:");
  Serial.print(x);
  Serial.print(",Y:");
  Serial.print(y);
  Serial.print(",Z:");
  Serial.print(z);
  Serial.print(",B:");
  Serial.println(btn);
}
