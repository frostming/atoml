import atoml as toml
from collections import OrderedDict
from atoml.decoder import TomlInlineTable, empty_inline_table


def test_decode_inline_table():
    content = """
info = {country = "china", postcode = 350012}
"""
    parsed = toml.loads(content)
    assert isinstance(parsed['info'], TomlInlineTable)


def test_encode_inline_table():
    data = {'info': empty_inline_table()}
    data['info'].update({'country': 'china', 'postcode': 350012})

    encoded = toml.dumps(data, preserve=True)
    assert 'info = {country = "china", postcode = 350012}' in encoded


def test_encode_array_of_inline_table():
    data = [('apple', 'red'), ('banana', 'yellow'), ('grape', 'purple')]
    my_dict = {'fruit': []}
    for name, color in data:
        item = empty_inline_table(OrderedDict)
        item['name'] = name
        item['color'] = color
        my_dict['fruit'].append(item)

    encoded = toml.dumps(my_dict, preserve=True)
    for name, color in data:
        assert '{name = "%s", color = "%s"}' % (name, color) in encoded
