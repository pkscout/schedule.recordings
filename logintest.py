from urllib.request import urlopen,Request
import json
import sys


ip = "127.0.0.1"
port = 8866
pin = "0000"
sid = ""

def doRequest5(method, isJSON = True):
    retval = False
    getResult = None
    url = "http://" + ip + ":" + str(port) + '/service?method=' + method
    if (not 'session.initiate' in method):
        url += '&sid=' + sid
    print(url)
    try:
        request = Request(url, headers={"Accept" : "application/json"})
        json_file = urlopen(request)
        getResult = json.load(json_file)
        json_file.close()
        retval = True
    except Exception as e:
        print(str(e))
    print(getResult)
    return retval, getResult

def hashMe (thedata):
    import hashlib
    h = hashlib.md5()
    h.update(thedata.encode('utf-8'))
    return h.hexdigest()


def  sidLogin5():
    method = 'session.initiate&ver=1.0&device=emby'
    ret, keys = doRequest5(method)
    global sid
    if ret == True:
        sid =  keys['sid']
        salt = keys['salt']
        method = 'session.login&md5=' + hashMe(':' + hashMe(pin) + ':' + salt)
        ret, login  = doRequest5(method)
        if ret and login['stat'] == 'ok':
            sid =  login['sid']
        else:
            print ("Fail")
    else:
        print ("Fail")

def main(method):
    sidLogin5()
    doRequest5(method)

if __name__== "__main__":
    main(sys.argv[1])