from peak.api import *
from interfaces import *
from places import MultiTraverser, Place
from publish import TraversalPath
from resources import Resource
from wsgiref.util import setup_testing_defaults

__all__ = [
    'Skin',
]































class Skin(MultiTraverser,Place):

    """Skins provide a branch-point between the app root and resources"""

    protocols.advise(
        instancesProvide = [ISkin]
    )

    cache      = binding.Make(dict)
    policy     = binding.Obtain('..')

    layerNames = binding.Require("Sequence of layer names")

    place_url  = binding.Obtain('policy/resourcePrefix')

    def items(self):
        getLayer = self.policy.getLayer
        prefix = self.place_url
        layers = []
        for name in self.layerNames:
            layer = getLayer(name)
            # Kludge: don't include layer in path to child resources, by
            #    suggesting its component name is an empty string
            binding.suggestParentComponent(self,'',layer)
            if __debug__:
                # Make sure the kludge worked, by asserting that the layer's
                # place_url (if any) is either an absolute URL, or the same
                # as our place_url.
                if IPlace(layer,None) is not None:
                    url = IPlace(layer).place_url
                    assert naming.URLMatch(url) or url==prefix, (
                        "Bad url", url,prefix
                    )
            layers.append(layer)
        return layers

    items = binding.Make(items, suggestParent=False)




    dummyEnviron = {}
    setup_testing_defaults(dummyEnviron)


    def getResource(self, path):

        path = adapt(path,TraversalPath)

        if path in self.cache:
            return self.cache[path]

        start = self.policy.newContext(
            self.dummyEnviron.copy(), self, self, None
        )

        if not path[0]:
            path = path[1:]

        resourceCtx = path.traverse(start)
        self.cache[path] = subject = resourceCtx.current
        return subject




















