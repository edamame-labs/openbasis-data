"""Shared vocabulary and coverage rules for statewide executive offices and state high courts.

Governors are collected by tools/regions/executive.py. Every other elected
statewide executive office, and each state's court(s) of last resort, are
collected by regional modules named tools/regions/statewide_<x>.py and
tools/regions/courts_<x>.py. See docs/STATEWIDE.md and docs/COURTS.md.

Statewide module interface (tools/regions/statewide_<x>.py):

    STATEWIDE = {'TX': {'lieutenantGovernor': 'collected', 'comptroller': 'collected',
                        'railroadCommissioner': 'not-collected', 'blockers': ['...']}, ...}
        Every *elected* statewide executive office the state has, other than the
        governor, keyed by an OFFICES key. Offices the state does not elect are
        omitted. 'not-collected' offices must have a blocker that says why.
    SOURCES = {key: (publisher, url)}; optional BROWSER = {keys needing a person-made capture}
    collect(acquire, offline) -> (rows, sources)

    Rows come from build.record(source, id, name, state, 'state', '<State> Executive', office=TITLE, ...).
    id is '<st>-<officeKey>' (single-holder offices) or '<st>-<officeKey>-<n>' (MULTI offices).

Court module interface (tools/regions/courts_<x>.py):

    COURTS = {'TX': {'Supreme Court of Texas': 'collected', 'Texas Court of Criminal Appeals': 'collected',
                     'blockers': []}, ...}
        Each court of last resort, by its official name. Rows have body = that name,
        office = 'Chief Justice' | 'Justice' | 'Presiding Judge' | 'Judge' (as the court titles its members).
    SOURCES, optional BROWSER, collect(acquire, offline) as above.
"""

# key: (office title used in rows, Google Civic role). Add keys here, never ad hoc in a module.
OFFICES = {
    'lieutenantGovernor': ('Lieutenant Governor', 'deputyHeadOfGovernment'),
    'secretaryOfState': ('Secretary of State', 'governmentOfficer'),
    'attorneyGeneral': ('Attorney General', 'governmentOfficer'),
    'treasurer': ('Treasurer', 'governmentOfficer'),
    'auditor': ('Auditor', 'governmentOfficer'),
    'comptroller': ('Comptroller', 'governmentOfficer'),
    'controller': ('Controller', 'governmentOfficer'),
    'superintendentOfPublicInstruction': ('Superintendent of Public Instruction', 'governmentOfficer'),
    'agricultureCommissioner': ('Commissioner of Agriculture', 'governmentOfficer'),
    'insuranceCommissioner': ('Insurance Commissioner', 'governmentOfficer'),
    'laborCommissioner': ('Commissioner of Labor', 'governmentOfficer'),
    'landCommissioner': ('Commissioner of Public Lands', 'governmentOfficer'),
    'mineInspector': ('Mine Inspector', 'governmentOfficer'),
    'publicServiceCommissioner': ('Public Service Commissioner', 'executiveCouncil'),
    'corporationCommissioner': ('Corporation Commissioner', 'executiveCouncil'),
    'railroadCommissioner': ('Railroad Commissioner', 'executiveCouncil'),
    'boardOfEqualizationMember': ('Board of Equalization Member', 'executiveCouncil'),
    'executiveCouncilor': ('Executive Councilor', 'executiveCouncil'),
    'stateBoardOfEducationMember': ('State Board of Education Member', 'schoolBoard'),
    'universityRegent': ('University Regent', 'specialPurposeOfficer'),
    'universityTrustee': ('University Trustee', 'specialPurposeOfficer'),
    'universityGovernor': ('University Board of Governors Member', 'specialPurposeOfficer'),
    'chiefFinancialOfficer': ('Chief Financial Officer', 'governmentOfficer'),
    'taxCommissioner': ('Tax Commissioner', 'governmentOfficer'),
    'officeOfHawaiianAffairsTrustee': ('Office of Hawaiian Affairs Trustee', 'specialPurposeOfficer'),
}
# Scope: offices elected by the voters of the whole state. Boards whose members are elected by district
# (state boards of education in AL/CO, CA Board of Equalization, CU Regents, NH Executive Council, district PSCs)
# are excluded: a district seat belongs to the residents of that district, and their district geography is not published.
# Offices that have several holders at once; their ids carry a suffix.
MULTI = {'publicServiceCommissioner', 'corporationCommissioner', 'railroadCommissioner', 'boardOfEqualizationMember',
         'executiveCouncilor', 'stateBoardOfEducationMember', 'universityRegent', 'universityTrustee', 'universityGovernor',
         'officeOfHawaiianAffairsTrustee'}
TITLES = {title: key for key, (title, _) in OFFICES.items()}
COURT_OFFICES = {'Chief Justice', 'Justice', 'Presiding Judge', 'Judge'}
STATUSES = {'collected', 'not-collected'}


def check_declarations(statewide, courts, state_codes):
    """Static checks on what the regional modules declare."""
    for st, item in statewide.items():
        assert st in state_codes, st
        for key, status in item.items():
            if key == 'blockers': continue
            assert key in OFFICES and key != 'governor', (st, key)
            assert status in STATUSES, (st, key, status)
        if any(v == 'not-collected' for k, v in item.items() if k != 'blockers'):
            assert item.get('blockers'), (st, 'A not-collected office needs a blocker')
    for st, item in courts.items():
        assert st in state_codes, st
        assert any(k != 'blockers' for k in item), (st, 'No court of last resort declared')
        for name, status in item.items():
            if name == 'blockers': continue
            assert status in STATUSES, (st, name, status)
        if any(v == 'not-collected' for k, v in item.items() if k != 'blockers'):
            assert item.get('blockers'), (st, 'A not-collected court needs a blocker')


def executive_offices(st, declared, rows):
    """{officeKey: {status, records}} for one state's non-governor offices, checked against its rows."""
    out = {}
    for key, status in declared.items():
        if key == 'blockers': continue
        title = OFFICES[key][0]
        n = sum(r['office'] == title for r in rows)
        if status == 'collected':
            assert n >= 1 if key in MULTI else n == 1, ('Statewide coverage disagrees with parsed rows', st, key, n)
        else:
            assert n == 0, ('Rows for a not-collected office', st, key, n)
        out[key] = dict(status=status, records=n)
    extra = {r['office'] for r in rows} - {OFFICES[k][0] for k in out} - {'Governor'}
    assert not extra, ('Rows for undeclared offices', st, sorted(extra))
    return out


def court_coverage(st, declared, rows):
    """{'courts': {name: {status, records}}, 'blockers': [...]} for one state, checked against its rows."""
    courts = {}
    for name, status in declared.items():
        if name == 'blockers': continue
        members = [r for r in rows if r['body'] == name]
        assert all(r['office'] in COURT_OFFICES for r in members), (st, name)
        assert (status == 'collected') == bool(members), ('Court coverage disagrees with parsed rows', st, name, len(members))
        courts[name] = dict(status=status, records=len(members))
    extra = {r['body'] for r in rows} - set(courts)
    assert not extra, ('Rows for undeclared courts', st, sorted(extra))
    return dict(courts=courts, blockers=declared.get('blockers', []))
