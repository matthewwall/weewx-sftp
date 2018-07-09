# weewx-sftp

Upload data using sftp


Installation

1) Download the generator

```
wget -O weewx-sftp.zip https://github.com/matthewwall/weewx-sftp/archive/master.zip
```

2) Install the generator

```
sudo wee_extension --install weewx-sftp.zip
```

3) Set the SFTP parameters in the weewx configuration file

```
[StdReport]
    [[SFTP]]
        skin = sftp
        user = username
        password = password
        server = host.example.com
        port = 2222
        path = /weewx
```

4) Re-start weewx

```
sudo /etc/init.d/weewx start
```
