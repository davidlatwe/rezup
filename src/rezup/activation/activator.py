from __future__ import absolute_import, unicode_literals

import os
import sys

if sys.version_info >= (3, 7):
    from importlib.resources import read_binary
else:
    from importlib_resources import read_binary
    # ^ should be installed with virtualenv
from .._vendor.six import ensure_text


class Activator(object):
    """Generates an activate script for the virtual environment"""

    def __init__(self, options):
        """Create a new activator generator.

        :param options: the parsed options as defined within :meth:`add_parser_arguments`
        """
        self.flag_prompt = options.prompt

    @classmethod
    def supports(cls, interpreter):
        """Check if the activation script is supported in the given interpreter.

        :param interpreter: the interpreter we need to support
        :return: ``True`` if supported, ``False`` otherwise
        """
        return True

    @classmethod
    def add_parser_arguments(cls, parser, interpreter):
        """
        Add CLI arguments for this activation script.

        :param parser: the CLI parser
        :param interpreter: the interpreter this virtual environment is based of
        """

    def templates(self):
        raise NotImplementedError

    def generate(self, creator):
        dest_folder = creator.bin_dir
        replacements = self.replacements(creator, dest_folder)
        generated = self._generate(replacements, self.templates(), dest_folder, creator)
        if self.flag_prompt is not None:
            creator.pyenv_cfg["prompt"] = self.flag_prompt
        return generated

    def replacements(self, creator, dest_folder):
        return {
            "__REZUP_PROMPT__": "" if self.flag_prompt is None else self.flag_prompt,
            "__PATH_SEP__": ensure_text(os.pathsep),
        }

    def _generate(self, replacements, templates, to_folder, creator):
        generated = []
        for template in templates:
            text = self.instantiate_template(replacements, template, creator)
            dest = to_folder / self.as_name(template)
            # use write_bytes to avoid platform specific line normalization (\n -> \r\n)
            dest.write_bytes(text.encode("utf-8"))
            generated.append(dest)
        return generated

    def as_name(self, template):
        return template.name

    def instantiate_template(self, replacements, template, creator):
        # read content as binary to avoid platform specific line normalization (\n -> \r\n)
        binary = read_binary(self.__module__, str(template))
        text = binary.decode("utf-8", errors="strict")
        for key, value in replacements.items():
            value = self._repr_unicode(creator, value)
            text = text.replace(key, value)
        return text

    @staticmethod
    def _repr_unicode(creator, value):
        # by default we just let it be unicode
        return value
