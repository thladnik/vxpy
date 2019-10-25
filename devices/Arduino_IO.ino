const int PIN = 13;
int inbyte = 0;

void setup() {
  Serial.begin(9600); // Baud rate 9600
  while (!Serial) {
    // Wait for serial to be ready
  }
  pinMode(PIN, OUTPUT);
}

void loop() {
  if (Serial.available() > 0) {
    inbyte = Serial.read();

    if (inbyte > 0) {
      digitalWrite(PIN, HIGH);
      delay(1); // 1 ms pulse
      digitalWrite(PIN, LOW);
    }
  }
}