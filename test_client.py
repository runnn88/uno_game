from infrastructure.network.client import GameClient

def on_message(msg):
    print("RECEIVED:", msg.type, msg.payload)

c = GameClient(on_message)
c.connect("127.0.0.1", 5051)
c.create_room("test")

input("Press Enter to exit...\n")