# Copyright (c) Mathias Kaerlev 2013-2017.
#
# This file is part of cuwo.
#
# cuwo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cuwo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with cuwo.  If not, see <http://www.gnu.org/licenses/>.

"""
Utilities for downloading Cube World package files from Picroma

Useful for downloading the terraingen dependencies
"""

import urllib.request
from urllib.error import HTTPError
import xml.dom.minidom
import zlib
import getpass
import os
import sys
import hashlib


VALIDATE_URL = 'https://picroma.com/cwvalidate/'
BASE_URL = 'https://s3.amazonaws.com/picroma/cwdownload/'
PACKAGE_FILE = BASE_URL + 'package.xml'
FILE_HASHES = {
    'Server.exe': '9c69b731cf197236ce800b44b2abe497',
    'data1.db': '5dd75c4fde12d1d1635e3791e26d22df',
    'data4.db': 'bbcd27346d51f4c7a1cb81e11a9d6fe4'
}


class ValidateError(Exception):
    pass


def download(s):
    return urllib.request.urlopen(s).read()


def validate(email, password, challenge=0):
    url = VALIDATE_URL + '?e={}&p={}&id={:032x}'.format(email, password,
                                                        challenge)
    try:
        download(url)
    except HTTPError:
        return False
    return True


def get_node_value(node, name):
    return node.getElementsByTagName(name)[0].firstChild.nodeValue


def download_package(*files):
    package = download(PACKAGE_FILE)
    doc = xml.dom.minidom.parseString(package.decode())
    result = {}

    for node in doc.getElementsByTagName('file'):
        destination = get_node_value(node, 'destination')
        if destination not in files:
            continue
        source = get_node_value(node, 'source')
        print('Descargando {}'.format(destination))
        data = zlib.decompress(download(BASE_URL + source))
        result[destination] = data

    return result


def get_input(prompt):
    if sys.stdin.isatty():
        return input(prompt)

    old_stdin = sys.stdin
    sys.stdin = open('/dev/tty', 'r')
    ret = input(prompt)
    sys.stdin.close()
    sys.stdin = old_stdin
    return ret


def download_prompt(*files, email=None, password=None):
    if 'TRAVIS' in os.environ:
        # Do not prompt if on Travis.
        return download_package(*files)

    if email and password:
        if not validate(email, password):
            print('Datos de inicio de sesion no validos, omitiendo el paquete.')
            raise ValidateError('Inicio de sesion no valido')
        return download_package(*files)

    print('Inicio de sesion de Picroma (dejar en blanco para omitir el paquete)')

    while True:
        use_email = email or get_input('Correo electronico: ')
        if use_email:
            use_password = password or getpass.getpass()

        if not use_email or not use_password:
            raise ValidateError('Inicio de sesion vacio proporcionado')

        if validate(use_email, use_password):
            break

        print('Datos de inicio de sesion incorrectos, intentelo de nuevo.')

    return download_package(*files)


def get_data_path(name):
    return os.path.join(os.getcwd(), 'data', name)


def check_hash(name, data):
    expected_md5 = FILE_HASHES[name]
    md5 = hashlib.md5(data).hexdigest()
    if md5 == expected_md5:
        return True
    print('MD5 no valido para {}, se esperaba {}, se encontro {}.'.format(
          name, expected_md5, md5))
    return False


def download_dependencies(email=None, password=None):
    names = list(FILE_HASHES.keys())
    download_names = []

    for name in names:
        path = get_data_path(name)
        try:
            with open(path, 'rb') as fp:
                data = fp.read()
            if check_hash(name, data):
                continue
            download_names.append(name)
        except OSError:
            download_names.append(name)

    if not download_names:
        return

    try:
        files = download_prompt(*download_names,
                                email=email, password=password)
    except ValidateError:
        return

    for name, data in files.items():
        if not check_hash(name, data):
            raise NotImplementedError()
        filename = get_data_path(name)
        with open(filename, 'wb') as fp:
            fp.write(data)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Descarga los recursos de Cube World usando una cuenta de Picroma.'
    )
    parser.add_argument('Correo electronico')
    parser.add_argument('Contraseña')
    args = parser.parse_args()
    download_dependencies(args.email, args.password)


if __name__ == '__main__':
    main()
