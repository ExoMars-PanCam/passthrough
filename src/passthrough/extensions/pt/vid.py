from .. import PTContext

class VID:
    """
    A class for storing a PDS4 version ID.

    A method is provided to increment major or minor versions.
    """
    def __init__(self, from_string: str = None, major: int = None, minor: int = None):
        """
        The constructor either takes a string or a major, minor pair of
        integers.
        """
        if from_string is not None:
            components = from_string.split(".")
            if not len(components):
                raise ValueError("VID string is empty!")
            self.major = int(components[0])
            self.minor = int(components[1]) if len(components) > 1 else 0
        elif isinstance(major, int) and isinstance(minor, int):
            self.major = major
            self.minor = minor
        else:
            raise TypeError("A VID must be provided either as a string or an int pair")

    def increment(self, which: str = "minor") -> None:
        """
        Increment either the major or minor part of the stored VID. When the
        major part is incremented, the minor is reset to zero.
        """
        if which not in ("major", "minor"):
            raise ValueError(f"expected one of 'major', 'minor'; got '{which}'")
        if which == "major":
            self.major += 1
            self.minor = 0
        else:
            self.minor = 1 if self.minor is None else self.minor + 1

    def __str__(self) -> str:
        return (
            f"{self.major}.{self.minor}" if self.minor is not None else str(self.major)
        )


def vid_increment(ctx: PTContext) -> str:
    """
    Extract the content of the current template element, increment its
    minor version and return the resulting version string.

    I think the way this is meant to be used is probably

    <something pt:fetch="true()" pt:fill="vid.increment()"/>
    """
    vid = VID(from_string=ctx.t_elem.text)
    vid.increment("minor")
    return str(vid)
