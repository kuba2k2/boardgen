# Copyright (c) Kuba Szczodrzyński 2022-06-15.

from enum import IntFlag


class PinFeatures(IntFlag):
    PIN_NONE = 1 << 0
    PIN_GPIO = 1 << 1
    PIN_IRQ = 1 << 2
    PIN_PWM = 1 << 3
    PIN_ADC = 1 << 4
    PIN_DAC = 1 << 5
    PIN_I2C = 1 << 6
    PIN_I2S = 1 << 7
    PIN_JTAG = 1 << 8
    PIN_SPI = 1 << 9
    PIN_SWD = 1 << 10
    PIN_UART = 1 << 11
