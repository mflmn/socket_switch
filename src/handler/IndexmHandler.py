#!/usr/bin/env python
#coding=utf8

from lib.route import route
from tornado.websocket import WebSocketHandler
from tornado.web import RequestHandler
import json

socket_handlers = set()
JOIN_TOPIC = '/network/join'
COMMAND_TOPIC = '/device/command'

JOIN_TOPIC_SI = 'gw/90FD9FFFFE19BB86/commands'

COMMAND_SI = 'gw/90FD9FFFFE19BB86/commands'


def send_message(message):
    for handler in socket_handlers:
        try:
            handler.write_message(message)
        except:
            print 'websocket msg send error'


@route(r'/', name='indexm') #首页
# class IndexmHandler(AdminBaseHandler):
class IndexmHandler(RequestHandler):

    def get(self):
        self.render('t_index.html')
        # self.render('test.html')


@route(r'/startWS', name='startWS')
class WSHandler(WebSocketHandler):

    def open(self):
        print 'open ws.....'
        global socket_handlers
        socket_handlers.add(self)
        # self.application.mqttClient.publish("test", "ppp MQTT", qos=0, retain=False)
        self.write_message("send ws msg")

    def on_message(self, message):
        print 'recive ws msg ....'
        macMap = self.application.macMap
        print "cache:macMap:%s" % macMap
        for k, v in macMap.items():
            msg = {}
            print "add new device to front end from cache####"
            msg['Action'] = 'ReportJoin'
            msg['DeviceType'] = v['deviceType']
            print "cache:devcie:%s" % v
            msg['Address'] = k
            msgStr = json.dumps(msg)

            self.write_message(msgStr)

    def on_close(self):
        print 'close ws....'

    def check_origin(self, origin):
        return True


@route(r'/join', name='join')
class JoinNetworkHandler(RequestHandler):

    def get(self):
        print "join pub msg"
        joinMsg = '{"commands":[{"command":"plugin network-creator-security open-network","postDelayMs":100}]}'
        self.application.mqttClient.publish(JOIN_TOPIC_SI, joinMsg, qos=0, retain=False)


@route(r'/getDevices', name='getDevices')
class DevicesHandler(RequestHandler):
    def get(self):
        print "getDevices"
        # {"Address": "000D6F0011002B5F", "GroupId": "0",
        #  "EndpointId": "1", "CommandType": "0106",
        #  "Command": {"Type": "1101", "State": "1"}}
        address = self.get_argument("address", None)
        macMap = self.application.macMap
        # macMap = {'0x1111111':{'keys':['1','2','3'], 'isScen':False}}
        # address = '0x%s' % address
        keys = self.getDeviceKeysById(address)
        # print "DevicesHandler:address:%s" % address
        device = []
        for item in macMap.keys():
            isScen = macMap[item]['isScen']
            if not isScen:
                device = device + self.getDeviceKeysById(item)
        # keys = macMap[address]['keys']
        # keys = ['1', '2', '3']
        # for i in range(0, len(keys)):
        #     keys[i] = address + keys[i]
        # print "keys:%s" % keys
        ret = {}
        ret['keys'] = keys
        ret['devices'] = device
        msgStr = json.dumps(ret)
        self.write(ret)
        # cmd = self.get_argument("cmd", None)
        # cmdParse = cmd.split("@")
    def getDeviceKeysById(self, address):
        macMap = self.application.macMap
        # macMap = {'0x1111111': {'keys': ['1', '2', '3']}}
        print "DevicesHandler:address:%s" % address
        keys = [] if not macMap.has_key(address) else macMap[address]['keys']
        # keys = ['1', '2', '3']
        keyList = []
        for i in range(0, len(keys)):
            kStr = address + '@' + keys[i]
            keyList.append(kStr)
        print "keys:%s" % keys
        return keyList


@route(r'/bind', name='bind')
class BindHandler(RequestHandler):
    def get(self):
        print "bind"
        macMap = self.application.macMap
        # {"Address": "000D6F0011002B5F", "GroupId": "0",
        #  "EndpointId": "1", "CommandType": "0106",
        #  "Command": {"Type": "1101", "State": "1"}}
        key = self.get_argument("key", None)
        device = self.get_argument("device", None)

        keyArray = key.split("@")
        scenAddress = keyArray[0][2:]
        scenKey = keyArray[1]
        sIndex = '0x%s' % scenAddress
        sNodeId = macMap[sIndex]['nodeId']

        deviceArray = device.split("@")
        devAddress = deviceArray[0][2:]
        devKey = deviceArray[1]
        devIndex = '0x%s' % devAddress
        devNodeId = macMap[devIndex]['nodeId']
        # ret = {}

        stoDevStr = '{"commands":[{"commandcli":"zdo bind %s %s %s 0x0006 {%s} {%s}"}]}'\
                    % (sNodeId, scenKey, devKey, scenAddress, devAddress)
        print "bind:stodev:%s" % stoDevStr
        self.application.mqttClient.publish(COMMAND_SI, stoDevStr, qos=0, retain=False)
        devToSStr = '{"commands":[{"commandcli":"zdo bind %s %s %s 0x0006 {%s} {%s}"}]}' \
                    % (devNodeId, devKey, scenKey, devAddress, scenAddress)
        print "bind:devtos:%s" % devToSStr
        self.application.mqttClient.publish(COMMAND_SI, devToSStr, qos=0, retain=False)
        # zdo bind 0x151D 1 1 0x0006 {D0CF5EFFFEF4E41F} {D0CF5EFFFEF7315A}
        # ret['keys'] = [1111, 2222, 3333]
        # ret['devices'] = ['a1', 'a2', 'b1']
        # msgStr = json.dumps(ret)
        # self.write(ret)
        led = macMap[sIndex]['lightStatus']
        if led:
            state = '0'
        else:
            state = '1'
        nodeId = sNodeId
        print "bind:led:nodeId:%s" % nodeId
        model1 = '{"commands": [{"commandcli": "zcl mfg-code 0x117B "}]}'
        print "bind:led:model1:%s" % model1
        self.application.mqttClient.publish(COMMAND_SI, model1, qos=0, retain=False)
        model2 = '{"commands": [{"commandcli": "zcl global write 0xFC56 0x0000 0x20 {0%s}"}]}' % state
        print "bind:led:model2:%s" % model2
        self.application.mqttClient.publish(COMMAND_SI, model2, qos=0, retain=False)
        model3 = '{"commands": [{"commandcli": "send %s 1 1"}]}' % nodeId
        print "bind:led:model3:%s" % model3
        self.application.mqttClient.publish(COMMAND_SI, model3, qos=0, retain=False)


@route(r'/unbind', name='unbind')
class UnBindHandler(RequestHandler):
    def get(self):
        print "unbind"
        macMap = self.application.macMap
        key = self.get_argument("key", None)
        device = self.get_argument("device", None)

        keyArray = key.split("@")
        scenAddress = keyArray[0][2:]
        scenKey = keyArray[1]
        sIndex = '0x%s' % scenAddress
        sNodeId = macMap[sIndex]['nodeId']

        deviceArray = device.split("@")
        devAddress = deviceArray[0][2:]
        devKey = deviceArray[1]
        devIndex = '0x%s' % devAddress
        devNodeId = macMap[devIndex]['nodeId']
        # ret = {}
        #zdo unbind unicast sNodeId {scenAddress} scenKey 0x0006 {devAddress} devKey
        stoDevUnStr = '{"commands":[{"commandcli":"zdo unbind unicast %s {%s} %s 0x0006 {%s} %s"}]}'\
                    % (sNodeId, scenAddress, scenKey, devAddress, devKey)
        print "unbind:stodev:%s" % stoDevUnStr
        self.application.mqttClient.publish(COMMAND_SI, stoDevUnStr, qos=0, retain=False)
        devToSUnStr = '{"commands":[{"commandcli":"zdo unbind unicast %s {%s} %s 0x0006 {%s} %s"}]}' \
                    % (devNodeId, devAddress, devKey, scenAddress, scenKey)
        print "unbind:devtos:%s" % devToSUnStr
        self.application.mqttClient.publish(COMMAND_SI, devToSUnStr, qos=0, retain=False)


@route(r'/getDevMethod', name='getDevMethod')
class GetDevMethod(RequestHandler):
    def get(self):
        print "get device method"
        macMap = self.application.macMap
        key = self.get_argument("address", None)

        keyArray = key.split("@")
        op = ['on', 'off']
        opStr = json.dumps(op)

        self.write(opStr)

        # ret = {}
        #zdo unbind unicast sNodeId {scenAddress} scenKey 0x0006 {devAddress} devKey
        # stoDevUnStr = '{"commands":[{"commandcli":"zdo unbind unicast %s {%s} %s 0x0006 {%s} %s"}]}'\
        #             % (sNodeId, scenAddress, scenKey, devAddress, devKey)


@route(r'/createScen', name='createScen')
class CreateScen(RequestHandler):
    def get(self):
        macMap = self.application.macMap
        scen = self.get_argument("scen", None)
        scen = json.loads(scen)
        print "CreateScen method,%s" % scen
        model1 = '{"commands": [{"commandcli": "zcl groups add 0x01 \\"1\\""}]}'
        # self.application.mqttClient.publish(COMMAND_TOPIC, model1, qos=0, retain=False)
        model2 = '{"commands": [{"commandcli": "send %s 1 %s"}]}'
        model3 = '{"commands": [{"commandcli": "zcl scenes add 0x0001 %s 0X0000 \\"%s\\" %s"}]}'
        scenID = None
        scenName = None
        length = len(scen)

        for i in range(0, length):
            scenStr = scen[i]
            cmd = scenStr.split(':')
            opKey = cmd[2]
            if opKey == 'on':
                extensionField = '0x01010006'

            else:
                extensionField = '0x00010006'
            keyStr = ''
            if i == 0:
                keyStr = cmd[0]
                scenParse = keyStr.split('@')
                scenAddress = scenParse[0]
                scenAddr = scenAddress
                sNID = macMap[scenAddress]['nodeId']
                # sNID = sNodeId
                sEID = scenParse[1]
                # sEID = sEndPID
                scenID = '0x0%s' % sEID
                scenName = '%s' % sEID

                keyStr = cmd[1]
                scenParse = keyStr.split('@')
                scenAddress = scenParse[0]
                devAddr = scenAddress
                dNID = macMap[scenAddress]['nodeId']
                # dNID = sNodeId
                dEID = scenParse[1]
                # dEID = sEndPID

                # unbind
                stoDevUnStr = '{"commands":[{"commandcli":"zdo unbind unicast %s {%s} %s 0x0006 {%s} %s"}]}' \
                              % (sNID, scenAddr[2:], sEID, devAddr[2:], dEID)
                print "CreateScen:unbind:stodev:%s" % stoDevUnStr
                self.application.mqttClient.publish(COMMAND_SI, stoDevUnStr, qos=0, retain=False)

                devToSUnStr = '{"commands":[{"commandcli":"zdo unbind unicast %s {%s} %s 0x0006 {%s} %s"}]}' \
                              % (dNID, devAddr[2:], dEID, scenAddr[2:], sEID)
                print "CreateScen:unbind:devtos:%s" % devToSUnStr
                self.application.mqttClient.publish(COMMAND_SI, devToSUnStr, qos=0, retain=False)

                #create scenario
                self.application.mqttClient.publish(COMMAND_SI, model1, qos=0, retain=False)
                sendStr = model2 % (sNID, sEID)
                self.application.mqttClient.publish(COMMAND_SI, sendStr, qos=0, retain=False)
                msgStr = model3 % (scenID, scenName, extensionField)
                self.application.mqttClient.publish(COMMAND_SI, msgStr, qos=0, retain=False)
                self.application.mqttClient.publish(COMMAND_SI, sendStr, qos=0, retain=False)

                self.application.mqttClient.publish(COMMAND_SI, model1, qos=0, retain=False)
                sendStr = model2 % (dNID, dEID)
                self.application.mqttClient.publish(COMMAND_SI, sendStr, qos=0, retain=False)
                msgStr = model3 % (scenID, scenName, extensionField)
                self.application.mqttClient.publish(COMMAND_SI, msgStr, qos=0, retain=False)
                self.application.mqttClient.publish(COMMAND_SI, sendStr, qos=0, retain=False)

            else:
                # keyStr = cmd[1]
                # scenParse = keyStr.split('@')
                # scenAddress = scenParse[0]
                # sNodeId = macMap[scenAddress]['nodeId']
                # sEndPID = scenParse[1]

                keyStr = cmd[1]
                scenParse = keyStr.split('@')
                scenAddress = scenParse[0]
                devAddr = scenAddress
                sNodeId = macMap[scenAddress]['nodeId']
                dNID = sNodeId
                sEndPID = scenParse[1]
                dEID = sEndPID
                print "scen key str:%s" % keyStr

                keyStr = cmd[0]
                scenParse = keyStr.split('@')
                scenAddress = scenParse[0]
                scenAddr = scenAddress
                sNodeId = macMap[scenAddress]['nodeId']
                sNID = sNodeId
                sEndPID = scenParse[1]
                sEID = sEndPID

                # unbind
                stoDevUnStr = '{"commands":[{"commandcli":"zdo unbind unicast %s {%s} %s 0x0006 {%s} %s"}]}' \
                              % (sNID, scenAddr[2:], sEID, devAddr[2:], dEID)
                print "CreateScen:unbind:stodev:%s" % stoDevUnStr
                self.application.mqttClient.publish(COMMAND_SI, stoDevUnStr, qos=0, retain=False)
                devToSUnStr = '{"commands":[{"commandcli":"zdo unbind unicast %s {%s} %s 0x0006 {%s} %s"}]}' \
                              % (dNID, devAddr[2:], dEID, scenAddr[2:], sEID)
                print "CreateScen:unbind:devtos:%s" % devToSUnStr
                self.application.mqttClient.publish(COMMAND_SI, devToSUnStr, qos=0, retain=False)


                #create scenario
                self.application.mqttClient.publish(COMMAND_SI, model1, qos=0, retain=False)
                sendStr = model2 % (dNID, dEID)
                self.application.mqttClient.publish(COMMAND_SI, sendStr, qos=0, retain=False)
                msgStr = model3 % (scenID, scenName, extensionField)
                self.application.mqttClient.publish(COMMAND_SI, msgStr, qos=0, retain=False)
                self.application.mqttClient.publish(COMMAND_SI, sendStr, qos=0, retain=False)

                # keyStr = cmd[0]
                # scenParse = keyStr.split('@')
                # scenAddress = scenParse[0]
                # scenAddr = scenAddress
                # sNodeId = macMap[scenAddress]['nodeId']
                # sNID = sNodeId
                # sEndPID = scenParse[1]
                # sEID = sEndPID
                #
                # # unbind
                # stoDevUnStr = '{"commands":[{"commandcli":"zdo unbind unicast %s {%s} %s 0x0006 {%s} %s"}]}' \
                #               % (sNID, scenAddr, sEID, devAddr, dEID)
                # print "CreateScen:unbind:stodev:%s" % stoDevUnStr
                # self.application.mqttClient.publish(COMMAND_SI, stoDevUnStr, qos=0, retain=False)
                # devToSUnStr = '{"commands":[{"commandcli":"zdo unbind unicast %s {%s} %s 0x0006 {%s} %s"}]}' \
                #               % (dNID, devAddr, dEID, scenAddr, sEID)
                # print "CreateScen:unbind:devtos:%s" % devToSUnStr
                # self.application.mqttClient.publish(COMMAND_SI, devToSUnStr, qos=0, retain=False)


@route(r'/command', name='command')
class CommandHandler(RequestHandler):

    def get(self):
        print "cmd pub msg"
        # {"Address": "000D6F0011002B5F", "GroupId": "0",
        #  "EndpointId": "1", "CommandType": "0106",
        #  "Command": {"Type": "1101", "State": "1"}}
        address = self.get_argument("address", None)
        cmd = self.get_argument("cmd", None)
        cmdParse = cmd.split("@")


        print "address:%s" % address
        msg = {}
        msg['EndpointId'] = cmdParse[1]
        # msg['Address'] = address
        # msg['GroupId'] = '0'
        # msg['CommandType'] = '0106'
        #
        # subCmd = {}
        # subCmd['Type'] = '110' + cmdParse[0]
        # subCmd['State'] = cmdParse[2]
        # msg['Command'] = subCmd
        # msgStr = json.dumps(msg)
        # print "cmd:%s" % msgStr
        # self.application.mqttClient.publish(COMMAND_TOPIC, msgStr, qos=0, retain=False)
        btnType = cmdParse[0]
        state = cmdParse[2]
        address = address[2:]
        if btnType == '4':
            self.led(address, state)
            return

        if btnType == '6':
            self.lockControl(address, state)
            return

        if state == '1':
            cmd = 'on'
        else:
            cmd = 'off'
        # model = '{"commands":[{"command":"zcl on-off %s"},{"command":"plugin device-table send {%s} 0x%s"}]}' % (cmd, address, msg['EndpointId'])


        if msg['EndpointId'] == '0':
            num = int(cmdParse[0]) + 1
            for i in range(1, num):
                model = '{"commands":[{"command":"zcl on-off %s"},{"command":"plugin device-table send {%s} 0x%s"}]}' % (cmd, address, i)
                print "loop:model:%s" % model
                self.application.mqttClient.publish(COMMAND_SI, model, qos=0, retain=False)
        else:
            model = '{"commands":[{"command":"zcl on-off %s"},{"command":"plugin device-table send {%s} 0x%s"}]}' % (cmd, address, msg['EndpointId'])
            print "single:model:%s" % model
            self.application.mqttClient.publish(COMMAND_SI, model, qos=0, retain=False)

    def led(self, address, state):
        macMap = self.application.macMap
        address = '0x%s' % address
        print "led:address:%s" % address
        nodeId = macMap[address]['nodeId']
        print "led:nodeId:%s" % nodeId
        model1 = '{"commands": [{"commandcli": "zcl mfg-code 0x117B "}]}'
        print "led:model1:%s" % model1
        self.application.mqttClient.publish(COMMAND_SI, model1, qos=0, retain=False)
        model2 = '{"commands": [{"commandcli": "zcl global write 0xFC56 0x0000 0x20 {0%s}"}]}' % state
        print "led:model2:%s" % model2
        self.application.mqttClient.publish(COMMAND_SI, model2, qos=0, retain=False)
        model3 = '{"commands": [{"commandcli": "send %s 1 1"}]}' % nodeId
        print "led:model3:%s" % model3
        self.application.mqttClient.publish(COMMAND_SI, model3, qos=0, retain=False)
        if state == '0':
            print "change led to status"
            self.application.macMap[address]['lightStatus'] = True
        else:
            print "change led to location"
            self.application.macMap[address]['lightStatus'] = False

    def lockControl(self, address, state):
        macMap = self.application.macMap
        address = '0x%s' % address
        print "lockControl:address:%s" % address
        nodeId = macMap[address]['nodeId']
        print "lockControl:nodeId:%s" % nodeId
        model1 = '{"commands": [{"commandcli": "zcl mfg-code 0x117B "}]}'
        print "lockControl:model1:%s" % model1
        self.application.mqttClient.publish(COMMAND_SI, model1, qos=0, retain=False)
        model2 = '{"commands": [{"commandcli": "zcl global write 0xFC56 0x0001 0x20 {0%s}"}]}' % state
        print "lockControl:model2:%s" % model2
        self.application.mqttClient.publish(COMMAND_SI, model2, qos=0, retain=False)
        model3 = '{"commands": [{"commandcli": "send %s 1 1"}]}' % nodeId
        print "lockControl:model3:%s" % model3
        self.application.mqttClient.publish(COMMAND_SI, model3, qos=0, retain=False)

