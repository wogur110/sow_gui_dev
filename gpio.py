import RPi.GPIO as GPIO
import time

def control_relay(gpio_number: int, buzzer_gpio: int, state: bool, mode: str = 'BCM'):
    """
    Control a relay connected to the specified GPIO pin and activate a buzzer for 1 second.
    
    Parameters:
    gpio_number (int): The GPIO pin number for the relay.
    buzzer_gpio (int): The GPIO pin number for the buzzer.
    state (bool): Desired state of the relay (True for ON/LOW, False for OFF/HIGH).
    mode (str): GPIO pin numbering mode ('BCM' or 'BOARD').
    """
    # Set up GPIO mode
    if mode == 'BCM':
        GPIO.setmode(GPIO.BCM)
    elif mode == 'BOARD':
        GPIO.setmode(GPIO.BOARD)
    else:
        raise ValueError("Invalid mode. Use 'BCM' or 'BOARD'.")

    # Set up the GPIO pins as outputs
    GPIO.setup(gpio_number, GPIO.OUT)
    GPIO.setup(buzzer_gpio, GPIO.OUT)

    try:
        # Control the relay
        if state:
            GPIO.output(gpio_number, GPIO.LOW)  # Relay ON
            print(f"GPIO {gpio_number}: Relay ON (LOW)")
        else:
            GPIO.output(gpio_number, GPIO.HIGH)  # Relay OFF
            print(f"GPIO {gpio_number}: Relay OFF (HIGH)")

        # Activate the buzzer
        GPIO.output(buzzer_gpio, GPIO.HIGH)  # Turn on the buzzer
        time.sleep(1)  # Buzzer on for 1 second
        GPIO.output(buzzer_gpio, GPIO.LOW)   # Turn off the buzzer
        print(f"Buzzer {buzzer_gpio}: Activated for 1 second")

    except KeyboardInterrupt:
        print("Operation interrupted by user.")
    finally:
        GPIO.cleanup()
        print("GPIO cleaned up.")

if __name__ == '__main__':
    # Example usage:
    control_relay(18, 23, True)  # Turn the relay ON, buzzer on GPIO 23
    control_relay(18, 23, False) # Turn the relay OFF, buzzer on GPIO 23
