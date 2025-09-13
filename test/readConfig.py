import configparser

cfg = configparser.ConfigParser()

# test.confから設定を読む
cfg.read("test.conf")


# 設定値をstr型で読み込む
ipaddress = cfg["section1"]["ipaddress"]
print("ipaddress = %s, type = %s" % (ipaddress, type(ipaddress)))

# 設定値をint型で読み込む
port = cfg.getint("section1", "port")
print("port = %d, type = %s" % (port, type(port)))

# 設定値をbool型で読み込む
useSSL = cfg.getboolean("section1", "useSSL")
print("useSSL = %s, type = %s" % (useSSL, type(useSSL)))

# section2から設定値を読み込む。区切り文字は=だけでなく:を使うことも可能。
ipaddress2 = cfg["section2"]["ipaddress"]
print("ipaddress2 = %s, type = %s" % (ipaddress2, type(ipaddress2)))