import inspect
from abc import ABC, abstractmethod

from attrs import NOTHING, define, field, make_class

from treb.core.context import Context
from treb.core.output import Error, Ok


@define(frozen=True, kw_only=True)
class Step(ABC):

    name: str

    callbacks = []

    def __attrs_post_init__(self):
        self._run_callbacks()

    def _run_callbacks(self):
        for cb in self.callbacks:
            cb(self)

    @classmethod
    def register_callback(cls, callback):
        cls.callbacks.append(callback)

    @classmethod
    def unregister_callback(cls, callback):
        cls.callbacks.remove(callback)

    @abstractmethod
    def run(self, ctx):
        raise NotImplementedError

    @abstractmethod
    def rollback(self, ctx):
        raise NotImplementedError


# def step(fn):
#     signature = inspect.signature(fn)

#     fields = {}

#     for (idx, param) in enumerate(signature.parameters.values()):

#         if param.kind not in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD, param.KEYWORD_ONLY):
#             raise TypeError("function cannot have variable arguments like *args or **kwargs")

#         if param.annotation is param.empty:
#             raise TypeError("all arguments must have a type annotation")

#         if param.annotation is Context:
#             pass

#         elif idx == 0:
#             raise TypeError("first argument must have type Context")

#         else:
#             fields[param.name] = field(
#                 default=NOTHING if param.default is param.empty else param.default,
#             )

#     base_cls = make_class(name=fn.__name__, attrs=fields, bases=(Step,))

#     print(fields)

#     def run(self, *args, **kwargs):
#         return Ok(fn(*args, **kwargs))

#     def rollback(self):
#         pass

#     cls_dict = {
#         "run": run,
#         "rollback": rollback,
#     }
#     return type(fn.__name__, (base_cls,), cls_dict)
