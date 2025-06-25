#include <Wire.h>
#include <Adafruit_PN532.h>
#include <SoftwareSerial.h>

/* ---------- HM‑10 wiring ---------- */
constexpr uint8_t BT_RX = 1;          // Arduino RX ← HM‑10 TX
constexpr uint8_t BT_TX = 0;          // Arduino TX → HM‑10 RX
SoftwareSerial    bt(BT_RX, BT_TX);

/* ---------- PN532 (I²C) ---------- */
Adafruit_PN532    nfc(-1, -1, &Wire);

/* helpers */
template<typename T> inline void bothPrintln(const T& v){ Serial.println(v); bt.println(v); }

/* ---------- EMV TLV parser (unchanged) ---------- */
void parseTLV(const uint8_t* buf, uint8_t len, String &pan, String &exp){
  for(uint8_t i = 0; i < len; ){
    uint8_t tag = buf[i++], L = buf[i++];
    if(tag == 0x70) { parseTLV(buf + i, L, pan, exp); }
    else if(tag == 0x5A) {                 // PAN
      pan = "";
      for(uint8_t j = 0; j < L; j++) pan += String(buf[i + j], HEX);
    }
    else if(tag == 0x5F && buf[i] == 0x24){ // Expiry YYMM
      i++; L = buf[i++];
      exp = "";
      for(uint8_t j = 0; j < L; j++){
        uint8_t b = buf[i + j];
        exp += (b < 0x10 ? "0" : "") + String(b, HEX);
      }
    }
    else if(tag == 0x57 && pan.length() == 0){   // Track‑2 fallback
      String t = "";
      for(uint8_t j = 0; j < L; j++){
        uint8_t b = buf[i + j];
        t += char('0' + ((b >> 4) & 0xF));
        t += char('0' + (b & 0xF));
      }
      int sep = t.indexOf('D'); if(sep < 0) sep = t.indexOf('=');
      if(sep > 0){ pan = t.substring(0, sep); exp = t.substring(sep + 1, sep + 5); }
    }
    i += L;
  }
}

/* ---------- setup ---------- */
void setup(){
  Serial.begin(9600);        // USB‑CDC
  bt.begin(9600);            // HM‑10 default baud
  while(!Serial){}           // wait for USB enumeration

  bothPrintln("HELLO");      // banner that Python looks for

  nfc.begin();
  if(!nfc.getFirmwareVersion()){
    bothPrintln("PN532 missing");
    while(true);
  }
  nfc.SAMConfig();
  bothPrintln("PN532 ready — tap card");
}

/* EMV command APDUs */
const uint8_t SEL_VISA[] = {0x00,0xA4,0x04,0x00,0x07,
                            0xA0,0x00,0x00,0x00,0x03,0x10,0x10, 0x00};
const uint8_t RD1[]      = {0x00,0xB2,0x01,0x0C,0x00};

/* ---------- loop ---------- */
void loop(){
  if(!nfc.inListPassiveTarget()){ delay(250); return; }

  uint8_t buf[255], len = sizeof(buf);

  if(!nfc.inDataExchange((uint8_t*)SEL_VISA, sizeof(SEL_VISA), buf, &len)){ delay(400); return; }
  len = sizeof(buf);
  if(!nfc.inDataExchange((uint8_t*)RD1, sizeof(RD1), buf, &len)){ delay(400); return; }

  String pan, exp;  parseTLV(buf, len, pan, exp);
  String uid = pan + exp;         // 16‑19‑digit PAN + 4‑digit YYMM
  bothPrintln(uid);               // *** the only runtime payload ***

  delay(2500);                    // simple debounce
}
