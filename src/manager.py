#!/usr/bin/env python
#coding=utf8

import time
import signal
import logging
import tornado.web
from tornado.httpserver import HTTPServer
from tornado.options import define, parse_command_line, options
from bootloader import settings, jinja_environment
from lib.route import Route
import paho.mqtt.client as mqtt
import threading
import json
from handler import IndexmHandler

import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(('8.8.8.8', 80))
ip = s.getsockname()[0]
macMap = {}
macMap['ip'] = ip


define('port', default=8080, type=int)
# mqttHost = '106.14.135.47'
# mqttHost = '192.168.31.223'
mqttHost = ip
print 'mqtthost:%s' % mqttHost
mqttPort = 1883
client_id = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
client = mqtt.Client(client_id)

DEVICE_JOIN = '/device/join'
DEVICE_STATUS = '/device/status'

DEVICE_JOIN_SI = 'gw/90FD9FFFFE19BB86/devicejoined'
COMMAND_SI = 'gw/90FD9FFFFE19BB86/commands'
ZCL_RESP_SI = 'gw/90FD9FFFFE19BB86/zclresponse'
DEVICE_LEAVE_SI = 'gw/90FD9FFFFE19BB86/deviceleft'






class Application(tornado.web.Application):
    def __init__(self):
        self.jinja_env = jinja_environment
        # self.jinja_env.filters.update(register_filters())
        self.jinja_env.tests.update({})
        self.jinja_env.globals['settings'] = settings
        global client
        self.mqttClient = client
        self.macMap = macMap
        # self.memcachedb = memcachedb
        # self.session_store = MemcacheSessionStore(memcachedb)
        
        handlers = [
                    tornado.web.url(r"/style/(.+)", tornado.web.StaticFileHandler, dict(path=settings['static_path']), name='static_path'),
                    tornado.web.url(r"/upload/(.+)", tornado.web.StaticFileHandler, dict(path=settings['upload_path']), name='upload_path')
                    ] + Route.routes()
        tornado.web.Application.__init__(self, handlers, **settings)

# httpApp = Application()

def syncdb():
    pass

def runserver():
    # global httpApp
    http_server = HTTPServer(Application(), xheaders=True)
    # http_server = HTTPServer(httpApp, xheaders=True)
    http_server.listen(options.port)
    
    loop = tornado.ioloop.IOLoop.instance()
    
    def shutdown():
        logging.info('Server stopping ...')
        http_server.stop()
        
        logging.info('IOLoop wil  be terminate in 1 seconds')   
        deadline = time.time() + 1
        
        def terminate():
            now = time.time()
            
            if now < deadline and (loop._callbacks or loop._timeouts):
                loop.add_timeout(now + 1, terminate)
            else:
                loop.stop()
                logging.info('Server shutdown')
        
        terminate()
    
    def sig_handler(sig, frame):
        logging.warn('Caught signal:%s', sig)
        loop.add_callback(shutdown)
    
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)
    
    logging.info('Server running on http://0.0.0.0:%d'%(options.port))
    loop.start()


def startMQTT():

    global client
    # client = mqtt.Client(client_id)  # ClientId不能重复，所以使用当前时间
    # client.username_pw_set("admin", "123456")  # 必须设置，否则会返回「Connected with result code 4」
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(mqttHost, mqttPort, 60)
    client.loop_forever()


def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("test")
    # client.subscribe(DEVICE_JOIN)
    client.subscribe(DEVICE_JOIN_SI)
    # client.subscribe(DEVICE_STATUS)
    client.subscribe(ZCL_RESP_SI)
    client.subscribe(DEVICE_LEAVE_SI)


def getModeId(msg):
    global client
    global macMap
    obj = json.loads(msg)
    nodeId = obj['nodeId']
    mac = obj['deviceEndpoint']['eui64']
    # print macMap
    if not macMap.has_key(mac):
        macMap[mac] = {}
        macMap[mac]['nodeId'] = nodeId
        endPoint = '1'
        cmd1 = '{"commands":[{"commandcli":"zcl global read 0x0000 0x0005"}]}'
        client.publish(COMMAND_SI, cmd1, qos=0, retain=False)
        cmd2 = '{"commands":[{"commandcli":"send %s 1 %s"}]}' % (nodeId, endPoint)
        client.publish(COMMAND_SI, cmd2, qos=0, retain=False)
        macMap[mac]['new'] = True
        macMap[mac]['lightStatus'] = True
    else:
        print 'join replicate'


def addDevice(mac, deviceType):
    global macMap
    msg = {}
    print "start add new device to front end####"
    msg['Action'] = 'ReportJoin'
    msg['DeviceType'] = deviceType
    # msg['Address'] = macMap[mac]['nodeId']
    msg['Address'] = mac
    msgStr = json.dumps(msg)
    print msgStr
    IndexmHandler.send_message(msgStr)
    macMap[mac]['new'] = False


def changeStatus(payload):
    # {"clusterId": "0x0B04", "attributeId": "0x0508", "attributeBuffer": "0x7400",
    #  "attributeDataType": "0x21",
    #  "deviceEndpoint": {"eui64": "0xD0CF5EFFFEF4E4A3", "endpoint": 1}}
    mac = payload['deviceEndpoint']['eui64']
    val = payload['attributeBuffer']
    type = payload['attributeId']
    low = int(val[2:4], 16)
    high = int(val[4:6], 16)*256
    value = float(high + low)
    # 0X0508电流
    # 0X050B功率
    # 0X0505电压
    # 0X0300电量
    if type == '0x0505':
        value = value / 10
    msg = {}
    msg['Address'] = mac
    msg['State'] = value
    msg['type'] = 'socket'
    msg['subType'] = type
    msg['Action'] = 'update'
    msgStr = json.dumps(msg)
    print "change status:%s" % msgStr
    IndexmHandler.send_message(msgStr)


def handleResp(msg):
    global macMap
    obj = json.loads(msg)
    clusterId = None if not obj.has_key("clusterId") else obj["clusterId"]
    if obj.has_key('commandData'):
        print 'zcl parse==='
        mac = obj['deviceEndpoint']['eui64']
        data = obj['commandData']

        if len(data) > 12:
            modelId = data[12:]
            print 'hanlerResp:buf data:%s' % data
            if macMap.has_key(mac) and macMap[mac]['new']:
                if modelId == '53323130302D453831302D31303033':
                    deviceType = '1103'
                    macMap[mac]['deviceType'] = '1103'
                    macMap[mac]['keys'] = ['1', '2', '3']
                    macMap[mac]['isScen'] = False
                    addDevice(mac, deviceType)
                elif modelId == '53323130302D453830392D31303032':
                    deviceType = '1102'
                    macMap[mac]['deviceType'] = '1102'
                    macMap[mac]['keys'] = ['1', '2']
                    macMap[mac]['isScen'] = False
                    addDevice(mac, deviceType)
                elif modelId == '53323130302D453830382D31303031':
                    deviceType = '1101'
                    macMap[mac]['deviceType'] = '1101'
                    macMap[mac]['keys'] = ['1']
                    macMap[mac]['isScen'] = False
                    addDevice(mac, deviceType)
                elif modelId == '53323130302D453831322D35313031':
                    deviceType = '1005'
                    macMap[mac]['deviceType'] = '1005'
                    macMap[mac]['keys'] = ['1']
                    macMap[mac]['isScen'] = False
                    addDevice(mac, deviceType)
                elif modelId == '53323130302D453831332D35313032':
                    deviceType = '1003'
                    macMap[mac]['deviceType'] = '1003'
                    macMap[mac]['keys'] = ['1']
                    macMap[mac]['isScen'] = False
                    addDevice(mac, deviceType)
                elif modelId == '53323130302D453831342D30343031':
                    print "one scenario switch"
                    deviceType = '2001'
                    macMap[mac]['deviceType'] = '2001'
                    macMap[mac]['keys'] = ['1']
                    macMap[mac]['isScen'] = True
                    addDevice(mac, deviceType)
                elif modelId == '53323130302D453831352D30343032':
                    print "two scenario switch"
                    deviceType = '2002'
                    macMap[mac]['deviceType'] = '2002'
                    macMap[mac]['keys'] = ['1', '2']
                    macMap[mac]['isScen'] = True
                    addDevice(mac, deviceType)
                elif modelId == '53323130302D453831362D30343033':
                    print "three scenario switch"
                    deviceType = '2003'
                    macMap[mac]['deviceType'] = '2003'
                    macMap[mac]['keys'] = ['1', '2', '3']
                    macMap[mac]['isScen'] = True
                    addDevice(mac, deviceType)
                elif modelId == '53323130302D453831372D30343034':
                    print "four scenario switch"
                    deviceType = '2004'
                    macMap[mac]['deviceType'] = '2004'
                    macMap[mac]['keys'] = ['1', '2', '3', '4']
                    macMap[mac]['isScen'] = True
                    addDevice(mac, deviceType)
                    # deviceType = '1003'
                    # macMap[mac]['deviceType'] = '1003'
                    # addDevice(mac, deviceType)
                else:
                    print "unknow model id:%s" % modelId
    elif clusterId == '0x0B04':
        changeStatus(obj)
    print macMap
                    # msg = {}
                    # print "start pub new device####"
                    # msg['Action'] = 'ReportJoin'
                    # msg['DeviceType'] = '1103'
                    # # msg['Address'] = macMap[mac]['nodeId']
                    # msg['Address'] = mac
                    # msgStr = json.dumps(msg)
                    # print msgStr
                    # IndexmHandler.send_message(msgStr)
                    # macMap[mac]['new'] = False


def removeDevice(msg):
    # {"eui64": "0xD0CF5EFFFEF4E429"}
    obj = json.loads(msg)
    mac = obj['eui64']
    global macMap
    ret = macMap.pop(mac, False)
    if not ret:
        print 'removeDevice:addree:%s,not found!' % mac
    else:
        frontEnd = {}
        print "remove device to front end####"
        frontEnd['Action'] = 'leave'
        frontEnd['Address'] = mac
        msgStr = json.dumps(frontEnd)
        print msgStr
        IndexmHandler.send_message(msgStr)



def on_message(client, userdata, msg):
    # global macMap
    payload = msg.payload.decode("utf-8")
    print(msg.topic+" : "+payload)
    # IndexmHandler.send_message(msg.payload.decode("utf-8"))
    if(msg.topic == DEVICE_JOIN_SI):
        getModeId(payload)
    elif(msg.topic == DEVICE_LEAVE_SI):
        removeDevice(payload)
    elif(msg.topic == ZCL_RESP_SI):
        handleResp(payload)
    # IndexmHandler.send_message(msg.payload)
    # obj = json.load(msg.payload)


if __name__ == '__main__':
    parse_command_line()
    
    # if options.cmd == 'syncdb':
    #     syncdb()
    # else:
    t = threading.Thread(target=startMQTT)
    t.setDaemon(True)
    t.start()
    # startMQTT()
    runserver()

