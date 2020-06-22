import time

loop_start = time.time()
timer_secs = 0
elapsed_secs = 0
elapsed_mins = 0

flash_wind = False

while True:
    timer_secs = time.time() - loop_start
    #print(elapsed_secs)
    if timer_secs > 1:
        if flash_wind == True:
            print("Send Muted Green")
            flash_wind = False
        else:
            print("Send Full Green")
            flash_wind = True

        loop_start = time.time()
        timer_secs = 0
        elapsed_secs = elapsed_secs + 1

        if elapsed_secs == 600:
            print("Its Been 10 Minutes, Update Metars")
            elapsed_mins = elapsed_mins + 1
            elapsed_secs = 0