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

import argparse
import os
import urllib.request
import urllib.error
import re
import subprocess
import io
import hashlib
import xml.etree.ElementTree
import sys

class ConfigFileCreator:
    """Создаёт конфигурационный файл настроек, запрашивая данные у
    пользователя в диалоге и сохраняя их в XML-формате в файле с
    заданным именем.

    """

    def __init__(self, config_file):
        """Принимает имя файла настроек для сохранения в XML-формате
        на диске."""
        self.config_file = config_file
        self._dct = None
        self._dialog = ConfigFileCreationDialog()
        self._xmldoc = ConfigFileXMLBuilder()
        self._disk = ConfigFileDisk()

    def start(self):
        """Начинает создание файла настроек, подготавливая чистые
        структуры для данных.

        """
        self._dct = {}

    def set_site_name(self):
        """Устанавливает имя сайта для вывода на экран через диалог с
        пользователем.

        По умолчанию устанавливает строку Unknown.

        """
        default_name = 'Unknown'
        site_name = self._dialog.ask_site_name(default_name)
        self._dct['site_name'] = site_name

    def set_urls_file(self):
        """Устанавливает элементы файла со ссылками для закачки через
        диалог с пользователем.

        Элементы включают в себя:

        - имя файла (по умолчанию urls)
        - маркер незакачанной ссылки (по умолчанию *)
        - маркер закачанной ссылки (по умолчанию [)
        - разделитель для имени закачанного файла (по умолчанию ' ')

        """
        default_name = 'urls'
        default_search = '*'
        default_replace = '['
        default_namesep = ' '
        urls_file_name = \
            self._dialog.ask_urls_file_name(default_name)
        urls_file_search = \
            self._dialog.ask_urls_file_search(default_search)
        urls_file_replace = \
            self._dialog.ask_urls_file_replace(default_replace)
        urls_file_namesep = \
            self._dialog.ask_urls_file_namesep(default_namesep)
        urls_file = {
            'name': urls_file_name,
            'search': urls_file_search,
            'replace': urls_file_replace,
            'namesep': urls_file_namesep,
        }
        self._dct['urls_file'] = urls_file

    def set_notice_messages(self):
        """Устанавливает элементы уведомлений о закачках через
        диалог с пользователем.

        Элементы включают в себя:

        - имя сайта (по умолчанию unknown)
        - сообщение для одного закачанного файла (по умолчанию "loaded %file")
          сообщение может включать в себя спецификатор %file,
          который заменяется на имя закачанного файла
        - сообщение для последнего закачанного файла (по умолчанию "all loaded")
          сообщение может включать в себя спецификатор %file,
          который заменяется на имя закачанного файла

        """
        default_name = 'unknown'
        default_one = 'loaded %file'
        default_all = 'all loaded'
        notice_messages_name = \
            self._dialog.ask_notice_messages_name(default_name)
        notice_messages_one = \
            self._dialog.ask_notice_messages_one(default_one)
        notice_messages_all = \
            self._dialog.ask_notice_messages_all(default_all)
        notice_messages = {
            'name': notice_messages_name,
            'one': notice_messages_one,
            'all': notice_messages_all,
        }
        self._dct['notice_messages'] = notice_messages

    def set_patterns(self):
        """Устанавливает элементы шаблонов регулярных выражений для
        поиска ссылки на странице через диалог с пользователем.

        Элементы включают в себя:

        - команда для закачки страницы (по умолчанию "curl %url")
          команда может включать в себя спецификатор %url,
          где %url заменяется на ссылку закачки
        - начальный шаблон регулярного выражения для определения
          начала поиска ссылки
        - левый шаблон регулярного выражения для определения
          левой границы ссылки
        - правый шаблон регулярного выражения для определения
          правой границы ссылки

        Если шаблоны регулярных выражений не заполняются в диалоге с
        пользователем, то оставляется пустой список шаблонов.

        """
        patterns = []
        number_of_patterns = 0
        default_load = 'curl %url'
        while self._dialog.ask_patterns_want_add(number_of_patterns):
            pattern_load = self._dialog.ask_pattern_load(default_load)
            pattern_start = self._dialog.ask_pattern_start()
            pattern_left = self._dialog.ask_pattern_left()
            pattern_right = self._dialog.ask_pattern_right()
            pattern = {
                'load': pattern_load,
                'start': pattern_start,
                'left': pattern_left,
                'right': pattern_right,
            }
            self._dialog.print_pattern_total(pattern)
            patterns.append(pattern)
            number_of_patterns += 1
        self._dct['patterns'] = patterns

    def set_load_command(self):
        """Устанавливает команду для закачки файла через диалог с
        пользователем.

        По умолчанию команда "curl %url -o %file"

        Команда может включать в себя спецификаторы %url и %file, где
        %url заменяется на ссылку закачиваемого файла, %file
        заменяется на имя закачиваемого файла.

        """
        default_command = 'curl %url -o %file'
        load_command = self._dialog.ask_load_command(default_command)
        self._dct['load_command'] = load_command

    def set_temp_file_names(self):
        """Устанавливает элементы временных файлов закачек через
        диалог с пользователем.

        Временный файл закачки - это файл, закачка для которого
        началась, но не была завершена и стала отложенной до
        следующего запуска закачки в режиме возобновления закачки.

        Элементы включают в себя:

        - префикс имени (по умолчанию "tmp_")
        - суффикс имени (по умолчанию ".mp4")
        - длину хеш-последовательности в имени файла
          хеш-последовательность строится на основе уникальности
          ссылки на файл и вставляется между префиксом и суффиксом

        """
        default_prefix = 'tmp_'
        default_suffix = '.mp4'
        default_random = '8'
        temp_filenames_prefix = \
            self._dialog.ask_temp_filenames_prefix(default_prefix)
        temp_filenames_suffix = \
            self._dialog.ask_temp_filenames_suffix(default_suffix)
        temp_filenames_random = \
            self._dialog.ask_temp_filenames_random(default_random)
        temp_filenames = {
            'prefix': temp_filenames_prefix,
            'suffix': temp_filenames_suffix,
            'random': temp_filenames_random,
        }
        self._dct['temp_filenames'] = temp_filenames

    def set_final_file_names(self):
        """Устанавливает элементы постоянных файлов закачек через
        диалог с пользователем.

        Постоянный файл закачки - это файл, закачка для которого
        началась или продолжилась и была завершена.

        Элементы включают в себя:

        - префикс имени (по умолчанию "file")
        - суффикс имени (по умолчанию ".mp4")

        """
        default_prefix = 'file'
        default_suffix = '.mp4'
        final_filenames_prefix = \
            self._dialog.ask_final_filenames_prefix(default_prefix)
        final_filenames_suffix = \
            self._dialog.ask_final_filenames_suffix(default_suffix)
        final_filenames = {
            'prefix': final_filenames_prefix,
            'suffix': final_filenames_suffix,
        }
        self._dct['final_filenames'] = final_filenames

    def save_to_file(self):
        """Сохраняет данные в файл настроек, преобразуя их из
        внутреннего формата данных в конечное представление в виде
        XML-данных.

        При сохранении проверяется наличие уже существующего файла
        настроек. Если файл уже существует, то новые данные могут его
        перезаписать, поэтому у пользователя запрашивается
        подтверждение о перезаписи файла. Если пользователь
        соглашается перезаписать файл, файл перезаписывается, иначе
        пользователю предлагается выбрать несколько раз новое имя для
        файла, чтобы не потерять новые установленные данные. Если
        пользователь не перезаписывает файл и не выбирает новое имя
        для файла, то ничего не меняется и старый файл остаётся
        неизменным.

        """
        self._xmldoc.build_header()
        self._xmldoc.build_site(self._dct['site_name'])
        self._xmldoc.build_urls_file(self._dct['urls_file'])
        self._xmldoc.build_notice_messages(self._dct['notice_messages'])
        self._xmldoc.build_patterns(self._dct['patterns'])
        self._xmldoc.build_load_command(self._dct['load_command'])
        self._xmldoc.build_temp_filenames(self._dct['temp_filenames'])
        self._xmldoc.build_final_filenames(self._dct['final_filenames'])
        self._xmldoc.build_footer()
        self._xmldoc.compose_parts()
        text = self._xmldoc.result()
        filename = self._disk.get_file_name(self.config_file)
        if filename is not None:
            self._disk.save(filename, text)

    def end(self):
        """Завершает создание файла настроек, очищая структуры для
        данных.

        """
        self._dct = None

class ConfigFileCreationDialog:
    """Проводит диалоги с пользователем в консоли, используя в
    сообщениях диалогов значения по умолчанию, и возвращая результаты,
    введённые пользователем.

    """

    def __init__(self):
        pass

    def ask_site_name(self, default):
        """Запрашивает у пользователя название сайта, предлагая
        установить значение по умолчанию, если пользователь вводит
        пустую строку.

        Аргументы:

        default -- название сайта по умолчанию

        Возвращается:

        Название сайта, введённое пользователем.
        В случае пустой строки возвращает значение default.

        """
        out = None
        while True:
            print('Tell the site name')
            print('(default: "{}")'.format(default))
            reply = input('> ')
            if reply == '':
                out = default
                print('ok "{}"'.format(default))
                print()
                break
            elif reply:
                out = reply
                print('ok "{}"'.format(reply))
                print()
                break
        return out

    def ask_urls_file_name(self, default):
        """Запрашивает у пользователя имя файла со ссылками на
        закачки, предлагая установить значение по умолчанию, если
        пользователь вводит пустую строку.

        Аргументы:

        default -- имя файла со ссылками на закачки

        Возвращается:

        Имя файла со ссылками на закачки, введённое пользователем.
        В случае пустой строки возвращает значение default.

        """
        out = None
        while True:
            print('Tell the urls file name')
            print('(default: "{}")'.format(default))
            reply = input('> ')
            if reply == '':
                out = default
                print('ok "{}"'.format(default))
                print()
                break
            elif reply:
                out = reply
                print('ok "{}"'.format(reply))
                print()
                break
        return out

    def ask_urls_file_search(self, default):
        """Запрашивает у пользователя маркер закачиваемой ссылки,
        предлагая установить значение по умолчанию, если пользователь
        вводит пустую строку.

        Аргументы:

        default -- маркер закачиваемой ссылки

        Возвращается:

        Маркер закачиваемой ссылки, введённый пользователем.
        В случае пустой строки возвращает значение default.

        """
        out = None
        while True:
            print('Tell the urls file search marker')
            print('(default: "{}")'.format(default))
            reply = input('> ')
            if reply == '':
                out = default
                print('ok "{}"'.format(default))
                print()
                break
            elif reply:
                out = reply
                print('ok "{}"'.format(reply))
                print()
                break
        return out

    def ask_urls_file_replace(self, default):
        """Запрашивает у пользователя маркер закачанной ссылки,
        предлагая установить значение по умолчанию, если пользователь
        вводит пустую строку.

        Аргументы:

        default -- маркер закачанной ссылки

        Возвращается:

        Маркер закачанной ссылки, введённый пользователем.
        В случае пустой строки возвращает значение default.

        """
        out = None
        while True:
            print('Tell the urls file replace marker')
            print('(default: "{}")'.format(default))
            reply = input('> ')
            if reply == '':
                out = default
                print('ok "{}"'.format(default))
                print()
                break
            elif reply:
                out = reply
                print('ok "{}"'.format(reply))
                print()
                break
        return out

    def ask_urls_file_namesep(self, default):
        """Запрашивает у пользователя разделитель имени файла,
        предлагая установить значение по умолчанию, если пользователь
        вводит пустую строку.

        Разделитель имени файла - разделитель, который находится между
        закачиваемой ссылкой и именем файла, под которым скачанный
        файл должен сохраниться.

        Аргументы:

        default -- разделитель имени файла по умолчанию

        Возвращается:

        Разделитель имени файла, введённый пользователем.
        В случае пустой строки возвращает значение default.

        """
        out = None
        while True:
            print('Tell the urls file name separator')
            print('(default: "{}")'.format(default))
            reply = input('> ')
            if reply == '':
                out = default
                print('ok "{}"'.format(default))
                print()
                break
            elif reply:
                out = reply
                print('ok "{}"'.format(reply))
                print()
                break
        return out

    def ask_notice_messages_name(self, default):
        """Запрашивает у пользователя название сайта в уведомлении,
        предлагая установить значение по умолчанию, если пользователь
        вводит пустую строку.

        Уведомление с названием сайта выводится на экран для каждого
        файла, когда файл закачан.

        Аргументы:

        default -- название сайта в уведомлении по умолчанию

        Возвращается:

        Название сайта в уведомлении, введённое пользователем.
        В случае пустой строки возвращает значение default.

        """
        out = None
        while True:
            print('Tell the notice messages name')
            print('(default: "{}")'.format(default))
            reply = input('> ')
            if reply == '':
                out = default
                print('ok "{}"'.format(default))
                print()
                break
            elif reply:
                out = reply
                print('ok "{}"'.format(reply))
                print()
                break
        return out

    def ask_notice_messages_one(self, default):
        """Запрашивает у пользователя сообщение в уведомлении для
        одной закачанной ссылки, предлагая установить значение по
        умолчанию, если пользователь вводит пустую строку.

        Уведомление с сообщением выводится на экран для каждого файла,
        когда файл закачан.

        В уведомлении можно использовать спецификаторы:

        %file -- имя файла, под которым сохранился закачанный файл

        Аргументы:

        default -- сообщение в уведомлении по умолчанию

        Возвращается:

        Сообщение в уведомлении, введённое пользователем.
        В случае пустой строки возвращает значение default.

        """
        out = None
        while True:
            print('Tell the notice messages one file')
            print('(default: "{}")'.format(default))
            reply = input('> ')
            if reply == '':
                out = default
                print('ok "{}"'.format(default))
                print()
                break
            elif reply:
                out = reply
                print('ok "{}"'.format(reply))
                print()
                break
        return out

    def ask_notice_messages_all(self, default):
        """Запрашивает у пользователя сообщение в уведомлении для всех
        закачанных ссылок, предлагая установить значение по умолчанию,
        если пользователь вводит пустую строку.

        Уведомление с сообщением выводится на экран для всех файлов,
        когда все файлы из списка закачиваемых файлов закачаны.

        Аргументы:

        default -- сообщение в уведомлении по умолчанию

        Возвращается:

        Сообщение в уведомлении, введённое пользователем.
        В случае пустой строки возвращает значение default.

        """
        out = None
        while True:
            print('Tell the notice messages all files')
            print('(default: "{}")'.format(default))
            reply = input('> ')
            if reply == '':
                out = default
                print('ok "{}"'.format(default))
                print()
                break
            elif reply:
                out = reply
                print('ok "{}"'.format(reply))
                print()
                break
        return out

    def ask_patterns_want_add(self, number_of_patterns):
        """Запрашивает у пользователя, будет ли пользователь добавлять
        шаблон с регулярными выражениями для поиска ссылки на странице
        для прыжка на следующую страницу или для финальной закачки
        ссылки в файл.

        Пользователь вводит y, n или пустую строку, которая означает
        n. Все другие вводы приводят к повторному вводу.

        Аргументы:

        number_of_patterns -- общее количество шаблонов с регулярными
        выражениями, используемое для вывода пользователю в случае,
        когда пользователь отказался добавлять шаблоны с регулярными
        выражениями

        Возвращается:

        True, если пользователь будет добавлять шаблон с регулярными
        выражениями для поиска ссылки на странице

        False, если пользователь не будет добавлять шаблон с регулярными
        выражениями для поиска ссылки на странице

        """
        out = None
        while True:
            print('Tell whether to add a pattern')
            print('(input y/n, default: n)')
            reply = input('> ')
            if reply == 'y':
                print('ok', 'start to add a pattern')
                out = True
                print()
                break
            elif not reply or reply == 'n':
                print('ok', 'don\'t need pattern')
                tobe = 'is' if number_of_patterns == 1 else 'are'
                ending = '' if number_of_patterns == 1 else 's'
                print(
                    'there {tobe} {} pattern{ending}'
                    .format(
                        number_of_patterns,
                        tobe=tobe,
                        ending=ending
                    )
                )
                out = False
                print()
                break
        return out

    def ask_pattern_load(self, default):
        """Запрашивает у пользователя команду загрузки страницы для
        шаблона с регулярными выражениями, предлагая установить
        значение по умолчанию, если пользователь вводит пустую строку.

        Команда загрузки страницы может иметь спецификатор %url,
        который заменяется в команде на ссылку на страницу.

        Аргументы:

        default -- команда загрузки страницы по умолчанию

        Возвращается:

        Команда загрузки страницы, введённая пользователем.
        В случае пустой строки возвращает значение default.

        """
        out = None
        while True:
            print('Tell the page load command')
            print('(default: "{}")'.format(default))
            reply = input('> ')
            if reply == '':
                out = default
                print('ok "{}"'.format(default))
                print()
                break
            elif reply:
                out = reply
                print('ok "{}"'.format(reply))
                print()
                break
        return out

    def ask_pattern_start(self):
        """Запрашивает у пользователя регулярное выражение начала
        поиска ссылки на странице для шаблона с регулярными
        выражениями.

        Поиск ссылки на странице по левой и правой границе ссылки
        начнётся, начиная с первого символа после подстроки, найденной
        на странице по регулярному выражению начала поиска ссылки.

        В регулярном выражении метасимволы могут быть проэкранированы
        бэкслешем. Например `\(' совпадёт с символом `(' в тексте
        страницы.

        Если пользователь вводит пустую строку, ввод повторяется.

        Возвращается:

        Регулярное выражение начала поиска ссылки, введённое
        пользователем.

        """
        out = None
        while True:
            print('Tell the regexp for start searching url')
            reply = input('> ')
            if reply:
                out = reply
                print('ok "{}"'.format(reply))
                print()
                break
            else:
                print('fail')
                print()
        return out

    def ask_pattern_left(self):
        """Запрашивает у пользователя регулярное выражение левой
        границы ссылки на странице для шаблона с регулярными
        выражениями.

        Ссылка на странице начинается с первого символа после левой
        границы ссылки.

        В регулярном выражении метасимволы могут быть проэкранированы
        бэкслешем. Например `\(' совпадёт с символом `(' в тексте
        страницы.

        Если пользователь вводит пустую строку, ввод повторяется.

        Возвращается:

        Регулярное выражение левой границы ссылки, введённое
        пользователем.

        """
        out = None
        while True:
            print('Tell the regexp for left border of the url')
            reply = input('> ')
            if reply:
                out = reply
                print('ok "{}"'.format(reply))
                print()
                break
            else:
                print('fail')
                print()
        return out

    def ask_pattern_right(self):
        """Запрашивает у пользователя регулярное выражение правой
        границы ссылки на странице для шаблона с регулярными
        выражениями.

        Ссылка на странице продолжается до первого символа правой
        границы ссылки.

        В регулярном выражении метасимволы могут быть проэкранированы
        бэкслешем. Например `\(' совпадёт с символом `(' в тексте
        страницы.

        Если пользователь вводит пустую строку, ввод повторяется.

        Возвращается:

        Регулярное выражение правой границы ссылки, введённое
        пользователем.

        """
        out = None
        while True:
            print('Tell the regexp for right border of the url')
            reply = input('> ')
            if reply:
                out = reply
                print('ok "{}"'.format(reply))
                print()
                break
            else:
                print('fail')
                print()
        return out

    def print_pattern_total(self, pattern):
        """Выводит на экран шаблон с регулярными выражениями,
        включающий в себя: команду загрузки страницы, регулярное
        выражение начала поиска ссылки на странице, регулярное
        выражение левой границы ссылки на странице, регулярное
        выражение правой границы ссылки на странице.

        Аргументы:

        pattern -- шаблон с регулярными выражениями

        """
        fmt = (
            'You entered pattern:\n'
            ' load: "{}"\n'
            'start: "{}"\n'
            ' left: "{}"\n'
            'right: "{}"\n'
        )
        print(fmt.format(
            pattern.get('load'),
            pattern.get('start'),
            pattern.get('left'),
            pattern.get('right'),
        ), end='')
        print()

    def ask_load_command(self, default):
        """Запрашивает у пользователя команду загрузки конечного
        файла, предлагая установить значение по умолчанию, если
        пользователь вводит пустую строку.

        Аргументы:

        default -- команда загрузки конечного файла по умолчанию

        Возвращается:

        Команда загрузки конечного файла, введённая пользователем.
        В случае пустой строки возвращает значение default.

        """
        out = None
        while True:
            print('Tell the load command')
            print('(default: "{}")'.format(default))
            reply = input('> ')
            if reply == '':
                out = default
                print('ok "{}"'.format(default))
                print()
                break
            elif reply:
                out = reply
                print('ok "{}"'.format(reply))
                print()
                break
        return out

    def ask_temp_filenames_prefix(self, default):
        """Запрашивает у пользователя префикс имён временных файлов,
        предлагая установить значение по умолчанию, если пользователь
        вводит пустую строку.

        Временный файл - это файл, который начал скачиваться, но не
        докачан.

        Аргументы:

        default -- префикс имён временных файлов по умолчанию

        Возвращается:

        Префикс имён временных файлов, введённый пользователем.
        В случае пустой строки возвращает значение default.

        """
        out = None
        while True:
            print('Tell the temp filenames prefix')
            print('(default: "{}")'.format(default))
            reply = input('> ')
            if reply == '':
                out = default
                print('ok "{}"'.format(default))
                print()
                break
            elif reply:
                out = reply
                print('ok "{}"'.format(reply))
                print()
                break
        return out

    def ask_temp_filenames_suffix(self, default):
        """Запрашивает у пользователя суффикс имён временных файлов,
        предлагая установить значение по умолчанию, если пользователь
        вводит пустую строку.

        Временный файл - это файл, который начал скачиваться, но не
        докачан.

        Аргументы:

        default -- суффикс имён временных файлов по умолчанию

        Возвращается:

        Суффикс имён временных файлов, введённый пользователем.
        В случае пустой строки возвращает значение default.

        """
        out = None
        while True:
            print('Tell the temp filenames suffix')
            print('(default: "{}")'.format(default))
            reply = input('> ')
            if reply == '':
                out = default
                print('ok "{}"'.format(default))
                print()
                break
            elif reply:
                out = reply
                print('ok "{}"'.format(reply))
                print()
                break
        return out

    def ask_temp_filenames_random(self, default):
        """Запрашивает у пользователя длину хеш-значения в именах
        временных файлов, предлагая установить значение по умолчанию,
        если пользователь вводит пустую строку.

        Временный файл - это файл, который начал скачиваться, но не
        докачан. Хеш-значение в имени временного файла отличает
        временный файл от других временных файлов.

        Аргументы:

        default -- длина хеш-значения в именах временных файлов по
        умолчанию

        Возвращается:

        Длина хеш-значения в именах временных файлов, введённая
        пользователем.
        В случае пустой строки возвращает значение default.

        """
        out = None
        while True:
            print('Tell the temp filenames random length')
            print('(default: "{}")'.format(default))
            reply = input('> ')
            if reply == '':
                out = default
                print('ok "{}"'.format(default))
                print()
                break
            elif reply:
                out = reply
                print('ok "{}"'.format(reply))
                print()
                break
        return out

    def ask_final_filenames_prefix(self, default):
        """Запрашивает у пользователя префикс имён конечных файлов,
        предлагая установить значение по умолчанию, если пользователь
        вводит пустую строку.

        Конечный файл - это файл, который начал скачиваться и
        докачался.

        Аргументы:

        default -- префикс имён конечных файлов по умолчанию

        Возвращается:

        Префикс имён конечных файлов, введённый пользователем.
        В случае пустой строки возвращает значение default.

        """
        out = None
        while True:
            print('Tell the final filenames prefix')
            print('(default: "{}")'.format(default))
            reply = input('> ')
            if reply == '':
                out = default
                print('ok "{}"'.format(default))
                print()
                break
            elif reply:
                out = reply
                print('ok "{}"'.format(reply))
                print()
                break
        return out

    def ask_final_filenames_suffix(self, default):
        """Запрашивает у пользователя суффикс имён конечных файлов,
        предлагая установить значение по умолчанию, если пользователь
        вводит пустую строку.

        Конечный файл - это файл, который начал скачиваться и
        докачался.

        Аргументы:

        default -- суффикс имён конечных файлов по умолчанию

        Возвращается:

        Суффикс имён конечных файлов, введённый пользователем.
        В случае пустой строки возвращает значение default.

        """
        out = None
        while True:
            print('Tell the final filenames suffix')
            print('(default: "{}")'.format(default))
            reply = input('> ')
            if reply == '':
                out = default
                print('ok "{}"'.format(default))
                print()
                break
            elif reply:
                out = reply
                print('ok "{}"'.format(reply))
                print()
                break
        return out

class ConfigFileXMLBuilder:
    """Строит XML-вариант конфигурационного файла в виде XML-файла."""

    def __init__(self):
        self._parts = []
        self._result = None

    def _escape(self, text):
        """Заменяет символы на их названия в виде XML-сущностей.

        Заменяемые символы заменяются следующим образом:

        & заменяется на &amp;
        < заменяется на &lt;
        > заменяется на &gt;
        " заменяется на &quot;

        Аргументы:

        text -- текст, в котором проводится замена символов на
        XML-сущности

        Возвращается:

        Текст из text, в котором заменены символы на XML-сущности.

        """
        text0 = text
        text1 = text0.replace('&', '&amp;')
        text2 = text1.replace('<', '&lt;')
        text3 = text2.replace('>', '&gt;')
        text4 = text3.replace('"', '&quot;')
        out = text4
        return out

    def build_header(self):
        """Строит заголовок XML-файла и добавляет его в хранилище
        частей XML-файла.

        Заголовок XML-файла включает в себя версию XML и кодировку
        XML-файла.

        """
        text = '<?xml version="1.0" encoding="utf-8"?>'
        self._parts.append(text)

    def build_site(self, value):
        """Строит корневой XML-узел с названием сайта и добавляет его
        в хранилище частей XML-файла.

        В XML-узле некоторые символы заменяются на XML-сущности в
        атрибуте имени.

        Аргументы:

        value -- название сайта

        """
        e_value = self._escape(value)
        fmt = '<site name="{name}">'
        text = fmt.format(name=e_value)
        self._parts.append(text)

    def build_urls_file(self, dct):
        """Строит XML-узел с файлом со ссылками для закачки и
        добавляет его в хранилище частей XML-файла.

        В XML-узле некоторые символы заменяются на XML-сущности во
        всех атрибутах.

        Аргументы:

        dct -- набор атрибутов файла со ссылками на закачки, который
        включает в себя: имя файла, маркер закачиваемого файла, маркер
        скачанного файла, разделитель для имени закачанного файла

        """
        e_name = self._escape(dct['name'])
        e_search=self._escape(dct['search'])
        e_replace=self._escape(dct['replace'])
        e_namesep=self._escape(dct['namesep'])
        fmt = (
            '  '
            '<urls '
            'file="{name}" '
            'search="{search}" '
            'replace="{replace}" '
            'namesep="{namesep}" '
            '/>'
        )
        text = fmt.format(
            name=e_name,
            search=e_search,
            replace=e_replace,
            namesep=e_namesep,
        )
        self._parts.append(text)

    def build_notice_messages(self, dct):
        """Строит XML-узел с уведомлениями о процессе скачивания
        файлов и добавляет его в хранилище частей XML-файла.

        В XML-узле некоторые символы заменяются на XML-сущности во
        всех атрибутах.

        Аргументы:

        dct -- набор атрибутов , который включает в себя: имя
        уведомляющего сайта, сообщение для одной успешной закачки и
        сообщение для всех выполненных закачек в списке закачек

        """
        e_name=self._escape(dct['name'])
        e_one=self._escape(dct['one'])
        e_all=self._escape(dct['all'])
        fmt = (
            '  '
            '<notice '
            'name="{name}" '
            'one="{one}" '
            'all="{all}" '
            '/>'
        )
        text = fmt.format(
            name=e_name,
            one=e_one,
            all=e_all,
        )
        self._parts.append(text)

    def build_patterns(self, lst):
        """Строит XML-узел с шаблонами с регулярными выражениями и
        добавляет его в хранилище частей XML-файла.

        В XML-узле некоторые символы заменяются на XML-сущности во
        всех атрибутах.

        Внутри XML-узла с шаблонами с регулярными выражениями
        вставляются отдельные XML-узлы с отдельными шаблонами с
        регулярными выражениями; получается составной XML-узел, внутри
        которого находятся XML-узлы шаблонов с регулярными
        выражениями.

        Аргументы:

        lst -- список шаблонов с регулярными выражениями

        Один шаблон с регулярными выражениями включает в себя: команду
        загрузки страницы со ссылкой, регулярное выражение начала
        поиска ссылки на странице, регулярное выражение левой границы
        ссылки, регулярное выражение правой границы ссылки.

        Если lst пустой, то создаётся пустой XML-узел всех шаблонов и
        добавляется в хранилище частей XML-файла.

        """
        if not lst:
            text = '  <patterns />'
            self._parts.append(text)
        else:
            header = '  <patterns>'
            footer = '  </patterns>'
            fmt = (
                '    '
                '<pattern '
                'load="{load}"\n'
                '             start="{start}"\n'
                '             left="{left}"\n'
                '             right="{right}" '
                '/>'
            )
            self._parts.append(header)
            for i in lst:
                e_load=self._escape(i['load'])
                e_start=self._escape(i['start'])
                e_left=self._escape(i['left'])
                e_right=self._escape(i['right'])
                text = fmt.format(
                    load=e_load,
                    start=e_start,
                    left=e_left,
                    right=e_right,
                )
                self._parts.append(text)
            self._parts.append(footer)

    def build_load_command(self, value):
        """Строит XML-узел с командой загрузки конечного файла и
        добавляет этот XML-узел в хранилище частей XML-файла.

        В XML-узле некоторые символы заменяются на XML-сущности в
        атрибуте имени.

        Аргументы:

        value -- команда загрузки конечного файла

        """
        e_value = self._escape(value)
        fmt = '  <load cmd="{command}" />'
        text = fmt.format(command=e_value)
        self._parts.append(text)

    def build_temp_filenames(self, dct):
        """Строит XML-узел с данными для временных закачиваемых файлов
        и добавляет его в хранилище частей XML-файла.

        В XML-узле некоторые символы заменяются на XML-сущности в
        атрибуте имени.

        Аргументы:

        dct -- данные для временных закачиваемых файлов

        Данные для временных закачиваемых файлов включают в себя:
        префикс имени файла, суффикс имени файла и длину
        хеш-последовательности в имени файла.

        """
        e_prefix=self._escape(dct['prefix'])
        e_suffix=self._escape(dct['suffix'])
        e_random=self._escape(dct['random'])
        fmt = (
            '  '
            '<temp '
            'prefix="{prefix}" '
            'suffix="{suffix}" '
            'random="{random}" '
            '/>'
        )
        text = fmt.format(
            prefix=e_prefix,
            suffix=e_suffix,
            random=e_random,
        )
        self._parts.append(text)

    def build_final_filenames(self, dct):
        """Строит XML-узел с данными для конечных закачанных файлов и
        добавляет его в хранилище частей XML-файла.

        В XML-узле некоторые символы заменяются на XML-сущности в
        атрибуте имени.

        Аргументы:

        dct -- данные для конечных закачанных файлов

        Данные для конечных закачанных файлов включают в себя: префикс
        имени файла, суффикс имени файла.

        """
        e_prefix=self._escape(dct['prefix'])
        e_suffix=self._escape(dct['suffix'])
        fmt = (
            '  '
            '<final '
            'prefix="{prefix}" '
            'suffix="{suffix}" '
            '/>'
        )
        text = fmt.format(
            prefix=e_prefix,
            suffix=e_suffix,
        )
        self._parts.append(text)

    def build_footer(self):
        """Строит подвал XML-файла и добавляет его в хранилище частей
        XML-файла.

        Подвал включает в себя закрывающий XML-тег корневого элемента.

        """
        text = '</site>'
        self._parts.append(text)

    def compose_parts(self):
        """Собирает XML-файл воедино из частей XML-файла, находящихся
        в общем хранилище частей XML-файла.

        """
        self._result = '\n'.join(self._parts)

    def result(self):
        """Возвращает собранный XML-файл с конфигурацией."""
        out = self._result
        return out

class ConfigFileDisk:

    def __init__(self):
        self._dialog = ConfigFileDiskDialog()

    def get_file_name(self, filename):
        out = None
        if os.path.exists(filename):
            out = self._dialog.ask_for_rewrite(filename)
            if out is None:
                out = self._dialog.ask_for_another_filename()
        else:
            out = filename
        return out

    def save(self, filename, text):
        with open(filename, 'w', encoding='utf-8') as fout:
            fout.write(text)
        out = True
        return out

class ConfigFileDiskDialog:

    def __init__(self):
        pass

    def ask_for_rewrite(self, filename):
        out = None
        while True:
            print('You have such file already:', filename)
            print('Do you want to rewrite it?')
            print('(input y/n, default: n)')
            reply = input('> ')
            if reply == 'y':
                print('ok', 'will be rewritten')
                print()
                out = filename
                break
            else:
                print('ok', 'will not change')
                print()
                out = None
                break
        return out

    def ask_for_another_filename(self):
        out = None
        n, maxn = 1, 3
        print(
            'You may choose another file name {} times'
            .format(maxn)
        )
        while n <= maxn:
            print('Input another file name, try #{}:'.format(n))
            print('(input name or leave it empty)')
            reply = input('> ')
            if reply:
                filename = reply
                if os.path.exists(filename):
                    print('fail', 'such file exists already')
                    print()
                else:
                    print('ok', 'new name is set')
                    print()
                    out = filename
                    break
            else:
                break
            n += 1
        if out is None:
            print('ok', 'no new name')
            print()
        return out

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
        out = None
        marker = self._marker
        with open(self._fname, encoding='utf-8') as fin:
            for line in fin:
                if line.startswith(marker):
                    out = line[len(marker):].strip()
                    break
        return out

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
        out = None
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
                    out = match.group('substr')
                    break
        return out

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
        self._complete = None

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
        """Вывести сообщение с помощью внешней программы."""
        cmdlst = ['kdialog', '--passivepopup',
                  '{0}{1}{2}'.format(self._name, self._sep, s)]
        subprocess.call(cmdlst)

class NoticeMessageHandler:
    """Сформировать сообщения одной закачки и всех закачек для вывода
    из шаблонов со спецификаторами."""
    def __init__(self):
        self._load_config = {}
        self._complete_config = {}

    def set_load_config(self, config):
        #дано    : конфигурация спецификаторов
        #получить: конфигурация спецификаторов сохранена
        """Установить конфигурацию спецификаторов для сообщения одной
        закачки.

        пример:
        {'file': 'some_name.mp4'}

        """
        self._load_config = config

    def set_complete_config(self, config):
        #дано    : конфигурация спецификаторов
        #получить: конфигурация спецификаторов сохранена
        """Установить конфигурацию спецификаторов для сообщения всех
        закачек.

        пример:
        {}

        """
        self._complete_config = config

    def get_load_message(self, template):
        #дано    : шаблон сообщения со спецификаторами
        #получить: соообщение после подстановки значений вместо
        #          спецификаторов
        """Сформировать сообщение из шаблона со спецификаторами для
        одной закачки.

        %file  заменить на имя закачанного файла.

        пример:

        'loaded %file' -> 'loaded some_name.mp4'

        """
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
        #дано    : шаблон сообщения со спецификаторами
        #получить: соообщение после подстановки значений вместо
        #          спецификаторов
        """Сформировать сообщение из шаблона со спецификаторами для
        всех закачек.

        в данный момент спецификаторов нет

        """
        out = template
        dct = self._complete_config
        prev = None
        while prev != out:
            for k, v in dct.items():
                out = out.replace('%' + k, v)
            prev = out
        return out

def parse_arguments():
    desc = """\
Read the config file, take urls from the urls file and jump to the
internal site pages to get the direct url to a file. Then download the
file by its direct url.\
    """
    parser = argparse.ArgumentParser(
        description=desc,
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'config_file',
        metavar='config',
        nargs='?',
        default='__PROGRAM_NAME__.xml',
        help="""configuration file for loading (default: __PROGRAM_NAME__.xml)"""
    )
    parser.add_argument(
        '-c',
        dest='create_config_file',
        metavar='filename',
        help="""create interactively configuration file for loading"""
    )
    optiontext = 'v' + __version__
    parser.add_argument('--version', '-V',
                        action='version',
                        version=optiontext)
    optiontext = ('License: {}, see more details'
                  ' at <http://www.gnu.org/licenses/>.'.format(__license__))
    parser.add_argument('--license',
                        action='version',
                        version=optiontext,
                        help='show program\'s license and exit')
    args = parser.parse_args()
    return args

def make_configuration(cmdline_args):
    arg_configfile = cmdline_args.config_file
    arg_createconfigfile = cmdline_args.create_config_file
    config = {}
    config_set_configfile(config, arg_configfile)
    config_set_createconfigfile(config, arg_createconfigfile)
    out = config
    return out

def config_set_configfile(config, value):
    config['config_file'] = value
    out = config
    return out

def config_get_configfile(config):
    out = config.get('config_file')
    return out

def config_set_createconfigfile(config, value):
    config['create_config_file'] = value
    out = config
    return out

def config_get_createconfigfile(config):
    out = config.get('create_config_file')
    return out

def create_config_file(config_file):
    cfc = ConfigFileCreator(config_file)
    cfc.start()
    cfc.set_site_name()
    cfc.set_urls_file()
    cfc.set_notice_messages()
    cfc.set_patterns()
    cfc.set_load_command()
    cfc.set_temp_file_names()
    cfc.set_final_file_names()
    cfc.save_to_file()
    cfc.end()

def download_files(config_file):
    cfh = ConfigFileHandler(config_file)
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

def main():
    args = parse_arguments()
    config = make_configuration(args)
    create_config_fname = config_get_createconfigfile(config)
    if create_config_fname is not None:
        create_config_file(create_config_fname)
        return 0
    config_fname = config_get_configfile(config)
    if not os.path.exists(config_fname):
        print(
            'Config file is not found: {}'.format(config_fname),
            file=sys.stderr
        )
        return 1
    download_files(config_fname)
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('\nBye!', file=sys.stderr)
        sys.exit(2)
