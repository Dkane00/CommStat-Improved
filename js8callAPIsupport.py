from socket import socket, AF_INET, SOCK_DGRAM
import json
import time

TYPE_STATION_SETGRID = 'STATION.SET_GRID'
TYPE_TX_SETMESSAGE = 'TX.SET_TEXT'
TYPE_TX_SEND = 'TX.SEND_MESSAGE'
TYPE_GET_CALL_ACTIVITY = "RX.GET_CALL_ACTIVITY"
TYPE_WINDOWRAISE = 'WINDOW.RAISE'
TXT_ALLCALLGRID = '@APRSIS GRID '
TXT_APRSIS = '@APRSIS'
TYPE_STATION_GETCALLSIGN = 'STATION.GET_CALLSIGN'
STN_SET_INFO = "STATION.SET_INFO"


class js8CallUDPAPICalls:

    def __init__(self, serverip, serverport):
        self.listen = (serverip, serverport)

    def sendMessage(self, messageType, messageText):
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.sock.bind(self.listen)

        content, addr = self.sock.recvfrom(65500)

        try:
            json.loads(content)
        except ValueError:
            pass

        self.reply_to = addr

        if messageType is not None:
            self.send(messageType, messageText)

        self.sock.close()

    def to_message(self, typ, value='', params=None):
        if params is None:
            params = {}
        return json.dumps({'type': typ, 'value': value, 'params': params})

    def send(self, *args, **kwargs):
        params = kwargs.get('params', {})
        if '_ID' not in params:
            params['_ID'] = int(time.time() * 1000)
            kwargs['params'] = params
        message = self.to_message(*args, **kwargs)
        print('sending outgoing message:', message)
        self.sock.sendto(message.encode(), self.reply_to)

    def sendMessageAndClose(self, messageType, messageText):
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.sock.bind(self.listen)

        content, addr = self.sock.recvfrom(65500)

        self.reply_to = addr

        if messageType is not None:
            self.send(messageType, messageText)

        self.sock.close()

    def sendGridToJS8Call(self, gridText, gpsStatus):
        if gpsStatus.startswith('Error'):
            return
        if gridText is None:
            return
        print('Sending Grid to JS8CAll...', gridText)
        self.sendMessageAndClose(TYPE_STATION_SETGRID, gridText)

    def sendInfoToJS8Call(self, string1, string2):
        print('Sending New Callsign Data to JS8CAll INFO Field')
        self.sendMessageAndClose(STN_SET_INFO, string2)

    def sendGridToALLCALL(self, gridText, gpsStatus):
        if gpsStatus.startswith('Error'):
            return
        if gridText is None:
            return
        messageToSend = TXT_ALLCALLGRID + gridText
        print("Sending ", messageToSend)
        self.sendMessageAndClose(TYPE_TX_SEND, messageToSend)