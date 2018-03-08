# weewx-sftp

Upload data using sftp


Installation

1) Download the generator

wget -O weewx-sftp.zip https://github.com/matthewwall/weewx-sftp/archive/master.zip

2) Install the generator

sudo wee_extension --install weewx-sftp.zip

3) Add the generator to the skin configuration

[Generators]
    generator_list = user.sftp.SFTPGenerator

4) Add to the weewx configuration

[StdReport]
    [[SFTP]]
        HTML_ROOT = /var/www/html
        skin = sftp
        user = username
        password = password
        server = host.example.com
        port = 2222
        path = /weewx

5) Start weewx

sudo /etc/init.d/weewx start
