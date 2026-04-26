# Node Wiring (MVP)

| Function | Pin |
|---|---|
| I2C SDA | GPIO17 |
| I2C SCL | GPIO18 |
| Sensor rail enable | GPIO7 |
| Soil ADC | GPIO1 |
| Battery ADC | GPIO2 |
| Solar ADC (optional) | GPIO3 |
| RS485 RX/TX | GPIO44/GPIO43 |
| RS485 DE/RE | GPIO42 |

Notes:
- Use waterproof glands and potted cable exits.
- Put BME280 in external radiation shield pod.
- Keep lux and leaf probes on strain-relieved cables.
- Use proper resistor divider scaling for 12V battery/solar channels.
