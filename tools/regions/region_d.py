"""Ohio and Pennsylvania current official roster cards; HTTP or browser DOM."""
import re
from urllib.parse import urljoin
from build import HTML, has_class, record

SOURCES = {
 'ok-upper':('Oklahoma Senate','https://www.oksenate.gov/senators'),
 'oh-upper':('Ohio Senate','https://www.ohiosenate.gov/members/directory'),
 'oh-lower':('Ohio House of Representatives','https://www.ohiohouse.gov/members/directory'),
 'pa-upper':('Pennsylvania General Assembly','https://www.palegis.us/senate/members'),
 'pa-lower':('Pennsylvania General Assembly','https://www.palegis.us/house/members'),
}
SOURCE_HOSTS = set()
COVERAGE = {st:{'upper':'collected','lower':'collected','blockers':[]} for st in ['OH','PA']}
COVERAGE_OVERRIDES = {'OK':{'upper':'collected','blockers':[]}}
BODIES = {'oh-upper':'Ohio Senate','oh-lower':'Ohio House of Representatives',
          'pa-upper':'Pennsylvania State Senate','pa-lower':'Pennsylvania House of Representatives'}


def parse(key, raw, source):
    tree=HTML(raw).root
    st,ch=key.split('-')
    rows=[]
    if st=='ok':
        cards=tree.find(lambda n:has_class(n,'sSen__item'))
        assert len(cards)==48, 'Expected full current Senate directory'
        for card in cards:
            names=card.find(lambda n:has_class(n,'sSen__sName') and not has_class(n,'sSen__sName-committee-info'))
            districts=card.find(lambda n:has_class(n,'sSen__sDis'))
            parties=card.find(lambda n:has_class(n,'sSen__sMaskText'))
            links=card.find(lambda n:n.tag=='a' and has_class(n,'sSen__sLink'))
            assert len(names)==len(districts)==len(parties)==len(links)==1
            name=names[0].text()
            district=re.fullmatch(r'District (\d+)',districts[0].text())
            assert district
            if name==districts[0].text():
                assert not parties[0].text(), 'Unclear placeholder'
                continue  # District-only placeholder does not identify a person.
            assert parties[0].text() in {'r','d','i'}
            rows.append(record(source,key+'-'+district[1],name,'OK','state','Oklahoma State Senate',district[1],party=parties[0].text(),website=urljoin(source['url'],links[0].attrs['href'])))
        assert 43<=len(rows)<=48 and len(rows)==len({r['id'] for r in rows})
        return rows
    if st=='oh':
        assert '136' in raw.decode(), 'Expected 136th General Assembly context'
        source['effectivePeriod']='136th General Assembly (2025-2026)'
        cards=tree.find(lambda n:has_class(n,'media-container-portrait'))
        for card in cards:
            names=card.find(lambda n:has_class(n,'media-overlay-caption-text-line-1'))
            districts=card.find(lambda n:has_class(n,'media-overlay-caption-text-line-2'))
            assert len(names)==len(districts)==1, 'Roster card changed'
            name=names[0].text()
            match=re.fullmatch(r'District\s+(\d+)\s*(?:\|\s*)?([DRI])?',districts[0].text())
            assert match,'Unrecognized district/party label'
            if name.lower()=='vacant': continue
            links=card.find(lambda n:n.tag=='a' and n.attrs.get('href'))
            assert len(links)==1
            rows.append(record(source,key+'-'+match[1],name,'OH','state',BODIES[key],match[1],
                               party=match[2],website=urljoin(source['url'],links[0].attrs['href'])))
    else:
        assert '2025-2026 Session' in tree.text(), 'Expected 2025-2026 session'
        source['effectivePeriod']='2025-2026 session'
        cards=tree.find(lambda n:has_class(n,'member') and 'data-district' in n.attrs)
        for card in cards:
            names=card.find(lambda n:has_class(n,'thumb-info-inner'))
            assert len(names)==1
            name=names[0].text()
            if name.lower()=='vacant': continue
            links=card.find(lambda n:n.tag=='a' and has_class(n,'thumb-info-wrapper'))
            assert len(links)==1
            path=links[0].attrs['href'].strip()
            assert f'/{"senate" if ch=="upper" else "house"}/members/bio/' in path
            rows.append(record(source,key+'-'+str(int(card.attrs['data-district'])),name,'PA','state',BODIES[key],
                               card.attrs['data-district'],party=card.attrs.get('data-party'),website=urljoin(source['url'],path)))
    maximum={'oh-upper':33,'oh-lower':99,'pa-upper':50,'pa-lower':203}[key]
    assert maximum*.9 <= len(rows) <= maximum,(key,'Unexpected roster size',len(rows))
    assert len(rows)==len({r['id'] for r in rows}), 'Duplicate district cards or incomplete DOM capture'
    return rows
