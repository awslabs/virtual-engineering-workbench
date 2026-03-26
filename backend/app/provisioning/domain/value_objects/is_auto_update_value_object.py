from app.shared.ddd import value_object


class IsAutoUpdateValueObject(value_object.ValueObject):
    value: bool
