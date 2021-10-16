import board
import neopixel

pixels = neopixel.NeoPixel(board.D18, 72, brightness=0.3, auto_write=False)

pixels.show()   # Initializes all NeoPixels to "off"

def verify_integer(case):
    try:
        case = int(case)
    except ValueError:
        print("** Enter a number only. **")
        prompt()
    else:
        choose_function(case)
        
def clear_pixels():
    color = [0, 0, 0]
    pixels.fill(color)

def pixels_pulse():
    try:
        while True:
            color = [0, 0, 0]
            step = 4
            for i in range(0,255,step): 
                color[0] = i
                pixels.fill(color)
                pixels.show()
    except KeyboardInterrupt:
        color[0] = 0
        pixels.fill(color)
        
def choose_function(case):
    clear_pixels()
    if case == 1: # Turns all pixels one color (red.)
        print_status(case)
        for i in range(len(pixels)):
            pixels[i] = (255, 0, 0)
    elif case == 2: # Alternative method to turn all pixels one color (red.)
        print_status(case)
        pixels.fill([255, 0, 0])
    elif case == 3: # Turn one pixel (in this case, the first pixel) red.
        print_status(case)
        pixels[0] = (255, 0, 0)
    elif case == 4: #Turn the first pixel of each 24-LED NeoPixel ring one color (red.)
        print_status(case)
        for i in range(0, len(pixels), 24):
            pixels[i] = (255, 0, 0)
    elif case == 5:
        print_status(case)
        pixels_pulse()
    elif case == 6:
        print_status(case)
        pixels.show()
    else:
        print("** Case not found. **")
    pixels.show()
    prompt()
    
def print_status(case):
    msg = "Function " + str(case) + " should be running..."
    print(msg)
    
def prompt():
    case = input("Choose a function: ")
    verify_integer(case)

instructions = """
    Enter the number of the function you'd like to run:
    
    1: Turns all pixels one color (red).
    2: (DISABLED) Alternative method to turn all pixels one color (red).
    3: Turn one pixel one color (in this case, turn the first pixel red.)
    4: Turn the first pixel of each 24-LED NeoPixel ring one color (red).
    5: Pulse all pixels one color (red).
    6: Clear all pixels.
    """

print(instructions)

prompt()
