isGateOpen = False

class Gate:
    def changeGatePosition(function):
        if function == 0:
            print("Kapu nyitása")
            isGateOpen = True
        elif function == 1:
            print("Kapu zárása")
            isGateOpen = False
    