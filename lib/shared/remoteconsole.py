
import socket;
import sys;
import time;
import lib.shared.timeout as  timeout;
import lib.shared.buffer as buffer;

class RCON(object):
    def __init__(self, address, bindAddr, password):
        self._address = address;
        self._bindAddr = bindAddr;
        self._password = bytes(password, "UTF-8");
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM);
        #self._sock.setblocking(False);
        self._isOpened = False;
        self._bytesSent = 0;
        self._bytesRead = 0;
        self._inBuf = buffer.Buffer();
        self._requestTimeout = timeout.Timeout();
    
    def __del__(self):
        if self._isOpened:
            self.Close();

    def Open(self):
        if not self._isOpened:
            self._inBuf.Drop();
            self._sock.bind((self._bindAddr, 0));
            self._sock.connect(self._address);
            self._sock.settimeout(0.001);
            self._isOpened = True;

    def Close(self):
        if self._isOpened:
            #self._sock.shutdown(socket.SHUT_RDWR);
            self._sock.close();
            self._isOpened = False;

    def Send(self, payload : bytes):
        if self._isOpened:
            l = len(payload);
            sent = 0;
            while sent < l:
                sent += self._sock.send(payload[sent:l]);
            self._bytesSent += sent;

    def Read(self, count = 1024) -> bytes:
        result = b'';
        if self._isOpened:
            while True:
                try:
                    result += self._sock.recv(count);
                except socket.timeout:
                        break;
        self._bytesRead += len(result);
        return result;
    
    def ReadResponse(self, count = 1024, timeout = 1) -> bool:
        bb = b'';
        if self._isOpened:
            isFinished = False;
            timedOut = False;
            self._requestTimeout.Set(timeout);
            while not isFinished or not timedOut:
                if not self._requestTimeout.IsSet():
                    timedOut = True;
                    return False;
                try:
                    bb += self._sock.recv(count);
                    if bb == b'':
                        print("Remote host closed the RCON connection.");
                        self.Close();
                        isFinished = True;
                    else:
                        if self.IsEndMessage(bb):
                            isFinished = True;
                except socket.timeout: # basically read previous recv frame and check if its completed
                    if self.IsEndMessage(bb):
                        isFinished = True;
                        break;
        self._bytesRead += len(bb);
        self._inBuf.Write(bb);
        return True;

    def GetResponse(self) -> bytes:
        result = None;
        if self._inBuf.HasToRead():
            result = bytes(self._inBuf.Read(self._inBuf.GetEffective()));
            self._inBuf.Drop();
        return result;

    def IsEndMessage(self, bt : bytes) -> bool:
        if len(bt) > 0:
            if bt[-1] == 10:
                return True;
        return False;

    # waits for response, ensures delivery
    def Request(self, payload, responseSize = 1024 ) -> bytes:
        result = b'';
        startTime = time.time();
        isOk = False;
        while not isOk:
            self.Send(payload);
            if not self.ReadResponse(responseSize):
                continue;
            else:
                result = self.GetResponse();
                isOk = True;
        print("Request time %f" % (time.time() - startTime));
        return result;

    def SvSay(self, msg):
        if not type(msg) == bytes:
            msg = bytes(msg, "UTF-8")
        if len(msg) > 148: # Message is too big for "svsay".
                        # Use "say" instead.
            return self.Say(msg)
        else:
            return self.Request(b"\xff\xff\xff\xffrcon %b svsay %b" % (self._password, msg));

    def Say(self, msg):
        if not type(msg) == bytes:
            msg = bytes(msg, "UTF-8")
            return self.Request(b"\xff\xff\xff\xffrcon %b say %b" % (self._password, msg));

    def SvTell(self, client, msg):
        if not type(msg) == bytes:
            msg = bytes(msg, "UTF-8")
        if not type(client) == bytes:
            client = str(client)
            client = bytes(client, "UTF-8")
        return self.Request(b"\xff\xff\xff\xffrcon %b svtell %b %b" % (self._password, client, msg));

    def MbMode(self, cmd):
        return self.Request(b"\xff\xff\xff\xffrcon %b mbmode %i" % (self._password, cmd))
    
    def ClientMute(self, player_id):
        return self.Request(b"\xff\xff\xff\xffrcon %b mute %i" % (self._password, player_id))
  
    def ClientUnmute(self, player_id):
        return self.Request(b"\xff\xff\xff\xffrcon %b unmute %i" % (self._password, player_id));

    # untested
    def ClientBan(self, player_ip):
        if not type(player_ip) == bytes:
            player_ip = bytes(player_ip, "UTF-8")
        return self.Request(b"\xff\xff\xff\xffrcon %b addip %b" % (self._password, player_ip))
    
    # untested
    def ClientUnban(self, player_ip):
        if not type(player_ip) == bytes:
            player_ip = bytes(player_ip, "UTF-8")
        return self.Request(b"\xff\xff\xff\xffrcon %b removeip %b" % (self._password, player_ip))


    def ClientKick(self, player_id):
        return self.Request(b"\xff\xff\xff\xffrcon %b clientkick %i" % (self._password, player_id))

    def Echo(self, msg):
        msg = bytes(msg, "UTF-8")
        return self.Request(b"\xff\xff\xff\xffrcon %b echo %b" % (self._password, msg))

    def SetTeam1(self, team):
        team = team.encode()
        return self.Request(b"\xff\xff\xff\xffrcon %b g_siegeteam1 \"%b\"" % (self._password, team))

    def SetTeam2(self, team):
        team = team.encode()
        return self.Request(b"\xff\xff\xff\xffrcon %b g_siegeteam2 \"%b\"" % (self._password, team))

    def SetCvar(self, cvar, val):
        if not type(cvar) == bytes:
            cvar = bytes(cvar, "UTF-8")
        if not type(val) == bytes:
            val = bytes(val, "UTF-8")
        return self.Request(b'\xff\xff\xff\xffrcon %b %b \"%b\"' % (self._password, cvar, val))

    def GetCvar(self, cvar):
        if not type(cvar) == bytes:
            cvar = bytes(cvar, "UTF-8")
        response = self.Request(b"\xff\xff\xff\xffrcon %b %b" % (self._password, cvar))
        if response != None and len(response) > 0:
            response = response.split(b"\"")[1]
            response = response[2:-2].decode("UTF-8", errors="ignore")
        return response

    def SetVstr(self, vstr, val):
        if not type(vstr) == bytes:
            vstr = bytes(vstr, "UTF-8")
        if not type(val) == bytes:
            val = bytes(val, "UTF-8")
        return self.Request(b"\xff\xff\xff\xffrcon %b set %b \"%b\"" % (self._password, vstr, val))

    def ExecVstr(self, vstr):
        if not type(vstr) == bytes:
            vstr = bytes(vstr, "UTF-8") 
        return self.Request(b"\xff\xff\xff\xffrcon %b vstr %b" % (self._password, vstr))

    def GetTeam1(self):
        response = self.Request(b"\xff\xff\xff\xffrcon %b g_siegeteam1" % (self._password))
        response = response.decode("UTF-8", "ignore")
        response = response.removeprefix("print\n\"g_siegeTeam1\" is:")
        response = response.split('"')[1][:-2]
        return response

    def GetTeam2(self):
        response = self.Request(b"\xff\xff\xff\xffrcon %b g_siegeteam2" % (self._password))
        response = response.decode("UTF-8", "ignore")
        response = response.removeprefix("print\n\"g_siegeTeam2\" is:")
        response = response.split('"')[1][:-2]
        return response

    def _mapRestart(self, delay=0):
        """ (DEPRECATED, DO NOT USE) """
        return self.Request(b"\xff\xff\xff\xffrcon %b map_restart %i" % (self._password, delay))

    def MapReload(self, mapName):
        """ USE THIS """
        currMap = mapName
        #self._Send(b"\xff\xff\xff\xffrcon %b mbmode 4" % (self._password))
        return self.Request(b"\xff\xff\xff\xffrcon %b map %b" % (self._password, currMap))

    def GetCurrentMap(self):
        response = self.Request(b"\xff\xff\xff\xffrcon %b mapname" % (self._password))
        response = response.removeprefix(b'\xff\xff\xff\xffprint\n^9Cvar ^7mapname = ^9"^7')
        mapName = response.removesuffix(b'^9"^7\n')
        return mapName

    def ChangeTeams(self, team1, team2, mapName):
        self.SetTeam1(team1)
        self.SetTeam2(team2)
        return self.MapReload(mapName)

    def Status(self):
        res = self.Request(b"\xff\xff\xff\xffrcon %b status notrunc" % (self._password))
        if len(res) == 0:
            return None;
        return res
