## ACTIVE PROJECT: "Mini Purdue Plant" CTF (concept stage; plan approval required before each sprint)

PURPOSE
A miniature server/equipment cooling room, built as a multi-device model at different Purdue levels and played as a CTF. Players assess it the way an OT assessor would: enumerate, classify, find writable points reachable from the wrong level, cause visible physical effects, and compare a vulnerable build to a hardened one. Audience: intermediate to practitioners. Users: students, visiting sponsors, lab staff. All work is on my own lab devices on an isolated network.

PROCESS STORY (use consistently in labels, dashboards, demo script)
A cooling room that keeps equipment from overheating. Real temperature sensor is the process variable. Fan/damper (servo) responds to temperature. An over-temperature interlock puts the system in a safe state. A door contact is the physical-access alarm. No water, level, or flow sensors. Attack story: spoof a cool reading and the room "overheats" while the dashboard says all is well.

FRAMEWORK DECISION (no sponsor-mandated framework)
- Backbone: ISA/IEC 62443 (zones and conduits, SL 1-4, seven foundational requirements: IAC, UC, SI, DC, RDF, TRE, RA).
- Tagging: MITRE ATT&CK for ICS technique names on every challenge and IDS alert. Verify IDs and current version at attack.mitre.org; do not guess IDs.
- Reference: NIST SP 800-82 Rev. 3. CSF 2.0 only as an optional one-line mapping.
- Course source of truth: Operational_Technology_Cybersecurity.pdf in this project. IEC 62443 text is paywalled; cite the textbook and ISA public pages.

ARCHITECTURE (proposed, unverified)
- L0/1 Field: ESP32-WROOM-32E field node with DS18B20 (temperature), BH1750 (light), reed switch (door), potentiometer on an ADC1 pin (setpoint), SG90 servo (damper, separate 5 V rail, common ground), LED bar (room-temperature / damper indicator), buzzer and status LEDs. Pico (non-W) optional as a wired L0 I/O node; Pico W optional as a rogue/inserted device.
- L2 Control: second ESP32 as PLC/gateway: MQTT client plus Modbus TCP server (verify libraries on Arduino core 3.3.8).
- L3 and L3.5 (single-Pi build): one Raspberry Pi 4 (8 GB) on Raspberry Pi OS Lite or Debian (not Kali) running Mosquitto, Grafana or Node-RED, a time-series store, and the scoreboard. Plant Wi-Fi on wlan0 (lab-only fake key); attacker/enterprise side on eth0; nftables enforces the boundary. Known limitation: broker and firewall share a host, so the DMZ is logical. A second Pi can separate them later. Use an SSD or high-endurance SD card.
- L4/5 Attacker seat: Kali Linux (Pi or laptop), limited initial access.
- Defender: existing ESP32 with OLED, acting as IDS and the "operator face".
- OPC-UA is a stretch goal on the Pi only. DNP3 and IEC 104 are simulated on the Pi or discussed.

TOOLS
- nmap is the primary discovery tool. Use gentle timing and limited ports; test that the ESP32 gateway survives scans. Verify Modbus and MQTT NSE scripts on the installed nmap version before relying on them.
- mosquitto_sub/pub and a Modbus client for interaction after discovery.

PLAYER PROGRESSION (after the 4 web levels)
5 Network discovery (nmap) -> 6 Browse MQTT namespace -> 7 Read gateway Modbus data model -> 8 Classify points (read-only vs writable, ranked by criticality) -> 9 Over-exposure: viewer writes a point it should not -> 10 Physical impact: spoof a sensor or change a setpoint; interlock trips to safe state -> 11 Defender/IDS detection -> 12 Replay all attacks against the hardened build.
Map each stage to a 62443 foundational requirement and ATT&CK for ICS technique names (discovery to RDF/DC; over-exposure to UC/IAC; spoofing to SI; detection to TRE; safe state and scan tolerance to RA).

SPRINTS (not time-based; each sprint is gated by its exit criteria, and I approve before the next one starts)
Every sprint also updates: README, wiring/pin table, BOM, security notes, changelog, decisions log, and a verified/unverified list.

Sprint 0 - Existing build baseline (everything I have already made)
- Scope: current ESP32-WROOM-32E build with OLED face and the four web levels. [Confirm exact contents and versions.]
- Deliverables: README, wiring table, BOM, setup/build steps, and config separated from code (no hard-coded credentials; example config with fake values).
- Exit: another person can rebuild and run it from the docs; all four levels pass a written test list.

Sprint 1 - Plant network and server foundation
- Scope: Pi 4 on Raspberry Pi OS Lite; plant Wi-Fi on wlan0; eth0 attacker side; nftables rules; Mosquitto installed; Kali attacker seat can reach only what is intended.
- Spikes: confirm access-point setup for the installed OS version.
- Exit: ESP32 joins the plant network; nmap from Kali sees only the intended hosts and ports; firewall rules documented and tested.

Sprint 2 - Field node and sensors (stages 5-6)
- Scope: field ESP32 with DS18B20, BH1750, reed switch, setpoint knob; publishes to MQTT; live dashboard.
- Spikes: verify sensor libraries on Arduino core 3.3.8; finalize pin plan against the datasheet (ADC1 only, avoid flash/strapping pins).
- Exit: warming the sensor moves the dashboard; disconnected or invalid sensor produces a fault state, not a bad reading; MQTT-browse challenge works.

Sprint 3 - L2 gateway and the writable point (stages 7-9)
- Scope: gateway ESP32 with Modbus TCP and a setpoint register; viewer account that can write when it should not; classification worksheet and answer key.
- Spikes: Modbus library on core 3.3.8; nmap NSE script availability; gateway survives gentle scans.
- Exit: discovery, data-model, classification and over-exposure challenges pass an end-to-end test; each maps to a 62443 FR and ATT&CK name.

Sprint 4 - Physical process and safety interlock (stage 10)
- Scope: servo damper, LED indicator, buzzer, status LEDs, reset button; over-temperature interlock and safe state; spoofing challenge.
- Safety: low-voltage only; interlock cannot be disabled over the network; safe state on loss of communication; human review before anything beyond low-voltage hardware.
- Exit: spoofed or manipulated values cause the visible effect; interlock trips and returns to a safe state; reset works.

Sprint 5 - Defender and scoreboard (stage 11)
- Scope: OLED face as IDS (out-of-range values, unexpected publishers, write attempts); dashboard alerts; live scoreboard; ATT&CK tags on alerts.
- Exit: each earlier attack raises the expected alert; no false alarms during a normal run; logs contain no secrets.

Sprint 6 - Hardened build (stage 12)
- Scope: TLS with certificate validation, per-device credentials, read-only ACLs, input sanity checks, signed OTA where supported; vulnerable vs hardened side by side (two plants, or an operator-only switch not changeable from the attacker seat).
- Rule: explain eFuse, secure boot and flash encryption tradeoffs before enabling; permanent changes need a test unit.
- Exit: replaying stages 5-10 against the hardened build fails as designed; results table maps each control to the attack it stops.

Sprint 7 - Demo, docs, polish
- Scope: attract mode (about 2 minutes, no keyboard) and hands-on practitioner mode; demo guide; threat model; poster/one-page summary; enclosure and labeling.
- Stretch (only if everything above is solid): OPC-UA on the Pi, Pico W rogue device, second Pi as a separate DMZ.
- Exit: a first-time visitor sees an attack change the room, sees the defender detect it, and sees the hardened build block it.

SAFETY AND SECURITY RULES
- Safety first, availability second, security third.
- Private isolated network only. Fake credentials only. Every weakness labeled "intentional".
- Low-voltage actuators only; no mains, relays or heaters without human review.
- Servo/actuator power is separate from the ESP32 3.3 V rail.
- Only unclassified, public information. Remind me before I paste anything controlled; follow sponsor and lab handling rules.
- No real credentials, certificates or hostnames in code; use Kconfig/NVS or an untracked secrets file with a committed example template.

HARDWARE (confirm and update)
- Dev board: ESP32-WROOM-32E, 4 MB flash, Arduino core 3.3.8. More ESP32s and Raspberry Pi Picos on hand. Raspberry Pi 4 (8 GB) for the plant server; Kali for the attacker seat.
- Pin plan not yet done. ADC1 only for analog, avoid flash pins, watch strapping pins, GPIO34-39 are input-only.

STATUS: Concept only. Next step is a short plan for Sprint 0 for my approval. Mark anything unverified as unverified.
