/*
 * soil-moisture-sensor.chip.c
 * Custom Wokwi chip: simula sensor capacitivo DFRobot SEN0193
 *
 * Mapeo de tensión de salida (AOUT):
 *   Seco  (0%)   |   2.8 V  (ADC 12-bit ≈ 2800)
 *   Mojado(100%) |   1.2 V  (ADC 12-bit ≈ 1200)
 *
 * El control deslizante "moisture" (0–100) en la UI de Wokwi
 * ajusta la tensión de salida en tiempo real.
 */

#include "wokwi-api.h"
#include <stdlib.h>

typedef struct {
  pin_t    pin_aout;
  uint32_t attr_moisture;
} chip_state_t;

static void write_output(chip_state_t *chip) {
  uint32_t moisture = attr_read(chip->attr_moisture);
  /* seco=0% → 2.8V, mojado=100% → 1.2V (inverso: más agua = menos tensión) */
  float voltage = 2.8f - (moisture / 100.0f) * 1.6f;
  pin_dac_write(chip->pin_aout, voltage);
}

static void timer_cb(void *user_data) {
  write_output((chip_state_t *)user_data);
}

void chip_init(void) {
  chip_state_t *chip = malloc(sizeof(chip_state_t));

  chip->pin_aout      = pin_init("AOUT", ANALOG);
  chip->attr_moisture = attr_init("moisture", 45);

  write_output(chip);

  const timer_config_t cfg = {
    .callback  = timer_cb,
    .user_data = chip,
  };
  timer_t t = timer_init(&cfg);
  timer_start(t, 100000, true);   /* actualiza cada 100 ms */
}
