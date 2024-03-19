class DynamicCounter:
    # template=r'counter:(?P<count>[0-9]+):user:(?P<id>[0-9]+)',

    def __init_subclass__(cls, template=None):
        cls.ok = template

    def __init__(self):
        print("ok")


class DynamicCounter2(DynamicCounter, template="as"):
    ...


print(DynamicCounter2.ok)
