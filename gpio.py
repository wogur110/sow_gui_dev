import RPi.GPIO as GPIO
import time

def blink_led(gpio_number: int, switch_time: float = 3, mode: str = 'BCM'):
    """
    Blink an LED connected to the specified GPIO pin.
    
    Parameters:
    gpio_number (int): The GPIO pin number.
    switch_time (float): Time in seconds to wait before switching the LED state.
    mode (str): GPIO pin numbering mode ('BCM' or 'BOARD').
    """
    # Set up GPIO mode
    if mode == 'BCM':
        GPIO.setmode(GPIO.BCM)
    elif mode == 'BOARD':
        GPIO.setmode(GPIO.BOARD)
    else:
        raise ValueError("Invalid mode. Use 'BCM' or 'BOARD'.")

    # Set up the GPIO pin as an output
    GPIO.setup(gpio_number, GPIO.OUT)

    # Blink the LED
    try:
            GPIO.output(gpio_number, GPIO.LOW)
            print(f"{gpio_number} : low")
            time.sleep(switch_time)
            GPIO.output(gpio_number, GPIO.HIGH)
            print(f"{gpio_number} : high")
            time.sleep(switch_time)
    except KeyboardInterrupt:
        print("Blinking stopped by user.")
    finally:
        GPIO.cleanup()
        print("GPIO cleaned up.")

if __name__ == '__main__':
    blink_led(18)
