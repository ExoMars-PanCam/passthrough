class VID:
    def __init__(self, from_string: str = None, major: int = None, minor: int = None):
        if from_string is not None:
            components = from_string.split(".")
            if not len(components):
                raise ValueError("VID string is empty!")
            self.major = components[0]
            self.minor = components[1] if len(components) > 1 else None
        elif isinstance(major, int) and isinstance(minor, int):
            self.major = major
            self.minor = minor
        else:
            raise TypeError("A VID must be provided either as a string or an int pair")

    def increment(self, which="minor"):
        if which not in ("major", "minor"):
            raise ValueError(f"expected one of 'major', 'minor'; got '{which}'")
        if which == "major":
            self.major += 1
            self.minor = 0
        else:
            self.minor = 1 if self.minor is None else self.minor + 1

    def __str__(self):
        return (
            f"{self.major}.{self.minor}" if self.minor is not None else str(self.major)
        )


def vid_increment(ctx):
    vid = VID(from_string=ctx.t_elem.text)
    vid.increment("minor")
    return str(vid)
