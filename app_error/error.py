class Error:
    __desc = None
    __num = None

    def __init__(self, err_desc, err_num=None):
        self.__desc = err_desc
        self.__num = err_num

    @property
    def error_desc(self):
        return self.__desc

    @error_desc.setter
    def error_desc(self, value):
        self.__desc = value

    @property
    def error_number(self):
        return self.__num

    @error_number.setter
    def error_number(self, value):
        self.__num = value
