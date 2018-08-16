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

