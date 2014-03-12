from __future__ import print_function
import re

from manifest_builder import ManifestBuilder

def parse_uint(s):
    ret = int(s, base=0)
    if ret < 0:
        raise ValueError("Negative integer not allowed here: '%s'" % (s))
    return ret

def parse_sha1sum(s, _sha1RE = re.compile(r'^[0-9a-f]{40}$')):
    sha1 = s.strip().lower()
    if not _sha1RE.match(sha1):
        raise ValueError("Not a valid SHA1 sum: '%s'" % (s))
    return sha1

class ManifestFileParser(ManifestBuilder):
    """Parse a text file containing a manifest description.

    The expected format is as follows:

     - Comments start with '#' and go to EOL.
     - Comments and empty lines are ignored.
     - Each line contains a single manifest entry..
     - The indent specifies at which level the entry is added.
     - Increasing the indent makes the current entry a child of the previous
       entry. Indentation rules work like in Python.
     - An entry consists of a name, and an optional collection of attributes
     - Attributes are defined between '{' and '}'
     - Attributes are comma-separated, and consists of a key and an associated
       value, separated by a colon.
     - Typical line format:
          entry name { attr1: value1, attr2: value2 } # comment
     - Whitespace is stripped from the start and end of all tokens
    """

    attr_handlers = {
        # name: handler (string -> parsed value)
        "mode": parse_uint,
        "uid": parse_uint,
        "gid": parse_uint,
        "size": parse_uint,
        "sha1": parse_sha1sum,
    }

    def supported_attrs(self):
        return self.attr_handlers.keys()

    def parse_attr(self, key_s, value_s):
        """Canonicalize the given attribute key and value strings."""
        key = key_s.strip().lower()
        return (key, self.attr_handlers.get(key, str)(value_s.strip()))

    def parse_token(self, token):
        """Parse the given token into a (entry, attrs) tuple.

        A token consists of an entry (file/directory name) and an optional
        collection of attributes that apply to that entry. The general format
        of a token is thus:
            token_name WS* { attr_key: attr_val, attr_key: attr_val, ... }
        """
        # The final '{' separates the entry from the attributes
        try:
            entry, attr_s = token.rsplit('{', 1)
        except ValueError: # no attributes
            return (token, {})

        assert attr_s.endswith('}')
        attrs = {}
        for s in attr_s[:-1].split(','):
            if not s.strip():
                continue
            k, v = self.parse_attr(*s.split(':', 1))
            attrs[k] = v

        return (entry.rstrip(), attrs)

    def parse_lines(self, f):
        """Return (indent, token, attrs) for each logical line in 'f'.

        The given 'f' may be anything that can be iterated to yield lines, e.g.
        a file object, a StringIO object, a list of lines, etc.
        """
        indents = [0] # Stack of indent levels. Initial 0 is always present
        for linenum, line in enumerate(f):
            # Strip trailing newline, strip comment to EOL, and s/tab/spaces/
            line = line.rstrip("\n").split('#', 1)[0].replace("\t", " " * 8)
            token = line.lstrip(" ") # Token starts after indent
            if not token: # blank line
                continue

            indent = len(line) - len(token) # Indent is #spaces stripped above
            if indent > indents[-1]: # Increasing indent
                indents.append(indent)
            elif indent < indents[-1]: # Decreasing indent
                while indent < indents[-1]:
                    indents.pop()
                if indent != indents[-1]:
                    raise ValueError("Broken indent at line %d in %s: level "
                        "%d != %d" % (linenum, getattr(f, "name", "<unknown>"),
                                      indent, indents[-1]))

            token = token.rstrip() # strip trailing WS
            token, attrs = self.parse_token(token) # split attrs out of token
            yield(len(indents) - 1, token, attrs)

    def build(self, f):
        """Parse the given file and return the resulting toplevel Manifest.

        The given file 'f' may be anything that can be iterated to yield lines.
        """
        prev = cur = top = self.manifest_class()
        level = 0
        for indent, token, attrs in self.parse_lines(f):
            if indent > level: # drill into the previous entry
                cur = prev
                level += 1
                assert indent == level
            elif indent < level:
                while indent < level:
                    cur = cur.getparent()
                    assert cur is not None
                    level -= 1
                assert indent == level

            prev = cur.add([token], attrs)
        return top

class ManifestFileWriter(object):
    """Generate a human-readable text file representation of a Manifest object.

    The output generated by this class should always be parseable by the above
    ManifestFileParser class.
    """

    formatter = {
        # name: formatter (parsed value -> parse-able string)
        "mode": lambda v: "0o%06o" % (v),
        # all the others work with str() default formatting
    }

    def format_attrs(self, attrs):
        """Return a parseable string representation of the given attributes."""
        if not attrs:
            return ""
        l = []
        for k, v in sorted(attrs.items()):
            l.append("%s: %s" % (k, self.formatter.get(k, str)(v)))
        return " {%s}" % (", ".join(l))

    def write(self, m, f, level = 0, indent = "\t", attrkeys = None):
        """Write the given Manifest in a ManifestFileParser-compatible format.

        The given Manifest 'm' is written to the given file object 'f' in a text
        format that can be re-read with ManifestFileParser.

        'attrkeys' is the set of attributes to be output, defaults to all.
        """
        for name, child in sorted(m.items()):
            attrs = child.getattrs()
            if attrkeys is not None:
                attrs = dict((k, v) for k, v in attrs.items() if k in attrkeys)
            print(indent * level + name + self.format_attrs(attrs), file=f)
            self.write(child, f, level + 1, indent, attrkeys)
