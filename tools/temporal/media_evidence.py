"""An explicit media-only evidence catalog, separate from government sources."""
from importlib import import_module,util
from urllib.parse import urlparse
from .evidence import EvidenceStore

MODULES=('media_federal','media_state','media_additional','media_california','media_west','media_midwest','media_south',
         'media_ap','media_ap_northeast','media_ap_midwest','media_ap_south','media_ap_west')
DIRECT_HOSTS={'www.alreporter.com','www.whqr.org','www.opb.org','www.wpr.org','apps.texastribune.org','interactives.apelections.org','apps.npr.org','www.npr.org','npr.org','apnews.com','www.apnews.com',
              'www.ap.org','ap.org','www.reuters.com','reuters.com','www.nbcnews.com',
              'www.texastribune.org','texastribune.org','elections.mpr.org','electionsapi.publicradio.org','www.mprnews.org','www.cnn.com','edition.cnn.com','www.pbs.org','www.cbsnews.com','abcnews.go.com'}


class MediaEvidenceStore(EvidenceStore):
    http_user_agent='Mozilla/5.0'
    @staticmethod
    def publications():
        result={}
        for name in MODULES:
            if util.find_spec(__package__+'.'+name):
                for key,value in import_module('.'+name,__package__).SOURCES.items():
                    if not key.startswith('media-'):raise ValueError('Media source identity must be distinct')
                    if key in result and result[key]!=value:raise ValueError('Conflicting media source identity')
                    result[key]=value
        return result

    @staticmethod
    def delegations():
        return {key:value for name in MODULES if util.find_spec(__package__+'.'+name)
                for key,value in getattr(import_module('.'+name,__package__),'DELEGATIONS',{}).items()}

    def direct_publication(self,key,url):
        parsed=urlparse(url)
        return (key in self.publications() and self.publications()[key][1]==url and
                parsed.scheme=='https' and parsed.hostname in DIRECT_HOSTS and
                not parsed.username and not parsed.password)
