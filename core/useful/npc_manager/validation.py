import keyword

from .schemas import PydanticFieldDef


def _validate_pydantic_fields(fields: list[PydanticFieldDef]) -> None:
    seen: set[str] = set()
    for field in fields:
        name = field.name
        if not name.isidentifier():
            raise ValueError(f"'{name}' is not a valid field name")
        if keyword.iskeyword(name):
            raise ValueError(f"'{name}' is a reserved Python keyword")
        if name.startswith('_'):
            raise ValueError(f"'{name}' must not start with an underscore")
        if name.startswith('model_'):
            raise ValueError(f"'{name}' collides with pydantic's protected 'model_' namespace")
        if name in seen:
            raise ValueError(f"duplicate field name '{name}'")
        seen.add(name)
        if field.type == 'enum' and not field.enum_values:
            raise ValueError(f"field '{name}' of type enum needs at least one enum value")
