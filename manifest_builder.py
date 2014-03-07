import manifest

class ManifestBuilder(object):
    """Base class for creating Manifests from a specific input source."""

    def __init__(self, manifest_class = manifest.Manifest):
        self.manifest_class = manifest_class

    def supported_attrs(self):
        """Return the set of attribute names that are supported."""
        raise NotImplementedError

    def build(self, source):
        """Build from the given source; return the top-level Manifest object."""
        raise NotImplementedError
