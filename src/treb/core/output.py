class Output:
    def __init__(self, obj):
        self.obj = obj


class Ok(Output):
    pass


class Error(Output):
    pass
