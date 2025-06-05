#!/usr/bin/env python3

import pytest
import julo


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
    assert julo.CommandLineHandler().split(i) == o, str((i, o))
