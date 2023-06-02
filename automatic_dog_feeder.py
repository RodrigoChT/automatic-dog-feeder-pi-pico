import machine
import utime
import pico_i2c_lcd

#### global variables
button_center_pressed = False
button_right_pressed = False
button_left_pressed = False
feed_ms_ticks_ago = 0

#### lcd display
sda = machine.Pin(0)
scl = machine.Pin(1)
i2c = machine.I2C(0, sda=sda, scl=scl, freq=400000)

i2c_addr     = 0x27
i2c_num_rows = 2
i2c_num_cols = 16

lcd = pico_i2c_lcd.I2cLcd(i2c, i2c_addr, i2c_num_rows, i2c_num_cols)

# custom characters for dog paw
lcd.custom_char(0,bytearray([0x00,0x00,0x03,0x03,0x0C,0x0D,0x03,0x07]))
lcd.custom_char(1,bytearray([0x00,0x00,0x18,0x18,0x06,0x16,0x18,0x1C]))
lcd.custom_char(2,bytearray([0x07,0x03,0x00,0x00,0x00,0x00,0x00,0x00]))
lcd.custom_char(3,bytearray([0x1C,0x18,0x00,0x00,0x00,0x00,0x00,0x00]))

#### real time clock and alarms
rtc = machine.RTC()
alarm_hm_list = [[10,30], [20,30]]
alarm_enabled_list = [False, False]

#### led lights
led_left = machine.Pin(13, machine.Pin.OUT)
led_right = machine.Pin(12, machine.Pin.OUT)

#### servos
# TODO: change led by feeding mechanism
led = machine.Pin(17, machine.Pin.OUT)

#### buttons
button_left = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_DOWN)
button_right = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_DOWN)
button_center = machine.Pin(16, machine.Pin.IN, machine.Pin.PULL_DOWN)

#### helper functions
def wait_pin_activate(pin):
    # wait for pin to activate
    # it needs to be stable for a continuous 20ms
    active = 0
    while active < 20:
        if pin.value() == 1:
            active += 1
            utime.sleep_ms(1)
        else:
            return False
    return True

def datetime_to_hm(datetime_tuple):
    return list(datetime_tuple[4:6])

def hm_to_datetime(hm):
    datetime_list = list(rtc.datetime())
    datetime_list[4] = hm[0]
    datetime_list[5] = hm[1]
    return tuple(datetime_list)

def set_number(initial_value,min_value,max_value,step):
    output_value = initial_value
    output_value += step
    if output_value < min_value:
        output_value = max_value
    elif output_value > max_value:
        output_value = min_value
    return output_value

def set_hm(initial_hm):
    lcd.clear()
    output_hm = initial_hm.copy()
    while True:
        reset_button_presses()
        lcd.move_to(0,0)
        lcd.putstr('Hour: {HH:>02d}'.format(HH=output_hm[0]))
        if button_left_pressed:
            output_hm[0] = set_number(output_hm[0],0,24,-1)
        if button_right_pressed:
            output_hm[0] = set_number(output_hm[0],0,24,1)
        if button_center_pressed:
            break
    while True:
        reset_button_presses()
        lcd.move_to(0,0)
        lcd.putstr('Min.: {MM:>02d}'.format(MM=output_hm[1]))
        if button_left_pressed:
            output_hm[1] = set_number(output_hm[1],0,60,-1)
        if button_right_pressed:
            output_hm[1] = set_number(output_hm[1],0,60,1)
        if button_center_pressed:
            break
    reset_button_presses()
    return output_hm

# TODO: temporary led instead of feeding mechanism        
def feed_dog():
    global feed_ms_ticks_ago
    ticks_ms_now = utime.ticks_ms()
    # avoid feeding multiple times
    if (ticks_ms_now - feed_ms_ticks_ago) > 61000:
        feed_ms_ticks_ago = ticks_ms_now
        lcd.clear()
        lcd.move_to(0,0)
        lcd.putstr('Feeding dog!')
        led.value(1)
        utime.sleep(5)
        led.value(0)
        lcd.clear()

def show_menu(number):
    lcd.move_to(0,0)
    if number == 0:
        lcd.putstr('Feed the dog!')
    elif number == 1:
        lcd.putstr('Adjust clock')
    elif number == 2:
        lcd.putstr('Adjust 1st feed')
    elif number == 3:
        lcd.putstr('Adjust 2nd feed')

def draw_paws():
    lcd.move_to(0,0)
    lcd.putstr(chr(0)+chr(1))
    lcd.move_to(0,1)
    lcd.putstr(chr(2)+chr(3))
    
    lcd.move_to(14,0)
    lcd.putstr(chr(0)+chr(1))
    lcd.move_to(14,1)
    lcd.putstr(chr(2)+chr(3))
    
def draw_time(hm):
    lcd.putstr('{HH:>02d}:{MM:>02d}'.format(HH=hm[0], MM=hm[1]))

#### IRQs
def handle_button_center_pressed(pin):
  if wait_pin_activate(pin):
      global button_center_pressed
      button_center_pressed = True
  
def handle_button_left_pressed(pin):
  if wait_pin_activate(pin):
      global button_left_pressed
      button_left_pressed = True
  
def handle_button_right_pressed(pin):
  if wait_pin_activate(pin):
      global button_right_pressed
      button_right_pressed = True

def reset_button_presses():
  global button_center_pressed
  global button_left_pressed
  global button_right_pressed
  button_center_pressed = False
  button_left_pressed = False
  button_right_pressed = False
  
button_center.irq(trigger=machine.Pin.IRQ_RISING, handler=handle_button_center_pressed)
button_left.irq(trigger=machine.Pin.IRQ_RISING, handler=handle_button_left_pressed)
button_right.irq(trigger=machine.Pin.IRQ_RISING, handler=handle_button_right_pressed)

#### main loop
while True:
    menu = 0
    current_hm = datetime_to_hm(rtc.datetime())
    
    # draw paws
    draw_paws()
    
    # draw time
    lcd.move_to(6,0)
    draw_time(current_hm)
    
    # draw feed times
    lcd.move_to(2,1)
    draw_time(alarm_hm_list[0])
    
    lcd.move_to(9,1)
    draw_time(alarm_hm_list[1])
    
    # check if it's feed time
    active_alarm_hm_list = [x for (x,y) in zip(alarm_hm_list, alarm_enabled_list) if y]
    if current_hm in active_alarm_hm_list:
        feed_dog()
        
    # toggle feeds with side buttons
    if button_left_pressed:
        reset_button_presses()
        if led_left.value() == 0:
            alarm_enabled_list[0] = True
        if led_left.value() == 1:
            alarm_enabled_list[0] = False     
        led_left.toggle()
    if button_right_pressed:
        reset_button_presses()
        if led_right.value() == 0:
            alarm_enabled_list[1] = True
        if led_right.value() == 1:
            alarm_enabled_list[1] = False     
        led_right.toggle()
    
    # menu
    if button_center_pressed:
        reset_button_presses()
        lcd.clear()
        while (menu < 4) and (menu > -1):
            show_menu(menu)
            if button_right_pressed:
                reset_button_presses()
                lcd.clear()
                menu += 1
            if button_left_pressed:
                reset_button_presses()
                lcd.clear()
                menu -= 1
            if button_center_pressed:
                reset_button_presses()
                if menu == 0:
                    feed_dog()
                elif menu == 1:
                    rtc.datetime(hm_to_datetime(set_hm(current_hm)))
                elif menu == 2:
                    alarm_hm_list[0] = set_hm(alarm_hm_list[0])
                elif menu == 3:
                    alarm_hm_list[1] = set_hm(alarm_hm_list[1])
                menu = -1
                    
            utime.sleep_ms(20)
        lcd.clear()
    else:
        utime.sleep(1)