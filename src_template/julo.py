#!/usr/bin/env python3

# This file is a part of __PROGRAM_NAME__ __PROGRAM_VERSION__
#
# __PROGRAM_COPYRIGHT__ __PROGRAM_AUTHOR__ __PROGRAM_AUTHOR_EMAIL__
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Загрузчик файлов, управляемый файлом, содержащим маркированные
ссылки.

Все отмеченные маркером ссылки загружаются по очереди.
Если файл по ссылке не докачан, то он сохраняется под своим временным
именем. Если файл докачан, то он сохраняется после последнего из
существующих в каталоге под следующим номером. Если после ссылки
задано имя файла, то файл сохраняется под заданным именем. Когда файл
скачан, пользователь уведомляется об этом всплывающим сообщением.
"""

__version__ = '__PROGRAM_VERSION_NO_V__'
__date__ = '__PROGRAM_UPDATE_DATE__'
__author__ = '__PROGRAM_AUTHOR__ __PROGRAM_AUTHOR_EMAIL__'
__license__ = '__PROGRAM_LICENSE__'

# 15.11.2012

import os
import urllib.request
import urllib.error
import re
import subprocess
import io
import hashlib
import xml.etree.ElementTree
import sys

class ConfigFileHandler:
    """Загружает данные из xml-файла."""
    def __init__(self, fname):
        """
        fname      имя файла

        пример:
        ConfigFileHandler('julo.xml')
        """
        self._fname = fname
        self._dct = {}

    def load_config(self):
        #дано    :
        #получить: из xml-файла данные загружены в словарь
        """Загрузить данные из файла."""
        root = xml.etree.ElementTree.parse(self._fname)
        for child in root.iter():
            tag = child.tag
            att = child.attrib
            if tag == 'site':
                self._dct[tag] = att['name']
            if tag == 'urls':
                self._dct[tag] = (att['file'], att['search'],
                                  att['replace'], att['namesep'])
            elif tag == 'notice':
                self._dct[tag] = (att['name'], att['one'],
                                  att['all'])
            elif tag == 'patterns':
                self._dct[tag] = []
            elif tag == 'pattern':
                self._dct['patterns'].append(
                    (att.get('load'), att['start'], att['left'], att['right']))
            elif tag == 'load':
                self._dct[tag] = att['cmd']
            elif tag == 'temp':
                self._dct[tag] = (att['prefix'], att['suffix'],
                                  int(att['random']))
            elif tag == 'final':
                self._dct[tag] = (att['prefix'], att['suffix'])

    def getname(self):
        #дано    :
        #получить: название сайта
        """Имя сайта."""
        return self._dct['site']

    def geturls(self):
        #дано    :
        #получить: ссылки (файл, маркер, маркер замены, разделитель имени)
        """Ссылки (файл, маркер, маркер замены, разделитель имени)."""
        return self._dct['urls']

    def getnotice(self):
        #дано    :
        #получить: уведомления (название, один, все)
        """Уведомления (название, один, все)."""
        return self._dct['notice']

    def getpatterns(self):
        #дано    :
        #получить: список шаблонов [(загрузчик, начало, левый, правый), ...]
        """Список шаблонов [(загрузчик, начало, левый, правый), ...]."""
        return self._dct['patterns']

    def getload(self):
        #дано    :
        #получить: команда с аргументами для загрузки файла
        """Команда с аргументами для загрузки файла.

        Пример:
          curl %url -o %file
          wget %url -O %file
          youtube-dl -c %url -o %file
          yt-dlp -c --proxy socks5://localhost:1080 %url -o %file

        """
        return self._dct['load']

    def gettemp(self):
        #дано    :
        #получить: временное имя (префикс, суффикс, число)
        """Временное имя (префикс, суффикс, число)."""
        return self._dct['temp']

    def getfinal(self):
        #дано    :
        #получить: постоянное имя (префикс, суффикс)
        """Постоянное имя (префикс, суффикс)."""
        return self._dct['final']

class FilesDownloader:
    """Загрузчик файлов по файлу с маркированными ссылками."""
    def __init__(self,
                 urlsfname, marker, rmarker, namesep,
                 notname, notmsg_load_t, notmsg_comp_t,
                 patterns,
                 loadcmd,
                 tmppref, tmpsuf, tmphlen,
                 nxtpref, nxtsuf):
        """
        urlsfname      файл с маркированными ссылками
        marker         маркер в начале ссылки
        rmarker        маркер замены
        namesep        разделитель имени
        notifymsg      сообщение для уведомления
        notname        название уведомителя
        notmsg_load_t  шаблон сообщения для уведомления о загрузке
                       аргумент %file заменяется на имя загруженного файла
        notmsg_comp_t  шаблон сообщения для уведомления о завершении
                       аргументов нет
        patterns       список с загрузчиком и шаблонами (в кортежах):
                         - команда загрузки с аргументом %url
                         - шаблон начала поиска
                         - левый шаблон строки
                         - правый шаблон строки
        loadcmd        команда загрузки с аргументами %url и %file
        tmppref        префикс временного файла
        tmpsuf         суффикс временного файла
        tmphlen        длина последовательности временного файла
        nxtpref        префикс постоянного файла
        nxtsuf         суффикс постоянного файла

        пример:
        FilesDownloader('urls', '*', '[', ' ',
                        'partv', 'loaded', 'complete',
                        [('curl %url', r'Скачать', r'<a href=.', r'. class'),
                         ('curl %url', r'Скачать', r'<a href=.', r'. class')],
                        'curl %url -o %file',
                        'tmp_', '.mp4', 8,
                        't', '.mp4')
        """
        self._urlsfname = urlsfname
        self._marker = marker
        self._rmarker = rmarker
        self._namesep = namesep
        self._notname = notname
        self._notmsg_load_t = notmsg_load_t
        self._notmsg_comp_t = notmsg_comp_t
        self._patterns = patterns
        self._loadcmd = loadcmd
        self._tmppref = tmppref
        self._tmpsuf = tmpsuf
        self._tmphlen = tmphlen
        self._nxtpref = nxtpref
        self._nxtsuf = nxtsuf

    def download_files(self):
        #дано    :
        #получить: по ссылкам с маркером из файла загружены
        #          файлы, загруженные ссылки отмечены другим
        #          маркером
        """Загрузить файлы по маркированным ссылкам из файла, сохраняя
        их под временными, постоянными или фиксированными именами (в
        зависимости от закачанности) и помечая загруженные ссылки
        другим маркером."""
        urlsfname = self._urlsfname
        marker = self._marker
        rmarker = self._rmarker
        namesep = self._namesep
        notname = self._notname
        notmsg_load_t = self._notmsg_load_t
        notmsg_comp_t = self._notmsg_comp_t
        patterns = self._patterns
        loadcmd = self._loadcmd
        tmppref = self._tmppref
        tmpsuf = self._tmpsuf
        tmphlen = self._tmphlen
        nxtpref = self._nxtpref
        nxtsuf = self._nxtsuf

        ufh = UrlsFileHandler(urlsfname, marker, rmarker, namesep)
        url_line = ufh.read_line()
        page = ufh.get_url(url_line)
        fxdname = ufh.get_file(url_line)
        if page:
            print('Start download')
        else:
            print('No urls')
            return
        nh = NoticeHandler(notname, ': ')
        nmh = NoticeMessageHandler()
        nmh.set_complete_config({})
        notmsg_comp = nmh.get_complete_message(notmsg_comp_t)
        while page is not None:
            dirurl = page
            for p in patterns:
                tmpph = PageHandler(dirurl, p[0], p[1], (p[2], p[3]))
                tmpph.start()
                dirurl = tmpph.get_string()
                tmpph.end()
            if not dirurl:
                print('Direct url is not found')
                return
            if fxdname is not None:
                filename = fxdname
            else:
                filename = \
                    NameHandler('', 0).get_next(nxtpref, nxtsuf)
            nmh.set_load_config({'file': filename})
            notmsg_load = nmh.get_load_message(notmsg_load_t)
            dh = DownloadHandler(loadcmd,
                                 dirurl,
                                 (tmppref, tmpsuf, page, tmphlen),
                                 (nxtpref, nxtsuf),
                                 fxdname)
            dh.start()
            dh.download()
            if dh.iscomplete():
                ufh.replace_line(page)
                nh.notify(notmsg_load)
                dh.end()
            else:
                dh.end()
                break
            url_line = ufh.read_line()
            page = ufh.get_url(url_line)
            fxdname = ufh.get_file(url_line)
        if page is None:
            nh.notify(notmsg_comp)

class UrlsFileHandler:
    """Обработчик файла, который может отыскивать маркированные
    строки, маркировать их другим маркером, а также брать
    фиксированное имя файла, если задан разделитель имени файла."""
    def __init__(self, fname, marker, rmarker, namesep):
        """
        fname      имя файла с маркированными строками
        marker     маркер строки
        rmarker    маркер замены
        namesep    разделитель имени

        пример:
        UrlsFileHandler('urls', '*', '[', ' ')
        """
        self._fname = fname
        self._marker = marker
        self._rmarker = rmarker
        self._namesep = namesep

    def read_line(self):
        #дано    :
        #получить: возвращается первая строка, начинающаяся
        #          с маркера (маркер удаляется)
        """Найти первую строку, начинающуюся с маркера."""
        marker = self._marker
        with open(self._fname, encoding='utf-8') as fin:
            for line in fin:
                if line.startswith(marker):
                    return line[len(marker):].strip()

    def get_url(self, string):
        #дано    : строка из файла со ссылками
        #получить: возвращается ссылка из первой строки, начинающейся
        #          с маркера (маркер удаляется)
        """Взять ссылку из строки файла."""
        if string:
            pos = string.find(self._namesep)
            if pos >= 0:
                return string[:pos]
            else:
                return string
        return None

    def get_file(self, string):
        #дано    : строка из файла со ссылками
        #получить: возвращается фиксированное имя файла из первой строки,
        #          начинающейся с маркера, если это имя задано
        """Взять фиксированное имя файла из строки файла."""
        if string:
            pos = string.find(self._namesep)
            if pos >= 0:
                return string[pos+len(self._namesep):]
        return None

    def replace_line(self, s):
        #дано    : задана строка для замены
        #получить: строка, начинающаяся с маркера, найдена,
        #          и маркер заменён на маркер замены
        """Заменить в строке маркер на маркер замены."""
        fname, tfname = self._fname, 'tmpfile'
        marker, rmarker = self._marker, self._rmarker
        with open(fname, encoding='utf-8') as fin, \
             open(tfname, 'w', encoding='utf-8') as fout:
            for line in fin:
                line = line.rstrip()
                if line.startswith(marker) and \
                   line[len(marker):].startswith(s):
                   print('{0}{1}'.format(rmarker, line[len(marker):]),
                         file=fout)
                else:
                    print(line, file=fout)
        os.remove(fname)
        os.rename(tfname, fname)

class PageHandler:
    """Обработчик для отыскивания на странице, загруженной с помощью
    команды загрузки, подстроки, которая находится после начального
    шаблона между левым и правым шаблонами."""
    def __init__(self, baseurl, loadcmd, startre, substrre=()):
        """
        baseurl     ссылка на страницу
        loadcmd     команда загрузки страницы с аргументом %url
                    при значении None используется команда по умолчанию
        startre     шаблон начала поиска
        substrre    левый и правый шаблоны строки

        пример:
        PageHandler('http://site/page',
                    'curl %url',
                    r'Скачать',
                    (r'<a href=.', r'. class'))
        """
        self._baseurl = baseurl
        self._loadcmd = loadcmd
        self._startre = startre
        self._substrre = substrre
        self._stream = None
        self._charset = None

    def start(self):
        #дано    :
        #получить: страница открыта
        """Начать работу, открыв страницу."""
        if self._loadcmd is None:
            pdl = PageDefaultLoader()
            pdl.open_stream(self._baseurl)
            self._stream = pdl.get_stream()
            self._charset = pdl.get_charset()
        else:
            pcl = PageCmdlineLoader(self._loadcmd)
            pcl.open_stream(self._baseurl)
            self._stream = pcl.get_stream()
            self._charset = pcl.get_charset()

    def get_string(self):
        # дано    :
        # получить: найдена подстрока после начала поиска,
        #           находящаяся между левым и правым шаблонами
        """Получить строку со страницы, подходящую под заданные шаблоны."""
        startpat = self._startre
        substrpat = '(?P<substr>.+?)'.join(self._substrre)
        searchflag = False
        for line in self._stream:
            linedec = line.decode(self._charset)
            if not searchflag:
                if re.search(startpat, linedec):
                    searchflag = True
            if searchflag:
                match = re.search(substrpat, linedec)
                if match is not None:
                    return match.group('substr')

    def end(self):
        #дано    :
        #получить: страница закрыта
        """Закончить работу, закрыв страницу."""
        self._stream.close()

class PageDefaultLoader:
    """Загрузчик страницы, который загружает страницу через встроенные
    средства."""
    def __init__(self):
        self._stream = None
        self._charset = None

    def open_stream(self, url):
        #дано    : ссылка на страницу
        #получить: открыт поток для чтения страницы и
        #          кодировка страницы установлена
        """Открыть поток для чтения страницы и установить кодировку
        страницы."""
        self._stream = urllib.request.urlopen(url)
        mo = re.search(r'charset=([a-z0-9-]+)',
                       self._stream.getheader('Content-Type'),
                       re.I)
        if mo is not None:
            self._charset = mo.group(1)
        else:
            self._charset = 'latin1'

    def get_stream(self):
        #дано    :
        #получить: поток для чтения страницы
        """Получить поток для чтения страницы."""
        return self._stream

    def get_charset(self):
        #дано    :
        #получить: кодировка для чтения страницы
        """Получить сохранённую кодировку страницы."""
        return self._charset

class PageCmdlineLoader:
    """Загрузчик страницы, который загружает страницу через внешний
    процесс."""
    def __init__(self, cmd):
        #дано    : внешняя команда в виде шаблона
        #получить: внешняя команда сохранена
        """Сохранить внешнюю команду в виде шаблона.

        cmd  внешняя команда в виде шаблона

        пример:
        PageCmdlineLoader('curl %url')

        """
        self._cmd = cmd
        self._stream = None
        self._charset = None

    def open_stream(self, url):
        #дано    : ссылка на страницу
        #получить: открыт поток для чтения страницы из внешней
        #          команды и кодировка страницы установлена
        """Открыть поток для чтения страницы и установить кодировку
        страницы."""
        clh = CommandLineHandler()
        cmdlst = clh.split(self._cmd)
        for i, string in enumerate(cmdlst):
            if string == '%url':
                cmdlst[i] = url
        p = subprocess.Popen(cmdlst, stdout=subprocess.PIPE)
        self._stream = io.BytesIO(p.communicate()[0])
        self._charset = 'utf-8'

    def get_stream(self):
        #дано    :
        #получить: поток для чтения страницы
        """Получить поток для чтения страницы."""
        return self._stream

    def get_charset(self):
        #дано    :
        #получить: кодировка для чтения страницы
        """Получить сохранённую кодировку страницы."""
        return self._charset

class DownloadHandler:
    """Обработчик для закачивания и сохранения файла."""
    def __init__(self, loadcmd, baseurl, tmpnameinfo, nxtnameinfo, fxdnameinfo):
        """
        loadcmd        команда с аргументами для скачивания
                       "prog %url -o %file"
        baseurl        ссылка на файл
        tmpnameinfo    информация для временного имени файла
                       (prefix, suffix, string, hashlen)
        nxtnameinfo    информация для постоянного имени файла
                       (prefix, suffix)
        fxdnameinfo    информация для фиксированного имени файла
                       filename or None

        пример:
        DownloadHandler('curl %url -o %file',
                        'http://file',
                        ('tmp', '.mp4', 'string', 8),
                        ('nxt', '.mp4'),
                        'file12345.mp4')

        """
        self._loadcmd = loadcmd
        self._baseurl = baseurl
        self._tmpnameinfo = tmpnameinfo
        self._nxtnameinfo = nxtnameinfo
        self._fxdnameinfo = fxdnameinfo

    def start(self):
        #дано    :
        #получить: флаг полноты закачки установлен в False
        """Начать работу и установить флаг закачки в False."""
        self._complete = False

    def download(self):
        #дано    :
        #получить: выполнена закачка файла;
        #          если файл не докачан, то у него временное имя;
        #          если файл докачан и у него установлено фиксированное имя,
        #          то у него устанавливается фиксированное имя;
        #          если файл докачан и у него нет фиксированного имени,
        #          то у него устанавливается имя по порядку
        """Закачать файл и сохранить его под временным именем, если
        файл не докачан, либо под фиксированным именем, если задано
        фиксированное имя и файл докачан, либо под именем по порядку,
        если фиксированное имя не задано и файл докачан."""
        tmppref, tmpsuf, s, hlen = self._tmpnameinfo
        nxtpref, nxtsuf = self._nxtnameinfo
        fxdconfig = self._fxdnameinfo
        nh = NameHandler(s, hlen)
        tmpname = nh.get_tmp(tmppref, tmpsuf)
        nxtname = nh.get_next(nxtpref, nxtsuf)
        fxdname = nh.get_fixed(fxdconfig)
        lh = LoadHandler(self._loadcmd, self._baseurl)
        if lh.download(tmpname):
            if fxdname is None:
                os.rename(tmpname, nxtname)
            else:
                os.rename(tmpname, fxdname)
            self._complete = True

    def iscomplete(self):
        #дано    :
        #получить: возвращается признак полноты закачки True/False
        """Возвратить признак полноты закачки True/False."""
        return self._complete

    def end(self):
        #дано    :
        #получить:
        """Завершить работу, ничего не делая."""
        pass

class NameHandler:
    """Создатель файловых имён: временного и следующего за
    существующим в каталоге."""
    def __init__(self, hs, hlen):
        """
        hs      строка для формирования последовательности
                временного имени
        hlen    длина последовательности временного имени

        пример:
        NameHandler('string', 8)

        """
        self._hs = hs
        self._hlen = hlen

    def get_tmp(self, pref, suf):
        #дано    : заданы префикс и суффикс имени
        #получить: возвращается имя временного файла, состоящее из
        #          префикс+число+суффикс, где число сформировано
        #          из строки
        """Создать временное имя в виде префикс+число+суффикс, где
        число формируется из строки."""
        shash = hashlib.md5(self._hs.encode('utf-8')).hexdigest()
        return '{0}{1}{2}'.format(pref, shash[:self._hlen], suf)

    def get_next(self, pref, suf):
        #дано    : заданы префикс и суффикс имени
        #получить: возвращается имя следующего файла в каталоге,
        #          состоящее из префикс+номер+суффикс, где номер
        #          является следующим за найденным в каталоге
        #          (1 - номер по умолчанию)
        """Возвратить имя следующего файла в виде префикс+номер+суффикс,
        где номер является следующим за найденным в каталоге
        (1 - номер по умолчанию)."""
        escpref, escsuf = re.escape(pref), re.escape(suf)
        pat = re.compile(r'{0}(\d+){1}'.format(escpref, escsuf))
        files = tuple(filter(pat.match, os.listdir('.')))
        if not files:
            name = '{0}1{1}'.format(pref, suf)
        else:
            n = max(int(pat.match(i).group(1)) for i in files)
            name = '{0}{1}{2}'.format(pref, n + 1, suf)
        return name

    def get_fixed(self, string):
        #дано    : задана строка с фиксированным именем
        #получить: возвращается фиксированное имя файла или ничего
        """Создать фиксированное имя файла, где фиксированное имя
        равно строке, либо вернуть пустоту."""
        if string:
            return string
        else:
            return None

class LoadHandler:
    """Загрузчик файла через команду общего вида."""
    def __init__(self, loadcmd, baseurl):
        """
        loadcmd    команда с аргументами для скачивания
                   "prog %url -o %file"
        baseurl    ссылка на файл

        Пример:

        LoadHandler('curl %url -o %file', 'http://file')

        """
        def prepare_url(url):
            if url.startswith('//'):
                out = 'http:' + url
            else:
                out = url
            return out
        self._loadcmd = loadcmd
        self._baseurl = prepare_url(baseurl)

    def download(self, save_name=None):
        #дано    : задано имя файла или имя по умолчанию
        #получить: ссылка скачана (с выводом скачивания на экран),
        #          файл сохранён с заданным именем
        #          (по умолчанию - под своим);
        #          возвращает True/False в зависимости от
        #          скачанности файла
        """Скачать файл по ссылке, сохранив под заданным именем.
        Если имя не задано, то сохранить под неизвестным именем."""
        clh = CommandLineHandler()
        cmdlst = clh.split(self._loadcmd)
        for i, string in enumerate(cmdlst):
            if string == '%url':
                cmdlst[i] = self._baseurl
            if string == '%file':
                if save_name:
                    cmdlst[i] = save_name
                else:
                    cmdlst[i] = 'unknown_' + self._baseurl
        try:
            p = subprocess.Popen(cmdlst)
            p.wait()
        except KeyboardInterrupt:
            return False
        return p.returncode == 0

class CommandLineHandler:
    """Обработчик командной строки с аргументами."""
    def split(self, s):
        #дано    : командная строка с аргументами
        #получить: список аргументов, разделённых по пробелам,
        #          исключая пробелы в двойных и в одинарных кавычках
        """Разделить командную строку на аргументы с учётом того, что
        пробелы могут находиться в аргументах в двойных и в одинарных
        кавычках, а также быть экранированными с помощью бэкслеша."""
        out = []
        arg = ''
        state = 'start'
        for ch in s:
            if state == 'start':
                if ch == ' ':
                    state = 'spaces'
                elif ch == '"':
                    state = 'dquote'
                elif ch == "'":
                    state = 'squote'
                else:
                    arg += ch
                    state = 'normal'
            elif state == 'normal':
                if ch == ' ':
                    if arg:
                        out.append(arg)
                    arg = ''
                    state = 'spaces'
                    continue
                elif ch == '"':
                    state = 'dquote'
                elif ch == "'":
                    state = 'squote'
                elif ch == '\\':
                    arg += ch
                    state = 'bslash normal'
                else:
                    arg += ch
            elif state == 'spaces':
                if ch == ' ':
                    continue
                if ch == '"':
                    state = 'dquote'
                elif ch == '\'':
                    state = 'squote'
                elif ch == '\\':
                    state = 'bslash normal'
                    arg = ch
                else:
                    arg = ch
                    state = 'normal'
            elif state == 'dquote':
                if ch == '"':
                    out.append(arg)
                    arg = ''
                    state = 'normal'
                    continue
                elif ch == '\\':
                    state = 'bslash dquote'
                arg += ch
            elif state == 'squote':
                if ch == '\'':
                    out.append(arg)
                    arg = ''
                    state = 'normal'
                    continue
                elif ch == '\\':
                    state = 'bslash squote'
                arg += ch
            elif state == 'bslash normal':
                arg += ch
                state = 'normal'
            elif state == 'bslash dquote':
                arg += ch
                state = 'dquote'
            elif state == 'bslash squote':
                arg += ch
                state = 'squote'
        if arg:
            out.append(arg)
        return out

class NoticeHandler:
    """Уведомитель, выводящий сообщение пользователю."""
    def __init__(self, name, sep):
        """
        name    название уведомителя
        sep     разделитель между названием и сообщением

        пример:
        NoticeHandler('notifier', ': ')

        """
        self._name = name
        self._sep = sep

    def notify(self, s):
        #дано    : задана строка s
        #получить: выведено сообщение name+sep+s
        cmdlst = ['kdialog', '--passivepopup',
                  '{0}{1}{2}'.format(self._name, self._sep, s)]
        subprocess.call(cmdlst)

class NoticeMessageHandler:
    def __init__(self):
        self._load_config = {}
        self._complete_config = {}

    def set_load_config(self, config):
        self._load_config = config

    def set_complete_config(self, config):
        self._complete_config = config

    def get_load_message(self, template):
        out = template
        dct = self._load_config
        prev = None
        while prev != out:
            prev = out
            for k, v in dct.items():
                out = out.replace('%' + k, v)
            prev = out
        return out

    def get_complete_message(self, template):
        out = template
        dct = self._complete_config
        prev = None
        while prev != out:
            for k, v in dct.items():
                out = out.replace('%' + k, v)
            prev = out
        return out

if __name__ == '__main__':
    if len(sys.argv) > 1:
        cfname = sys.argv[1]
    else:
        cfname = 'julo.xml'
    if not os.path.exists(cfname):
        print(
            'Config file is not found: {}'.format(cfname),
            file=sys.stderr
        )
        sys.exit(1)
    cfh = ConfigFileHandler(cfname)
    cfh.load_config()
    assert cfh.getname(), 'The site name is empty'
    print('Load config...', cfh.getname())
    ufname, marker, rmarker, namesep = cfh.geturls()
    nname, nload, ncomp = cfh.getnotice()
    patterns = cfh.getpatterns()
    loadcmd = cfh.getload()
    tpref, tsuf, tlen = cfh.gettemp()
    npref, nsuf = cfh.getfinal()
    fd = FilesDownloader(ufname, marker, rmarker, namesep,
                         nname, nload, ncomp,
                         patterns,
                         loadcmd,
                         tpref, tsuf, tlen,
                         npref, nsuf)
    fd.download_files()
