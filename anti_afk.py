import minescript as m
import time

while True:
    m.player_press_forward(True)
    time.sleep(0.5)
    m.player_press_forward(False)
    time.sleep(10)
    m.player_press_backward(True)
    time.sleep(0.5)
    m.player_press_backward(False)
    time.sleep(10)