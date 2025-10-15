# 🌡️ Computherm B / ProSmart System Integration for Home Assistant

![Banner](https://brands.home-assistant.io/computherm_b/dark_logo.png)




Bring your **Computherm B / ProSmart System Wi-Fi Thermostat** into Home Assistant and take full control of your heating! Monitor temperatures, manage boost modes, and view schedules—all from one elegant dashboard.

---

## 🔹 Features

- **Live Temperature Monitoring**  
  See real-time readings from your thermostat.

- **Manual & Schedule Setpoints**  
  Keep track of your manual adjustments and programmed schedules, change manual temperature.

- **Boost Control**  
  Display boost mode state (`ON` / `OFF`) and remaining boost time in minutes, change boost temperature.

- **Hysteresis Values**  
  Monitor high and low hysteresis settings for precise temperature control.

- **Relay & Function Status**  
  Know the current relay state (`ON` / `OFF`) and the function (`HEATING`, `COOLING`) of your thermostat.

- **Fully Coordinated Sensors**  
  All data is updated every minute via the integrated data coordinator for a smooth experience.

---

## ⚡ Installation via HACS

1. Open **HACS** in your Home Assistant instance.  
2. Click on **Integrations**.  
3. Click the **three dots** in the top right corner.  
4. Select **Custom repositories**.  
5. Add the repository URL:  https://github.com/Pucur/prosmartsystem-computhermb-ha
6. Select **Integration** as the category.  
7. Click **Add**.  
8. Find **Computherm B / ProSmart System** in the integration list and click **Download**.  
9. **Restart Home Assistant**.  

---

## 📦 Configuration

After restart, go to **Settings → Devices & Services → Add Integration** and select **Computherm B / ProSmart System**.  
Enter your **email** and **password** to link your thermostat.

Once added, your sensors will automatically appear:

| Sensor | Description |
|--------|-------------|
| Temperature | Current room temperature |
| Manual Set Point | Temperature manually set on thermostat |
| Schedule Set Point | Programmed temperature according to schedule |
| Boost Set Point | Temperature set during boost mode |
| Boost Active | Whether boost mode is active (`ON` / `OFF`) |
| Boost Remaining | Time left for boost mode (minutes) |
| Hysteresis High | High hysteresis value |
| Hysteresis Low | Low hysteresis value |
| Relay State | Current relay state (`ON` / `OFF`) |
| Function | Current function of thermostat (HEATING / COOLING / OFF) |

---

## 🌐 Support & Issues

- **Documentation & Updates:** [GitHub Repository](https://github.com/Pucur/prosmartsystem-computhermb-ha)  
- **Report Issues:** [GitHub Issues](https://github.com/Pucur/prosmartsystem-computhermb-ha/issues)  

---

## 🛠️ Requirements

- Home Assistant with HACS installed  
- Wi-Fi thermostat from **Computherm / ProSmart System**  
- Python `requests` library (handled automatically by Home Assistant)

---

Made with ❤️ by **Pucur**
