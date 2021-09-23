class MessageBuilder:
    QUOTE_NONE = {}
    QUOTE_TEXT = str.maketrans({_k: '\\' + _k for _k in "_*[]()~`>#+-=|{}.!\\"})
    QUOTE_PRE = str.maketrans({'`': '\\`', '\\': '\\\\'})
    QUOTE_URL = str.maketrans({')': '\\)', '\\': '\\\\'})

    __slots__ = ('_parts', )

    def __init__(self):
        self._parts = []

    def __str__(self):
        return ''.join(self._parts)

    def raw(self, *value) -> 'MessageBuilder':
        self._parts.extend(value)
        return self

    def nl(self) -> 'MessageBuilder':
        return self.raw("\n")

    # noinspection PyDefaultArgument
    def text(self, *value, escape=True, quote=QUOTE_TEXT) -> 'MessageBuilder':
        if not escape:
            quote = self.QUOTE_NONE
        return self.raw(*(str(i).translate(quote) for i in value))

    def _inline(self, char, *value, escape=True) -> 'MessageBuilder':
        if not value:
            return self.raw(char)

        return self.raw(char)\
            .text(*value, escape=escape, quote=self.QUOTE_PRE if char == '`' else self.QUOTE_TEXT)\
            .raw(char)

    def link(self, value, link) -> 'MessageBuilder':
        return self.raw('[', str(value), '](').text(link, quote=self.QUOTE_URL).raw(')')

    def pre(self, *value, language="") -> 'MessageBuilder':
        return self.raw("```", language, "\n").text(*value, quote=self.QUOTE_PRE).raw("\n```")

    def bold(self, *value, escape=True) -> 'MessageBuilder':
        return self._inline('*', *value, escape=escape)

    def italic(self, *value, escape=True) -> 'MessageBuilder':
        return self._inline('_', *value, escape=escape)

    def underline(self, *value, escape=True) -> 'MessageBuilder':
        return self._inline('__', *value, escape=escape)

    def strikethrough(self, *value, escape=True) -> 'MessageBuilder':
        return self._inline('~', *value, escape=escape)

    def code(self, *value, escape=True) -> 'MessageBuilder':
        return self._inline('`', *value, escape=escape)