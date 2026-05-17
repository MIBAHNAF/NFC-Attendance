# Smart NFC Attendance Logger

Smart NFC Attendance Logger is a prototype contactless attendance system that uses an Arduino Uno, a PN532 NFC reader, and a Python desktop application to record attendance in an Excel workbook. The system was designed as a low-cost proof of concept for replacing manual sign-in sheets with a faster tap-based workflow.

The prototype reads a stable numeric identifier from a supported contactless card or mobile wallet interaction, sends that identifier to a Python application over USB serial or Bluetooth Low Energy, and marks the matching person as present in `attendance.xlsm`.

## Project Goals

- Reduce the time needed to take attendance in a classroom or lab setting.
- Use inexpensive, widely available hardware.
- Support contactless identification through NFC-enabled cards or devices.
- Store attendance in a familiar Excel-based format.
- Provide a simple GUI for scanning, registration, and second-device enrollment.

## System Overview

The system has three main parts:

1. **NFC reader firmware**

   The Arduino firmware in `src/main.cpp` initializes a PN532 NFC reader over I2C. When a compatible NFC payment credential is tapped, the firmware sends EMV APDU commands, parses TLV data, and outputs a numeric identifier over serial and HM-10 Bluetooth.

2. **Transport layer**

   `transport.py` reads incoming scan data from either USB serial or BLE. Both transports push scanned identifiers into a shared queue so the attendance application can process them in one place.

3. **Attendance logger GUI**

   `attendance_logger.py` opens `attendance.xlsm`, finds the column for the current date, receives scanned identifiers, matches them against stored records, and marks the corresponding student as present.

## Hardware

Required:

- Arduino Uno
- PN532 NFC reader module
- USB cable
- NFC/contactless card or supported mobile wallet credential
- Windows laptop or desktop running Python

Optional:

- HM-10 compatible BLE module, advertised as `DSD TECH`

## Wiring

For Arduino Uno and PN532 in I2C mode:

```text
PN532 VCC -> Arduino 5V
PN532 GND -> Arduino GND
PN532 SDA -> Arduino A4
PN532 SCL -> Arduino A5
```

Make sure the PN532 board is set to I2C mode using its switch or jumper configuration.

Optional HM-10 wiring used by the firmware:

```text
HM-10 TX -> Arduino RX / pin 1
HM-10 RX -> Arduino TX / pin 0
HM-10 VCC -> Arduino 5V or 3.3V, depending on module requirements
HM-10 GND -> Arduino GND
```

Note: using pins `0` and `1` for Bluetooth can interfere with USB serial upload/debugging. Disconnect the BLE module if upload issues occur.

## Software Requirements

- Python 3
- PlatformIO
- Arduino framework for PlatformIO
- Python packages:
  - `openpyxl`
  - `pyserial`
  - `bleak`

Install Python dependencies with:

```powershell
pip install openpyxl pyserial bleak
```

## Firmware Setup

From the project root:

```powershell
cd W:\Nfc_Apple_pay
pio run -t upload --upload-port COM3
```

Use the correct COM port for your Arduino. To monitor serial output:

```powershell
pio device monitor -p COM3 -b 9600
```

Expected startup output:

```text
HELLO
PN532 ready - tap card
```

When a compatible card is tapped, the firmware prints a numeric identifier similar to:

```text
41139824914470533005
```

## Running the Attendance Logger

Run the Python GUI from the project root:

```powershell
cd W:\Nfc_Apple_pay
python attendance_logger.py
```

The application will:

- open `attendance.xlsm`
- use the worksheet named `Template`
- look for today's date in row `9`
- wait for scan data from USB or BLE
- mark the matched row with `P`

If a scanned identifier is not already registered, the app prompts for the person's name and phone number, stores the new record, and marks the person present for the current date.

## Excel Workbook Layout

The workbook is used as the attendance database.

Expected layout in `attendance.xlsm`:

```text
Column A: Primary identifier
Column B: Secondary identifier
Column C: Phone number
Column D: Name
Row 9, Column E onward: Date headers
Row 10 onward: Student records
```

The logger only runs if today's date exists in row `9`. If the app reports `Date column missing`, add the current date to the date header row.

## Attendance Flow

1. Start the Arduino firmware.
2. Confirm the serial monitor shows `HELLO`.
3. Start `attendance_logger.py`.
4. Tap a registered card or device.
5. The app checks the scanned identifier against columns `A` and `B`.
6. If found, the app writes `P` under today's date.
7. If already marked, the app displays an `Already marked` status.
8. If not found, the app starts a new-person registration flow.

## Second Device Support

The GUI includes a checkbox for enrolling a second device. When enabled, after a new person is added, the app waits for another valid scan and stores it in column `B`. This allows one person to be recognized by two different contactless credentials.

## Current Status

The prototype has been verified to:

- detect the PN532 reader over I2C
- communicate with the Arduino over `COM3` at `9600` baud
- output a long numeric identifier from a contactless tap
- pass that identifier into the Python attendance logger
- save a second device identifier into the Excel workbook

## Limitations

- The firmware currently selects the Visa EMV application ID. Mastercard and other networks would require additional APDU selection logic and testing.
- Mobile wallet behavior can vary by issuer, phone, card network, and wallet implementation.
- The system stores identifiers in Excel without encryption.
- The Excel workbook must contain the current date before the app starts.
- The BLE path depends on a compatible HM-10 style device and the `bleak` Python package.
- Pins `0` and `1` are shared with Arduino serial communication, so BLE wiring may complicate uploading firmware.

## Privacy and Security Notes

This project is a prototype for academic research and should not be deployed with real payment credentials in a production environment without significant security work.

Depending on the card or wallet, the scanned value may represent payment-card-derived data, a tokenized account value, or another stable identifier. Treat all scanned identifiers as sensitive. A production version should hash or encrypt identifiers, restrict access to the workbook, avoid storing raw payment-related values, and document informed consent from participants.

## Repository Structure

```text
Nfc_Apple_pay/
  attendance_logger.py   Python Tkinter attendance application
  transport.py           USB serial and BLE reader classes
  attendance.xlsm        Excel attendance workbook
  platformio.ini         PlatformIO configuration
  src/main.cpp           Arduino PN532 firmware
  test1.py               Helper script for listing serial ports
  include/               PlatformIO include folder
  lib/                   PlatformIO library folder
  test/                  PlatformIO test folder
```

## Future Work

- Add Mastercard support by selecting the Mastercard AID and testing record parsing.
- Add automatic date-column creation in the workbook.
- Store hashed identifiers instead of raw scanned values.
- Add a configuration file for COM port, BLE device name, workbook path, and sheet name.
- Improve error handling when BLE dependencies are missing.
- Add a simple export/reporting workflow for attendance summaries.
- Replace Excel storage with SQLite or a small web dashboard for multi-user deployments.

## Thesis Direction

This project can support a thesis focused on the design, implementation, and evaluation of a low-cost NFC-based attendance system. Strong thesis sections include:

- motivation and problem statement
- NFC and EMV background
- system architecture
- hardware implementation
- software implementation
- attendance data model
- testing and evaluation
- security, privacy, and ethical limitations
- future improvements

