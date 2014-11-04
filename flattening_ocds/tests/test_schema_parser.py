import pytest
from collections import OrderedDict
from flattening_ocds.schema import SchemaParser


def test_filename_and_dict_error(tmpdir):
    """A value error should be raised if both schema_filename and
    root_schema_dict are supplied to SchemaParser"""
    tmpfile = tmpdir.join('test_schema.json')
    tmpfile.write('{}')
    with pytest.raises(ValueError):
        SchemaParser(schema_filename=tmpfile.strpath, root_schema_dict={})


def test_references_followed(tmpdir):
    """JSON references should be followed when a JSON file is read."""
    tmpfile = tmpdir.join('test_schema.json')
    tmpfile.write('{"a":{"$ref":"#/b"}, "b":"c"}')
    parser = SchemaParser(schema_filename=tmpfile.strpath)
    assert parser.root_schema_dict['a'] == 'c'


def test_order_preserved(tmpdir):
    """Order should be preserved when a JSON file is read."""
    tmpfile = tmpdir.join('test_schema.json')
    tmpfile.write('{"a":{}, "c":{}, "b":{}, "d":{}}')
    parser = SchemaParser(schema_filename=tmpfile.strpath)
    assert list(parser.root_schema_dict.keys()) == ['a', 'c', 'b', 'd']


def test_main_sheet_basic():
    parser = SchemaParser(root_schema_dict={
        'properties': {
            'testA': {},
            'testB': {}
        }
    })
    parser.parse()
    assert set(parser.main_sheet) == set(['testA', 'testB'])


def test_main_sheet_nested():
    parser = SchemaParser(root_schema_dict={
        'properties': {
            'testA': {
                'type': 'object',
                'properties': {'testC': {}}
            }
        }
    })
    parser.parse()
    assert set(parser.main_sheet) == set(['testA.testC'])


def test_sub_sheet():
    parser = SchemaParser(root_schema_dict={
        'properties': {
            'testA': {
                'type': 'array',
                'items': {
                    'properties': {'testB': {}}
                }
            },
        }
    })
    parser.parse()
    assert set(parser.main_sheet) == set([])
    assert set(parser.sub_sheets) == set(['testA'])
    assert list(parser.sub_sheets['testA']) == ['ocid', 'testB']


class TestSubSheetParentID():
    def test_parent_is_object(self):
        parser = SchemaParser(root_schema_dict={
            'properties': {
                'testA': {
                    'type': 'object',
                    'properties': {
                        'id': {},
                        'testB': {
                            'type': 'array',
                            'items': {
                                'properties': {'testC': {}}
                            }
                        }
                    }
                }
            }
        })
        parser.parse()
        assert set(parser.main_sheet) == set(['testA.id'])
        assert set(parser.sub_sheets) == set(['testB'])
        assert list(parser.sub_sheets['testB']) == ['ocid', 'testA.id', 'testC']

    def test_parent_is_array(self):
        parser = SchemaParser(root_schema_dict={
            'properties': {
                'testA': {
                    'type': 'array',
                    'items': {
                        'properties': {
                            'id': {},
                            'testB': {
                                'type': 'array',
                                'items': {
                                    'properties': {'testC': {}}
                                }
                            }
                        }
                    }
                }
            }
        })
        parser.parse()
        assert set(parser.main_sheet) == set()
        assert set(parser.sub_sheets) == set(['testA', 'testB'])
        assert list(parser.sub_sheets['testA']) == ['ocid', 'id']
        assert list(parser.sub_sheets['testB']) == ['ocid', 'testA.id', 'testC']

    def test_two_parents(self):
        parser = SchemaParser(root_schema_dict={
            'properties': OrderedDict([
                ('testA', {
                    'type': 'array',
                    'items': {
                        'properties': {
                            'id': {},
                            'testB': {
                                'type': 'array',
                                'items': {
                                    'properties': {'testC': {}}
                                }
                            }
                        }
                    }
                }),
                ('testD', {
                    'type': 'array',
                    'items': {
                        'properties': {
                            'id': {},
                            'testB': {
                                'type': 'array',
                                'items': {
                                    'properties': {'testE': {}}
                                }
                            }
                        }
                    }
                })
            ])
        })
        parser.parse()
        assert set(parser.main_sheet) == set()
        assert set(parser.sub_sheets) == set(['testA', 'testB', 'testD'])
        assert list(parser.sub_sheets['testA']) == ['ocid', 'id']
        assert list(parser.sub_sheets['testD']) == ['ocid', 'id']
        assert list(parser.sub_sheets['testB']) == ['ocid', 'testA.id', 'testD.id', 'testC', 'testE']


def test_references_sheet_names(tmpdir):
    """The referenced name should be used for the sheet name"""
    tmpfile = tmpdir.join('test_schema.json')
    tmpfile.write('''{
        "properties": { "testA": {
            "type": "array",
            "items": {"$ref": "#/testB"}
        } },
        "testB": { "properties": {"testC":{}} }
    }''')
    parser = SchemaParser(schema_filename=tmpfile.strpath)
    parser.parse()
    assert set(parser.sub_sheets) == set(['testB'])
    assert list(parser.sub_sheets['testB']) == ['ocid', 'testC']