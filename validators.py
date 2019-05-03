import jsonschema
from django.core.exceptions import ValidationError
from jsonschema.validators import validator_for


def validate_json_schema(value):
    """
    Validate json schema
    """
    try:
        if value:
            # check only if schema defined
            cls = validator_for(value)
            cls.check_schema(value)
    except Exception as e:
        raise ValidationError(message=e.message)

    return value


def validate_json_schema_data(value, schema):
    """
    Validate data according json schema
    """
    try:
        # check result schema
        if value and schema:
            properties = schema.get('properties').keys()
            unexpected_properties = value.keys() - properties
            if unexpected_properties:
                # value key(s) not in expected properties
                raise ValidationError(message=f"{unexpected_properties} not in schema properties")
            jsonschema.validate(value, schema)
    except jsonschema.exceptions.ValidationError as e:
        raise ValidationError(message=e.message)

    return value


def validate_type_geom(layer, feature_geom):
    if layer and feature_geom:
        if layer.type_geom and layer.type_geom != feature_geom.geom_type:
            raise ValidationError(message=f'Geometry type is not the same on the layer')
    return feature_geom