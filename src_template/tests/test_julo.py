#!/usr/bin/env python3

# This file is a part of __PROGRAM_NAME__ __PROGRAM_VERSION__
#
# This file installs __PROGRAM_NAME__ in the operating system, cleans
# temporary files and directory in the project.
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

import pytest
import __PROGRAM_NAME__


@pytest.mark.parametrize(
    'io', (
        ('', []),
        ('echo', ['echo']),
        (' echo', ['echo']),
        ('echo ', ['echo']),
        (' echo ', ['echo']),

        ('echo a', ['echo', 'a']),
        ('echo  a', ['echo', 'a']),
        ('echo a ', ['echo', 'a']),
        ('echo  a ', ['echo', 'a']),

        ('echo a b', ['echo', 'a', 'b']),
        ('echo "a b"', ['echo', 'a b']),
        ('echo "a b" "c d"', ['echo', 'a b', 'c d']),
        ('echo "a b" "c"', ['echo', 'a b', 'c']),
        ('echo "a" "b c"', ['echo', 'a', 'b c']),

        ("echo 'a b'", ['echo', 'a b']),
        ("echo 'a b' 'c d'", ['echo', 'a b', 'c d']),

        ('echo \\a', ['echo', '\\a']),
        ('echo a\\ b', ['echo', 'a\\ b']),
        ('echo a \\b', ['echo', 'a', '\\b']),
        ('echo a\\  b', ['echo', 'a\\ ', 'b']),
        ('echo a \\ b', ['echo', 'a', '\\ b']),

        ('echo "\\""', ['echo', '\\"']),
        ('echo " \\" "', ['echo', ' \\" ']),
        ('echo "\\"a"', ['echo', '\\"a']),
        ('echo "\\" a"', ['echo', '\\" a']),

        ("echo '\\''", ['echo', "\\'"]),
        ("echo ' \\' '", ['echo', " \\' "]),
        ("echo '\\'a'", ['echo', "\\'a"]),
        ("echo '\\' a'", ['echo', "\\' a"]),

        ('echo "a b', ['echo', 'a b']),
    )
)
def test_command_line_split(io):
    i, o = io
    assert __PROGRAM_NAME__.CommandLineHandler().split(i) == o, str((i, o))
