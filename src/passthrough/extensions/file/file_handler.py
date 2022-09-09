from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Dict, Optional, Sequence, Type, Union, List, Tuple

from lxml import etree

from ...exc import PTTemplateError


class DataObject(metaclass=ABCMeta):
    _handlers: ClassVar[Dict[str, Type["DataObject"]]] = {}

    def __init__(self, t_elem: etree._Element, nsmap: Dict[str, str]):
        self._t_elem = t_elem
        self._nsmap = nsmap
        self._offset: Optional[int] = None

        self.data: Any = None
        self.local_id: str = self._find_id()

    def __init_subclass__(
        cls,
        classes: Union[str, Sequence[str], None] = None,
        abstract: bool = False,
        **kwargs,
    ):
        super().__init_subclass__(**kwargs)
        if abstract:
            return
        elif classes is None or len(classes) == 0:
            raise TypeError(
                f"{cls.__name__} does not specify the required class parameter"
                " 'classes' (the data object class(es) supported by the type, e.g."
                " 'Encoded_Image')"
            )
        if isinstance(classes, str):
            cls._handlers[classes] = cls
        else:
            for c in classes:
                cls._handlers[c] = cls

    @classmethod
    def from_elem(cls, t_elem: etree._Element, nsmap: Dict[str, str]) -> "DataObject":
        name = etree.QName(t_elem).localname
        if name not in cls._handlers:
            raise ValueError(f"Data object of class '{name}' is not supported")
        return cls._handlers[name](t_elem, nsmap)

    @property
    def offset(self) -> int:
        if self._offset is None:
            raise RuntimeError(
                f"Offset requested before data object '{self.local_id}' has been"
                " written to disk"
            )
        return self._offset

    @offset.setter
    def offset(self, offset: int):
        if not isinstance(offset, int):
            raise TypeError(
                f"offset must be an integer number of bytes; got {offset}"
                f" ({type(offset)})"
            )
        self._offset = offset

    @property
    @abstractmethod
    def size(self) -> int:
        ...

    @property
    @abstractmethod
    def serialized(self) -> bytes:
        # FIXME: Union with str for compat w/ text files?
        # FIXME: implement __bytes__ instead? (typing.SupportsBytes)
        ...

    def _find_id(self) -> str:
        local_id = self._t_elem.find("./pds:local_identifier", namespaces=self._nsmap)
        if local_id is None:
            raise PTTemplateError(
                "No pds:local_identifier found for data object class", self._t_elem
            )
        return local_id.text.strip()


class FileHandler(metaclass=ABCMeta):
    @property
    @abstractmethod
    def creation_date_time(self) -> str:
        ...

    @property
    @abstractmethod
    def file_name(self) -> str:
        ...

    @property
    @abstractmethod
    def file_size(self) -> int:
        ...

    @property
    @abstractmethod
    def md5_checksum(self) -> str:
        ...

    @property
    @abstractmethod
    def t_elem(self) -> etree._Element:
        ...

    @abstractmethod
    def write(self, out_dir: Path) -> None:
        ...

    @abstractmethod
    def __getitem__(self, local_id: str) -> DataObject:
        ...

    # TODO: __contains__, __len__, etc.?
